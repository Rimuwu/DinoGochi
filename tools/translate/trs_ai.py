import json
from logging.handlers import RotatingFileHandler
import random
import os
import sys
import emoji
import re
import asyncio
import threading
from tqdm.asyncio import tqdm
import logging
from dotenv import load_dotenv
import aiohttp

# Загружаем переменные окружения из .env
load_dotenv()

# Logger setup
logger = logging.getLogger()
ex = os.path.dirname(__file__)

log_filehandler = RotatingFileHandler(filename=f"{ex}/logs/last.log", encoding='utf-8', mode='a+')
log_streamhandler = logging.StreamHandler()
log_formatter = logging.Formatter("%(message)s")
log_filehandler.setFormatter(log_formatter)
log_streamhandler.setFormatter(log_formatter)
logger.addHandler(log_filehandler)
logger.addHandler(log_streamhandler)
logger.setLevel(logging.INFO)

# Load settings
with open(os.path.join(ex, 'settings.json'), encoding='utf-8') as f: 
    settings = json.load(f)
    replace_codes = settings['replace_codes']
    main_code = settings['main_code']
    langs_path = settings['langs_path']
    dump_path = settings['dump_path']
    ignore_translate_keys = settings['ignore_translate_keys']
    no_edit = settings['no_edit']

# Чтение и парсинг токенов из env
raw_keys = os.getenv("G4F_API_KEYS", "")
G4F_API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]
G4F_API_BASE = os.getenv("G4F_API_BASE", "https://g4f.space/v1")

# Лимит на размер одной пачки (батча) в символах
MAX_BATCH_CHAR_LIMIT = 1500 

if not G4F_API_KEYS:
    print("[ERROR] Не найдено ни одного токена G4F_API_KEYS в файле .env!")
    sys.exit(1)

STOP_BY_CTRL_C = False

async def only_translate_batch(batch_items, from_language, to_language, api_key):
    """
    Отправляет группу строк напрямую через aiohttp с фиксом Brotli-сжатия.
    """
    # Жесткая пауза между пакетами, чтобы уложиться в лимит "1 запрос в секунду" у конечного провайдера
    await asyncio.sleep(random.uniform(1.5, 2.5))

    current_model = "gpt-4o-mini"
    payload = {item[0]: item[1] for item in batch_items}

    system_prompt = (
        f"You are a professional localization engine for a Telegram bot.\n"
        f"Task: Translate the values inside the provided JSON object from '{from_language}' to '{to_language}'.\n\n"
        f"CRITICAL RULES:\n"
        f"1. Output ONLY a valid raw JSON object containing the translations. Do not wrap it in markdown codeblocks (like ```json). Never include explanations, greetings, or commentary.\n"
        f"2. Keep the original keys exactly as they are in the input JSON.\n"
        f"3. Preserve all variable placeholders inside text exactly as they are. Examples: {{name}}, {{count}}, #1042#, /start, <b>, </b>, etc. Do not translate, format, or alter them.\n"
        f"4. Keep all emojis exactly in their original positions.\n"
        f"5. Maintain the exact original structure, line breaks (\\n), trailing/leading spaces, and markdown style (**bold**, _italic_).\n"
        f"   - Pay special attention to spaces before or after line breaks (\\n). If there are spaces before \\n, keep them exactly!\n"
        f"6. If a text is already in the target language or cannot be translated, return it completely unchanged."
    )

    url = f"{G4F_API_BASE.rstrip('/')}/chat/completions"
    
    # Явно исключаем 'br' (Brotli), чтобы сервер принудительно слал gzip/deflate, убирая ошибку Can not decode content-encoding: br
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate" 
    }
    
    data = {
        "model": current_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=60) as response:
                if response.status != 200:
                    err_text = await response.text()
                    logger.error(f"HTTP Error {response.status}: {err_text}")
                    return None
                    
                res_json = await response.json()
                res_text = res_json['choices'][0]['message']['content'].strip()
        
        if res_text.startswith("```"):
            res_text = re.sub(r"^```(?:json)?\n|```$", "", res_text, flags=re.MULTILINE).strip()
            
        return json.loads(res_text)
    except Exception as e:
        logger.error(f"AI Batch Error: {e}")
        return None

async def process_batch_with_retry(batch_items, to_lang, from_lang, rep=0):
    """
    Управляет отправкой батча строк, ротирует ключи из env с увеличенным временем ожидания при ошибках.
    """
    selected_key = random.choice(G4F_API_KEYS)

    translated_dict = await only_translate_batch(batch_items, from_lang, to_lang, selected_key)

    if translated_dict is None or not isinstance(translated_dict, dict):
        if rep < 5:
            # При ошибках 429 увеличиваем паузу (бэкбофф), давая прокси-серверу остыть
            wait_time = (2 ** (rep + 1)) * 3 + random.uniform(1.0, 3.0)
            print(f"[RETRY] Ошибка пакета ({len(batch_items)} ключей). Ждем {wait_time:.1f} сек... (Попытка {rep + 1}/5)")
            await asyncio.sleep(wait_time)
            return await process_batch_with_retry(batch_items, to_lang, from_lang, rep=rep + 1)
        
        return {item[0]: "NOTEXT" for item in batch_items}

    return translated_dict

def read_json(path):
    if not os.path.exists(path): return {}
    with open(path, encoding='utf-8') as f: return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def set_by_path(dct, path, value, dump=None):
    keys = path.split('.')
    cur = dct
    for idx, k in enumerate(keys[:-1]):
        next_k = keys[idx + 1]
        if isinstance(cur, list):
            k_int = int(k)
            while len(cur) <= k_int: cur.append([] if next_k.isdigit() else {})
            cur = cur[k_int]
        elif isinstance(cur, dict):
            if k not in cur: cur[k] = [] if next_k.isdigit() else {}
            cur = cur[k]
    last = keys[-1]
    if isinstance(cur, list) and last.isdigit():
        last = int(last)
        while len(cur) <= last: cur.append(None)
        cur[last] = value
    else:
        cur[last] = value

def del_by_path(dct, path):
    keys = path.split('.')
    cur = dct
    for k in keys[:-1]:
        cur = cur[int(k)] if isinstance(cur, list) else cur[k]
    last = keys[-1]
    if isinstance(cur, list): del cur[int(last)]
    else: del cur[last]

def build_structure(data):
    if isinstance(data, dict): return {k: build_structure(v) for k, v in data.items()}
    if isinstance(data, list): return [build_structure(v) for v in data]
    return 'NOTEXT'

def compare_structures(base, dump, path=""):
    new_keys, changed_keys, deleted_keys = [], [], []
    if isinstance(base, dict):
        base_keys = set(base.keys())
        dump_keys = set(dump.keys()) if isinstance(dump, dict) else set()
        for k in base_keys:
            new_path = f"{path}.{k}" if path else k
            if k not in dump_keys: new_keys.append(new_path)
            else:
                n, c, d = compare_structures(base[k], dump[k], new_path)
                new_keys, deleted_keys = new_keys + n, deleted_keys + d
                if not (new_path.split('.')[-1] in no_edit or (len(new_path.split('.')) > 1 and new_path.split('.')[-2] in no_edit)):
                    changed_keys += c
        for k in dump_keys - base_keys: deleted_keys.append(f"{path}.{k}" if path else k)
    elif isinstance(base, list) and isinstance(dump, list):
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)
            if idx >= len(dump): new_keys.append(new_path)
            else:
                n, c, d = compare_structures(v, dump[idx], new_path)
                new_keys, deleted_keys = new_keys + n, deleted_keys + d
                if not (new_path.split('.')[-1] in no_edit or (len(new_path.split('.')) > 1 and new_path.split('.')[-2] in no_edit)):
                    changed_keys += c
        for idx in range(len(base), len(dump)): deleted_keys.append(f"{path}.{idx}" if path else str(idx))
    else:
        if base != dump: changed_keys.append(path)
    return new_keys, changed_keys, deleted_keys

def sort_dict_by_reference(data, reference):
    if isinstance(reference, dict) and isinstance(data, dict):
        return {k: sort_dict_by_reference(data[k], reference[k]) for k in reference if k in data} | {k: data[k] for k in data if k not in reference}
    if isinstance(reference, list) and isinstance(data, list):
        return [sort_dict_by_reference(data[i], reference[i]) for i in range(min(len(data), len(reference)))] + data[len(reference):]
    return data

def ctrl_c_watcher():
    global STOP_BY_CTRL_C
    try:
        input("\n[LOG] Нажмите Enter для остановки...\n")
        STOP_BY_CTRL_C = True
    except Exception:
        STOP_BY_CTRL_C = True

def get_by_path(dct, path):
    keys = path.split('.')
    cur = dct
    for k in keys:
        if isinstance(cur, list) and k.isdigit():
            cur = cur[int(k)] if int(k) < len(cur) else None
        else: cur = cur.get(k) if isinstance(cur, dict) else None
    return cur

async def translate_batch_task(batch, lang, main_code, lang_data, dump_data, lang_path, dump_path_, main_data, pbar, semaphore):
    global STOP_BY_CTRL_C
    if STOP_BY_CTRL_C:
        pbar.update(1)
        return

    async with semaphore:
        translated_batch = await process_batch_with_retry(batch, lang, main_code)
        
        for path, orig_value in batch:
            translated_value = translated_batch.get(path, "NOTEXT")
            
            if translated_value == "NOTEXT":
                dump_value = "NOTEXT"
            else:
                dump_value = orig_value
                print(f"Переведено [{lang}]: {path} -> {translated_value}")

            set_by_path(lang_data, path, translated_value)
            set_by_path(dump_data, f'{lang}.'+path, dump_value)

        pbar.update(1)
        
        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

async def async_main():
    global STOP_BY_CTRL_C
    threading.Thread(target=ctrl_c_watcher, daemon=True).start()

    lang_arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    main_lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{main_code}.json"))
    main_data = read_json(main_lang_path).get(main_code, {})

    log_dir = os.path.join(ex, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    lang_files = os.listdir(os.path.normpath(os.path.join(ex, langs_path)))
    lang_codes = [f.replace('.json', '') for f in lang_files if f.endswith('.json') and f.replace('.json', '') != main_code]
    if lang_arg: lang_codes = [l for l in lang_codes if l == lang_arg]

    for lang in lang_codes:
        print(f"\n=== Перевод: {lang} ===")
        lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
        dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

        lang_data = read_json(lang_path).get(lang, {})
        dump_data = read_json(dump_path_)

        if not dump_data:
            dump_data = {lang: build_structure(main_data)}
            write_json(dump_path_, dump_data)

        new_keys, changed_keys, deleted_keys = compare_structures(main_data, dump_data[lang])

        def collect_notext(data, path=""):
            if isinstance(data, dict):
                for k, v in data.items(): collect_notext(v, f"{path}.{k}" if path else k)
            elif isinstance(data, list):
                for idx, v in enumerate(data): collect_notext(v, f"{path}.{idx}" if path else str(idx))
            elif data == "NOTEXT" and path not in changed_keys:
                changed_keys.append(path)

        collect_notext(lang_data)

        for key in deleted_keys:
            try: del_by_path(lang_data, key)
            except: pass
            try: del_by_path(dump_data[lang], key)
            except: pass

        for key in new_keys:
            orig = get_by_path(main_data, key)
            if not isinstance(orig, str): set_by_path(lang_data, key, orig)

        write_json(dump_path_, dump_data)
        
        paths_to_translate = []
        def collect_leafs(data, base_path=""):
            res = []
            if isinstance(data, dict):
                for k, v in data.items(): res.extend(collect_leafs(v, f"{base_path}.{k}" if base_path else k))
            elif isinstance(data, list):
                for idx, v in enumerate(data): res.extend(collect_leafs(v, f"{base_path}.{idx}" if base_path else str(idx)))
            elif isinstance(data, (str, int, float, bool)):
                res.append((base_path, data))
            return res

        for path in new_keys + changed_keys:
            orig = get_by_path(main_data, path)
            if isinstance(orig, (dict, list)): paths_to_translate.extend(collect_leafs(orig, path))
            else: paths_to_translate.append((path, orig))

        batches = []
        current_batch = []
        current_batch_chars = 0

        for path, value in paths_to_translate:
            if not isinstance(value, str) or not value.strip() or value.lower() in ["true", "false"]:
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue
                
            if set(path.split('.')) & set(ignore_translate_keys):
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue
                
            if len(value) <= 2 or all(c in [e['emoji'] for e in emoji.emoji_list(value)] for c in value if not c.isspace()):
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue

            if current_batch_chars + len(value) > MAX_BATCH_CHAR_LIMIT and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_batch_chars = 0

            current_batch.append((path, value))
            current_batch_chars += len(value)

        if current_batch:
            batches.append(current_batch)

        total_batches = len(batches)
        if total_batches == 0:
            write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
            write_json(dump_path_, dump_data)
            continue

        semaphore = asyncio.Semaphore(1)
        pbar = tqdm(total=total_batches, desc="Перевод пакетов", unit="пакет")
        
        tasks = [
            translate_batch_task(batch, lang, main_code, lang_data, dump_data, lang_path, dump_path_, main_data, pbar, semaphore)
            for batch in batches
        ]

        await asyncio.gather(*tasks)
        pbar.close()

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

if __name__ == '__main__':
    asyncio.run(async_main())