import json
import os
import sys
import re
import time
import random
import logging
import signal
import queue
from logging.handlers import RotatingFileHandler
from tqdm import tqdm
from threading import Thread, Lock, Event

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Настройка логов
logger = logging.getLogger("trs_gemini")
ex = os.path.dirname(__file__)
log_dir = os.path.join(ex, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filehandler = RotatingFileHandler(filename=f"{ex}/logs/last.log", encoding='utf-8', mode='a+')
log_streamhandler = logging.StreamHandler()
log_formatter = logging.Formatter("%(message)s")
log_filehandler.setFormatter(log_formatter)
log_streamhandler.setFormatter(log_formatter)
logger.addHandler(log_filehandler)
logger.addHandler(log_streamhandler)
logger.setLevel(logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Загрузка настроек
with open(os.path.join(ex, 'settings.json'), encoding='utf-8') as f:
    settings = json.load(f)
    main_code = settings['main_code']
    langs_path = settings['langs_path']
    dump_path = settings['dump_path']
    ignore_translate_keys = settings['ignore_translate_keys']
    no_edit = settings['no_edit']

# Читаем ключи из .env
raw_keys = os.getenv("GEMINI_API_KEY", "")
base_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

KEY_CONFIGS = []

print("[INFO] Инициализируем API-ключи (оптимизированный плавный старт)...")

for idx, key in enumerate(base_keys):
    masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "INVALID"
    
    # Стартуем по умолчанию с gemma-2-27b-it (15 RPM).
    # Если на твоем тарифе она недоступна (404), воркер сам переключит ключ на gemini-2.5-flash
    KEY_CONFIGS.append({
        "api_key": key,
        "rpm": 15,
        "model": "gemma-2-27b-it",
        "delay": 60.0 / 15.0,
        "masked": masked_key
    })
    print(f"  -> Ключ #{idx+1} ({masked_key}) добавлен в пул. Стартовая модель: gemma-2-27b-it")

# Окно лимита символов на батч для экономного расхода RPM (172к символов разобьются примерно на 12 запросов)
MAX_BATCH_CHAR_LIMIT = 20000

if not KEY_CONFIGS:
    print("\n[КРИТИЧЕСКАЯ ОШИБКА] Нет токенов GEMINI_API_KEY в файле .env.")
    sys.exit(1)

file_lock = Lock()
print_lock = Lock()
shutdown_event = Event()

def should_skip_translation(val):
    if not isinstance(val, str): return True
    val_strip = val.strip()
    if not val_strip: return True
    if val_strip.lower() in ["true", "false"]: return True
    no_emoji_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf\s\d\W_]', '', val_strip)
    if not no_emoji_text: return True
    return False

def only_translate_batch(client, client_idx, model_name, batch_items, from_language, to_language):
    if shutdown_event.is_set(): return None, False, model_name

    payload = {item[0]: item[1] for item in batch_items}

    system_prompt = (
        f"You are a professional localization engine for a Telegram bot DinoGochi.\n"
        f"Task: Translate the values inside the provided JSON object from '{from_language}' to '{to_language}'.\n\n"
        f"CRITICAL RULES:\n"
        f"1. Output ONLY a valid raw JSON object containing the translations. Do not wrap it in markdown codeblocks. Never include explanations, greetings, or commentary.\n"
        f"2. Keep the original keys exactly as they are in the input JSON.\n"
        f"3. Preserve all variable placeholders inside text exactly as they are. Examples: {{name}}, {{count}}, #1042#, /start, <b>, </b>, etc. Do not translate or format them.\n"
        f"4. Keep all emojis exactly in their original positions.\n"
        f"5. Maintain the exact original structure, line breaks (\\n), trailing/leading spaces, and markdown style (**bold**, _italic_).\n"
        f"6. Maintain the gaming slang and context of a virtual pet (tamagotchi) game.\n"
        f"7. Before translating, analyze the source Russian text. If it contains minor grammar, spelling mistakes, or typos, correct the meaning internally and translate the CORRECTED text. Do not carry over typos.\n"
        f"8. The text formatting (alignment, spaces, indentation) forms the structure of the message. If there are multiple spaces or specific alignment, they MUST be preserved exactly.\n"
        f"9. NEVER leave the text in the source language (Russian) in the output. Every single value must be translated into the target language, even if it contains specific game terms or style elements."
    )

    try:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json"
        )

        response = client.models.generate_content(
            model=model_name,
            contents=json.dumps(payload, ensure_ascii=False),
            config=config
        )
        
        if shutdown_event.is_set(): return None, False, model_name

        if not response or not response.text:
            return None, False, model_name

        res_text = response.text.strip()
        if res_text.startswith("```"):
            res_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', res_text, flags=re.IGNORECASE).strip()

        data = json.loads(res_text)
        return data, False, model_name

    except json.JSONDecodeError:
        with print_lock:
            logger.error(f"\n[Поток-{client_idx}] [ERROR] Некорректный JSON от модели.")
        return None, False, model_name
    except Exception as e:
        is_rate_limit = False
        err_msg = str(e)
        
        # Переключение на Flash «на лету» при ошибке 404
        if "404" in err_msg or "not found" in err_msg.lower():
            new_model = "gemini-2.5-flash" if model_name != "gemini-2.5-flash" else "gemini-2-flash"
            with print_lock:
                print(f"\n[Поток-{client_idx}] Модель {model_name} недоступна (404). Переключаемся на {new_model}...")
            return None, False, new_model

        if "429" in err_msg or "ResourceExhausted" in err_msg or "rate-limited" in err_msg:
            is_rate_limit = True
        else:
            with print_lock:
                logger.error(f"\n[Поток-{client_idx}] [API ERROR с моделью {model_name}]: {e}")
        return None, is_rate_limit, model_name

# --- Служебные функции работы с JSON ---
def read_json(path):
    if not os.path.exists(path): return {}
    with open(path, encoding='utf-8') as f: return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def set_by_path(dct, path, value):
    keys = path.split('.')
    cur = dct
    for idx, k in enumerate(keys[:-1]):
        if isinstance(cur, dict):
            if k not in cur:
                # Больше не гадаем по next_k.isdigit(), смотрим на фактический тип в cur, если он уже есть.
                # По умолчанию для новых веток всегда создаем dict, так как в локализациях цифры чаще всего — ключи объектов.
                cur[k] = {}
            cur = cur[k]
        elif isinstance(cur, list):
            k_int = int(k)
            while len(cur) <= k_int: 
                cur.append({})
            cur = cur[k_int]
            
    last = keys[-1]
    if isinstance(cur, dict):
        cur[last] = value
    elif isinstance(cur, list):
        if last.isdigit():
            last = int(last)
            while len(cur) <= last: 
                cur.append(None)
            cur[last] = value
        else:
            # Фоллбек на случай, если структура перемешалась
            pass

def get_by_path(dct, path):
    keys = path.split('.')
    cur = dct
    for k in keys:
        if isinstance(cur, list) and k.isdigit(): 
            cur = cur[int(k)] if int(k) < len(cur) else None
        elif isinstance(cur, dict): 
            cur = cur.get(k)
        else: 
            return None
    return cur

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

def build_structure(data):
    if isinstance(data, dict): return {k: build_structure(v) for k, v in data.items()}
    if isinstance(data, list): return [build_structure(v) for v in data]
    return 'NOTEXT'

# --- Потоковый Воркер ---
def worker_lifecycle(task_queue, progress_bar, config, client_idx, lang, lang_path, dump_path_, main_data):
    client = genai.Client(api_key=config["api_key"])
    model_name = config["model"]
    delay = config["delay"]

    while not shutdown_event.is_set():
        try:
            batch = task_queue.get(timeout=1)
        except queue.Empty:
            break

        start_time = time.time()
        rep = 0
        success = False

        while rep < 5 and not success and not shutdown_event.is_set():
            translated_dict, is_rate_limit, updated_model = only_translate_batch(
                client, client_idx, model_name, batch, main_code, lang
            )
            
            # Если произошла 404 ошибка и модель сменилась на Flash
            if updated_model != model_name:
                model_name = updated_model
                delay = 60.0 / 5.0  # Снижаем RPM до 5 для безопасной работы с Flash
                continue

            if is_rate_limit:
                task_queue.put(batch)
                wait_time = random.uniform(25.0, 40.0)
                with print_lock:
                    print(f"\n[Поток-{client_idx}][{model_name}] Лимит RPM (429)! Возвращаем батч в очередь. Спим {wait_time:.1f} сек...")
                time.sleep(wait_time)
                break 

            if shutdown_event.is_set(): break

            if translated_dict and isinstance(translated_dict, dict):
                bad_paths = []
                for path, orig_value in batch:
                    translated_value = translated_dict.get(path, "NOTEXT")
                    if translated_value != "NOTEXT":
                        orig_vars = set(re.findall(r'\{([^}]+)\}', str(orig_value)))
                        trans_vars = set(re.findall(r'\{([^}]+)\}', str(translated_value)))
                        contains_arabic = bool(re.search(r'[\u0600-\u06ff\u0750-\u077f\ufb50-\ufbc1\ufbd3-\ufd3f\ufd50-\ufdfd\ufe70-\ufefc]', str(translated_value)))
                        contains_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', str(translated_value))) if lang not in ['ru', 'uk', 'be', 'bg', 'mk', 'sr'] else False
                        newline_mismatch = str(orig_value).count('\n') != str(translated_value).count('\n')
                        
                        if orig_vars != trans_vars or contains_arabic or contains_cyrillic or newline_mismatch:
                            bad_paths.append(path)

                if bad_paths and rep < 4:
                    rep += 1
                    time.sleep(4)
                    continue

                with file_lock:
                    lang_data_current = read_json(lang_path).get(lang, {})
                    dump_data_current = read_json(dump_path_)

                    for path, orig_value in batch:
                        translated_value = translated_dict.get(path, "NOTEXT")
                        if path in bad_paths: translated_value = "NOTEXT"
                        set_by_path(lang_data_current, path, translated_value)
                        set_by_path(dump_data_current, f'{lang}.'+path, orig_value if translated_value != "NOTEXT" else "NOTEXT")
                    
                    write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                    write_json(dump_path_, dump_data_current)
                    
                success = True
                progress_bar.update(1)
            else:
                rep += 1
                time.sleep(4)

        if not success and not shutdown_event.is_set() and not is_rate_limit:
            with file_lock:
                lang_data_current = read_json(lang_path).get(lang, {})
                dump_data_current = read_json(dump_path_)
                for path, _ in batch:
                    set_by_path(lang_data_current, path, "NOTEXT")
                    set_by_path(dump_data_current, f'{lang}.'+path, "NOTEXT")
                write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                write_json(dump_path_, dump_data_current)
            progress_bar.update(1)

        elapsed = time.time() - start_time
        if elapsed < delay and success:
            time.sleep(delay - elapsed)

        task_queue.task_done()

def main():
    def handle_signal(signum, frame):
        with print_lock: print("\n[INFO] Корректное сохранение и выход...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    lang_arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    main_lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{main_code}.json"))
    main_data = read_json(main_lang_path).get(main_code, {})

    lang_files = os.listdir(os.path.normpath(os.path.join(ex, langs_path)))
    lang_codes = [f.replace('.json', '') for f in lang_files if f.endswith('.json') and f.replace('.json', '') != main_code]
    if lang_arg: lang_codes = [l for l in lang_codes if l == lang_arg]

    for lang in lang_codes:
        if shutdown_event.is_set(): break

        print(f"\n=== Обработка локализации [{lang}] ===")
        lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
        dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

        lang_data = read_json(lang_path).get(lang, {})
        dump_data = read_json(dump_path_)

        if not dump_data:
            dump_data = {lang: build_structure(main_data)}
            write_json(dump_path_, dump_data)

        new_keys, changed_keys, deleted_keys = compare_structures(main_data, dump_data[lang])

        paths_to_translate = []
        def collect_leafs(data, base_path=""):
            res = []
            if isinstance(data, dict):
                for k, v in data.items(): res.extend(collect_leafs(v, f"{base_path}.{k}" if base_path else k))
            elif isinstance(data, list):
                for idx, v in enumerate(data): res.extend(collect_leafs(v, f"{base_path}.{idx}" if base_path else str(idx)))
            elif isinstance(data, (str, int, float, bool)): res.append((base_path, data))
            return res

        all_main_leafs = collect_leafs(main_data)
        keys_to_translate = set(new_keys + changed_keys)
        
        for path, orig in all_main_leafs:
            curr_val = get_by_path(lang_data, path)
            curr_dump_val = get_by_path(dump_data.get(lang, {}), path)
            if curr_val == "NOTEXT" or curr_dump_val == "NOTEXT" or curr_val is None:
                keys_to_translate.add(path)

        for path, orig in all_main_leafs:
            if path in keys_to_translate: paths_to_translate.append((path, orig))

        batches = []
        current_batch = []
        current_batch_chars = 0

        for path, value in paths_to_translate:
            if should_skip_translation(value) or (set(path.split('.')) & set(ignore_translate_keys)):
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue

            if current_batch_chars + len(value) > MAX_BATCH_CHAR_LIMIT and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_batch_chars = 0

            current_batch.append((path, value))
            current_batch_chars += len(value)

        if current_batch: batches.append(current_batch)

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

        if not batches:
            print("[INFO] Новых строк для перевода нет.")
            continue

        task_queue = queue.Queue()
        for batch in batches:
            task_queue.put(batch)
        
        print(f"[INFO] Активируем пул из {len(KEY_CONFIGS)} рабочих ключей...")
        
        with tqdm(total=len(batches), desc="Прогресс пакетов") as pbar:
            threads = []
            for idx, config in enumerate(KEY_CONFIGS):
                t = Thread(
                    target=worker_lifecycle,
                    args=(task_queue, pbar, config, idx + 1, lang, lang_path, dump_path_, main_data)
                )
                t.start()
                threads.append(t)
                # Плавная задержка старта потоков (4 секунды), чтобы исключить 429 RPM на старте
                time.sleep(4.0)

            while any(t.is_alive() for t in threads):
                if shutdown_event.is_set():
                    while not task_queue.empty():
                        try:
                            task_queue.get_nowait()
                            task_queue.task_done()
                        except queue.Empty: break
                    break
                time.sleep(0.5)

            for t in threads: t.join()

    if shutdown_event.is_set():
        print("[INFO] Прервано пользователем.")
    else:
        print("[INFO] Перевод успешно завершен.")

if __name__ == '__main__':
    main()