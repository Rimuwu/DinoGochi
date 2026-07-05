import json
import os
import sys
sys.stdout.reconfigure(errors='replace')
sys.stderr.reconfigure(errors='replace')
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

# Цветовая разметка вывода в консоль
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"

# Читаем ключи из .env
raw_keys = os.getenv("GEMINI_API_KEY", "")
base_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

KEY_CONFIGS = []

print("[INFO] Инициализируем API-ключи (оптимизированный плавный старт)...")

for idx, key in enumerate(base_keys):
    masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "INVALID"
    
    # Стартуем по умолчанию с gemini-2.5-flash (15 RPM).
    KEY_CONFIGS.append({
        "api_key": key,
        "rpm": 15,
        "model": "gemini-2.5-flash",
        "delay": 60.0 / 15.0,
        "masked": masked_key
    })
    print(f"  -> Ключ #{idx+1} ({masked_key}) добавлен в пул. Стартовая модель: gemini-2.5-flash")

def should_ignore_path(path, ignore_keys):
    if not path:
        return False
    parts = path.split('.')
    for idx, part in enumerate(parts):
        if part in ignore_keys:
            # Если это 'inline_menu' и оно не является конечным ключом (т.е. это словарь, который нужно обходить дальше)
            if part == 'inline_menu' and idx < len(parts) - 1:
                continue
            return True
    return False

# Окно лимита символов на батч для экономного расхода RPM (172к символов разобьются примерно на 12 запросов)
MAX_BATCH_CHAR_LIMIT = 20000

if not KEY_CONFIGS:
    print(f"\n{COLOR_RED}[КРИТИЧЕСКАЯ ОШИБКА] Нет токенов GEMINI_API_KEY в файле .env.{COLOR_RESET}")
    sys.exit(1)

file_lock = Lock()
print_lock = Lock()
shutdown_event = Event()

def should_skip_translation(val):
    if not isinstance(val, str): return True
    val_strip = val.strip()
    if not val_strip: return True
    if val_strip.lower() in ["true", "false", "notext"]: return True
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
        f"3. Preserve all variable placeholders inside curly braces (e.g. {{name}}, {{count}}) and special IDs (e.g. #1042#) exactly. Do not translate them.\n"
        f"4. Keep all emojis exactly in their original positions.\n"
        f"5. Maintain the exact original structure, line breaks (\\n), trailing/leading spaces, and markdown style (**bold**, _italic_).\n"
        f"6. Maintain the gaming slang and context of a virtual pet (tamagotchi) game.\n"
        f"7. Before translating, analyze the source Russian text. If it contains minor grammar, spelling mistakes, or typos, correct the meaning internally and translate the CORRECTED text. Do not carry over typos.\n"
        f"8. The text formatting (alignment, spaces, indentation) forms the structure of the message. If there are multiple spaces or specific alignment, they MUST be preserved exactly.\n"
        f"9. NEVER leave the text in the source language (Russian) in the output. Every single value must be translated into the target language, even if it contains specific game terms or style elements.\n"
        f"10. Note that text inside angle brackets representing command parameter hints (e.g. <тип_квеста>, <userid>) is NOT an HTML formatting tag and MUST be translated into the target language (e.g. to <quest_type>, <userid>)."
    )

    try:
        with print_lock:
            print(f"\n{COLOR_CYAN}[Поток-{client_idx}][{to_language.upper()}] Отправка пакета на перевод ({len(batch_items)} ключей)...{COLOR_RESET}")
            for path, val in batch_items[:3]: 
                print(f"  -> [{path}]: {repr(val)}")
            if len(batch_items) > 3:
                print(f"  ... и еще {len(batch_items) - 3} ключей.")

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

        with print_lock:
            print(f"\n{COLOR_GREEN}[Поток-{client_idx}][{to_language.upper()}] Успешно получен перевод:{COLOR_RESET}")
            for path, _ in batch_items[:3]:
                translated = data.get(path, "NOTEXT")
                print(f"  <- [{path}]: {repr(translated)}")
            if len(batch_items) > 3:
                print(f"  ... всего переведено строк: {len(data)}")

        return data, False, model_name

    except json.JSONDecodeError:
        with print_lock:
            logger.error(f"\n{COLOR_RED}[Поток-{client_idx}][{to_language.upper()}] [ERROR] Некорректный JSON от модели.{COLOR_RESET}")
        return None, False, model_name
    except Exception as e:
        is_rate_limit = False
        err_msg = str(e)
        
        # Переключение на другую модель «на лету» при ошибке 404
        if "404" in err_msg or "not found" in err_msg.lower():
            new_model = "gemini-2-flash" if model_name == "gemini-2.5-flash" else "gemini-2.5-flash"
            with print_lock:
                print(f"\n{COLOR_YELLOW}[Поток-{client_idx}] Модель {model_name} недоступна (404). Переключаемся на {new_model}...{COLOR_RESET}")
            return None, False, new_model

        if "429" in err_msg or "ResourceExhausted" in err_msg or "rate-limited" in err_msg:
            is_rate_limit = True
            with print_lock:
                logger.warning(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{model_name}][{to_language.upper()}] [429] Ответ API: {err_msg[:300]}{COLOR_RESET}")
        else:
            with print_lock:
                logger.error(f"\n{COLOR_RED}[Поток-{client_idx}][{model_name}][{to_language.upper()}] [API ERROR с моделью {model_name}]: {e}{COLOR_RESET}")
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

def validate_translation(orig_value, translated_value, lang):
    if not isinstance(translated_value, str):
        return False, "not a string"
    if translated_value == "NOTEXT":
        return False, "value is NOTEXT"
    
    # 1. Variable placeholders like {name}, {count}
    orig_vars = set(re.findall(r'\{([^}]+)\}', str(orig_value)))
    trans_vars = set(re.findall(r'\{([^}]+)\}', str(translated_value)))
    if orig_vars != trans_vars:
        return False, f"Placeholders mismatch: {orig_vars} vs {trans_vars}"
        
    # 2. Tag formatting (Telegram allowed HTML tags only)
    tag_pattern = r'</?(?:b|strong|i|em|u|ins|s|strike|del|span|tg-spoiler|a|code|pre|blockquote)(?:\s+[^>]*)?>'
    orig_tags = re.findall(tag_pattern, str(orig_value), re.IGNORECASE)
    trans_tags = re.findall(tag_pattern, str(translated_value), re.IGNORECASE)
    if orig_tags != trans_tags:
        return False, f"Tags mismatch: {orig_tags} vs {trans_tags}"

    # 3. Markdown formatting tokens: **, __, *, _, `, ||, ~
    def extract_formatting(text):
        return (text.count('**'), text.count('__'), text.count('*'), text.count('_'), text.count('`'), text.count('||'), text.count('~'))
    if extract_formatting(str(orig_value)) != extract_formatting(str(translated_value)):
        return False, f"Markdown formatting mismatch: {extract_formatting(str(orig_value))} vs {extract_formatting(str(translated_value))}"

    # 4. Special IDs (#1042#) and Telegram commands (/start)
    orig_ids = set(re.findall(r'#\d+#', str(orig_value)))
    trans_ids = set(re.findall(r'#\d+#', str(translated_value)))
    if orig_ids != trans_ids:
        return False, f"IDs mismatch: {orig_ids} vs {trans_ids}"

    def extract_commands(text):
        matches = re.findall(r'(?:^|[\s\(\[\{\"\x27\x60])(/([a-zA-Z0-9_]+))', text)
        return set(m[0].strip() for m in matches)

    orig_commands = extract_commands(str(orig_value))
    trans_commands = extract_commands(str(translated_value))
    if orig_commands != trans_commands:
        return False, f"Telegram commands mismatch: {orig_commands} vs {trans_commands}"

    # 5. Emojis matching exactly
    def extract_emojis(text):
        return re.findall(r'[\U00010000-\U0010ffff\u2600-\u27bf]', text)
    orig_emojis = extract_emojis(str(orig_value))
    trans_emojis = extract_emojis(str(translated_value))
    if orig_emojis != trans_emojis:
        return False, f"Emojis mismatch: {orig_emojis} vs {trans_emojis}"

    # 6. Line breaks (\n) and leading/trailing whitespaces
    orig_newlines = str(orig_value).count('\n')
    trans_newlines = str(translated_value).count('\n')
    if orig_newlines != trans_newlines:
        return False, f"Newlines count mismatch: {orig_newlines} vs {trans_newlines}"
    
    orig_str = str(orig_value)
    trans_str = str(translated_value)
    _sp_l = lambda s: re.sub(r'^[ \t]+', '', s)
    _sp_r = lambda s: re.sub(r'[ \t]+$', '', s)
    orig_lspace = len(orig_str) - len(_sp_l(orig_str))
    trans_lspace = len(trans_str) - len(_sp_l(trans_str))
    orig_rspace = len(orig_str) - len(_sp_r(orig_str))
    trans_rspace = len(trans_str) - len(_sp_r(trans_str))
    if orig_lspace != trans_lspace or orig_rspace != trans_rspace:
        return False, f"Whitespace mismatch: lspace {orig_lspace} vs {trans_lspace}, rspace {orig_rspace} vs {trans_rspace}"

    # 7. Cyrillic letters check
    cyrillic_langs = ['ru', 'uk', 'be', 'bg', 'mk', 'sr']
    contains_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', trans_str))
    if lang not in cyrillic_langs and contains_cyrillic:
        cyr_chars = ''.join(set(re.findall(r'[а-яА-ЯёЁ]', trans_str)))
        return False, f"Cyrillic characters found in non-Cyrillic language: '{cyr_chars}'"

    # 8. Check if target language doesn't support Cyrillic but translation is identical to original and contains Cyrillic
    if lang not in cyrillic_langs and orig_str == trans_str and any(c in 'а-яА-ЯёЁ' for c in orig_str):
        return False, "Identical translation containing Cyrillic"

    # 9. Arabic script check
    contains_arabic = bool(re.search(r'[\u0600-\u06ff\u0750-\u077f\ufb50-\ufbc1\ufbd3-\ufd3f\ufd50-\ufdfd\ufe70-\ufefc]', trans_str))
    if contains_arabic:
        return False, "Arabic characters found"

    return True, ""

def sync_structure(base, target, lang, path=""):
    if isinstance(base, dict):
        res = {}
        for k, v in base.items():
            new_path = f"{path}.{k}" if path else k
            target_v = target.get(k) if isinstance(target, dict) else None
            is_no_edit = k in no_edit or (path and path.split('.')[-1] in no_edit)
            if is_no_edit:
                res[k] = v
            else:
                res[k] = sync_structure(v, target_v, lang, new_path)
        return res
    elif isinstance(base, list):
        res = []
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)
            target_v = target[idx] if (isinstance(target, list) and idx < len(target)) else None
            is_no_edit = str(idx) in no_edit or (path and path.split('.')[-1] in no_edit)
            if is_no_edit:
                res.append(v)
            else:
                res.append(sync_structure(v, target_v, lang, new_path))
        return res
    else:
        if should_skip_translation(base) or (path and should_ignore_path(path, ignore_translate_keys)):
            return base
        if target is not None and target != "NOTEXT":
            return target
        return "NOTEXT"

def sync_dump_structure(base, target, lang_data, path=""):
    if isinstance(base, dict):
        res = {}
        for k, v in base.items():
            new_path = f"{path}.{k}" if path else k
            target_v = target.get(k) if isinstance(target, dict) else None
            lang_v = lang_data.get(k) if isinstance(lang_data, dict) else None
            res[k] = sync_dump_structure(v, target_v, lang_v, new_path)
        return res
    elif isinstance(base, list):
        res = []
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)
            target_v = target[idx] if (isinstance(target, list) and idx < len(target)) else None
            lang_v = lang_data[idx] if (isinstance(lang_data, list) and idx < len(lang_data)) else None
            res.append(sync_dump_structure(v, target_v, lang_v, new_path))
        return res
    else:
        if should_skip_translation(base) or (path and should_ignore_path(path, ignore_translate_keys)):
            return base
        if lang_data is not None and lang_data != "NOTEXT":
            return base
        return "NOTEXT"

def build_structure(data):
    if isinstance(data, dict): return {k: build_structure(v) for k, v in data.items()}
    if isinstance(data, list): return [build_structure(v) for v in data]
    return 'NOTEXT'

# --- Потоковый Воркер ---
def worker_lifecycle(task_queue, progress_bar, config, client_idx, main_data):
    client = genai.Client(api_key=config["api_key"])
    model_name = config["model"]
    delay = config["delay"]

    consec_429 = 0          # Счётчик подряд идущих рейт-лимитов без успешного перевода
    MAX_CONSEC_429 = 10     # Порог отключения токена

    while not shutdown_event.is_set():
        try:
            item = task_queue.get(timeout=1)
        except queue.Empty:
            break

        lang, lang_path, dump_path_, batch = item
        start_time = time.time()
        rep = 0
        success = False

        batch = list(batch)  # Преобразуем в список для изменения при ретраях
        while rep < 5 and batch and not success and not shutdown_event.is_set():
            translated_dict, is_rate_limit, updated_model = only_translate_batch(
                client, client_idx, model_name, batch, main_code, lang
            )
            
            # Если произошла 404 ошибка и модель сменилась на Flash
            if updated_model != model_name:
                model_name = updated_model
                delay = 60.0 / 5.0  # Снижаем RPM до 5 для безопасной работы с Flash
                continue

            if is_rate_limit:
                consec_429 += 1
                task_queue.put(item)
                wait_time = random.uniform(25.0, 40.0)
                with print_lock:
                    print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{model_name}][{lang.upper()}] Лимит RPM (429)! Возвращаем батч в очередь. Спим {wait_time:.1f} сек... ({consec_429}/{MAX_CONSEC_429}){COLOR_RESET}")
                if consec_429 >= MAX_CONSEC_429:
                    with print_lock:
                        print(f"\n{COLOR_RED}[Поток-{client_idx}] Токен отключён: {MAX_CONSEC_429} рейт-лимитов подряд без единого успешного перевода.{COLOR_RESET}")
                    return  # Завершаем воркер полностью
                time.sleep(wait_time)
                break 

            if shutdown_event.is_set(): break

            if translated_dict and isinstance(translated_dict, dict):
                bad_paths = []
                good_items = []
                reasons = {}
                for path, orig_value in batch:
                    translated_value = translated_dict.get(path, "NOTEXT")
                    
                    # Самоисправление: убираем carriage returns (\r), лишние переносы строк и пробелы
                    if isinstance(translated_value, str) and isinstance(orig_value, str):
                        translated_value = translated_value.replace('\r', '')
                        if orig_value.count('\n') == 0 and translated_value.count('\n') > 0:
                            translated_value = translated_value.replace('\n', ' ')
                            translated_value = re.sub(r' {2,}', ' ', translated_value)
                        
                        space_lstrip = lambda s: re.sub(r'^[ \t]+', '', s)
                        space_rstrip = lambda s: re.sub(r'[ \t]+$', '', s)
                        orig_lspace = len(orig_value) - len(space_lstrip(orig_value))
                        orig_rspace = len(orig_value) - len(space_rstrip(orig_value))
                        stripped_trans = space_lstrip(space_rstrip(translated_value))
                        translated_value = (' ' * orig_lspace) + stripped_trans + (' ' * orig_rspace)
                        translated_dict[path] = translated_value

                    is_valid, reason = validate_translation(orig_value, translated_value, lang)
                    if is_valid:
                        good_items.append((path, orig_value, translated_value))
                    else:
                        bad_paths.append(path)
                        reasons[path] = reason

                # Сохраняем успешные переводы сразу
                if good_items:
                    with file_lock:
                        lang_data_current = read_json(lang_path).get(lang, {})
                        dump_data_current = read_json(dump_path_)

                        for path, orig_value, translated_value in good_items:
                            set_by_path(lang_data_current, path, translated_value)
                            set_by_path(dump_data_current, f'{lang}.'+path, orig_value)
                        
                        write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                        write_json(dump_path_, dump_data_current)
                    consec_429 = 0  # Сбрасываем счётчик рейт-лимитов при успешном переводе

                if bad_paths:
                    if rep < 4:
                        rep += 1
                        # Оставляем в батче только ошибочные ключи
                        batch = [item for item in batch if item[0] in bad_paths]
                        with print_lock:
                            print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{lang.upper()}][RETRY] Некачественный перевод для:")
                            for p in bad_paths:
                                print(f"  -> [{p}] Ошибка: {reasons[p]}")
                            print(f"Повторная отправка только ошибочных ключей ({len(batch)} шт.). Попытка {rep}/5. Пауза 4 сек...{COLOR_RESET}")
                        time.sleep(4)
                        continue
                    else:
                        # На последней попытке записываем NOTEXT для оставшихся некачественных
                        with file_lock:
                            lang_data_current = read_json(lang_path).get(lang, {})
                            dump_data_current = read_json(dump_path_)
                            for path, _ in batch:
                                set_by_path(lang_data_current, path, "NOTEXT")
                                set_by_path(dump_data_current, f'{lang}.'+path, "NOTEXT")
                            write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                            write_json(dump_path_, dump_data_current)
                        success = True
                        progress_bar.update(1)
                else:
                    success = True
                    progress_bar.update(1)
            else:
                rep += 1
                if rep < 5:
                    time.sleep(4)
                else:
                    # Если все попытки исчерпаны и ответа нет, заполняем NOTEXT
                    with file_lock:
                        lang_data_current = read_json(lang_path).get(lang, {})
                        dump_data_current = read_json(dump_path_)
                        for path, _ in batch:
                            set_by_path(lang_data_current, path, "NOTEXT")
                            set_by_path(dump_data_current, f'{lang}.'+path, "NOTEXT")
                        write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                        write_json(dump_path_, dump_data_current)
                    success = True
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
    priority_order = ['en', 'id', 'es']
    lang_codes = sorted(lang_codes, key=lambda l: priority_order.index(l) if l in priority_order else len(priority_order))
    if lang_arg: lang_codes = [l for l in lang_codes if l == lang_arg]

    all_batches = []

    for lang in lang_codes:
        if shutdown_event.is_set(): break

        print(f"\n=== Подготовка локализации [{lang}] ===")
        lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
        dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

        lang_data = read_json(lang_path).get(lang, {})
        dump_data = read_json(dump_path_)

        # Synchronize and clean up initial files to strictly match main_data structure
        lang_data = sync_structure(main_data, lang_data, lang)
        dump_data[lang] = sync_dump_structure(main_data, dump_data.get(lang, {}), lang_data)

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
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
            if (curr_val is None or (isinstance(curr_val, str) and curr_val.strip().upper() == "NOTEXT") or
                curr_dump_val is None or (isinstance(curr_dump_val, str) and curr_dump_val.strip().upper() == "NOTEXT")):
                keys_to_translate.add(path)

        for path, orig in all_main_leafs:
            if path in keys_to_translate: paths_to_translate.append((path, orig))

        valid_items = []
        for path, value in paths_to_translate:
            if should_skip_translation(value):
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue
            if should_ignore_path(path, ignore_translate_keys):
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue
            valid_items.append((path, value))

        to_translate_count = len(valid_items)
        print(f"[INFO] Найдено {len(paths_to_translate)} потенциальных ключей для перевода. Будет переведено: {to_translate_count}")

        # Вычисляем динамический лимит символов на пакет для распределения по всем потокам
        num_threads = len(GEMINI_API_KEYS) if GEMINI_API_KEYS else 1
        total_chars = sum(len(val) for _, val in valid_items)
        target_batch_chars = total_chars / num_threads if num_threads > 0 else total_chars
        batch_char_limit = min(MAX_BATCH_CHAR_LIMIT, max(1, int(target_batch_chars)))

        lang_batches = []
        current_batch = []
        current_batch_chars = 0

        for path, value in valid_items:
            if current_batch_chars + len(value) > batch_char_limit and current_batch:
                lang_batches.append(current_batch)
                current_batch = []
                current_batch_chars = 0

            current_batch.append((path, value))
            current_batch_chars += len(value)

        if current_batch: lang_batches.append(current_batch)

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

        for b in lang_batches:
            all_batches.append((lang, lang_path, dump_path_, b))

    if not all_batches:
        print("[INFO] Новых строк для перевода нет ни на один язык.")
        return

    task_queue = queue.Queue()
    for item in all_batches:
        task_queue.put(item)
    
    print(f"[INFO] Активируем пул из {len(KEY_CONFIGS)} рабочих ключей для обработки {len(all_batches)} пакетов по всем языкам...")
    
    with tqdm(total=len(all_batches), desc="Прогресс пакетов") as pbar:
        threads = []
        for idx, config in enumerate(KEY_CONFIGS):
            t = Thread(
                target=worker_lifecycle,
                args=(task_queue, pbar, config, idx + 1, main_data)
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

    # Финальная синхронизация для всех языков после завершения
    if not shutdown_event.is_set():
        for lang in lang_codes:
            lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
            dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

            final_lang_data = read_json(lang_path).get(lang, {})
            final_dump_data = read_json(dump_path_)

            final_lang_data = sync_structure(main_data, final_lang_data, lang)
            final_dump_data[lang] = sync_dump_structure(main_data, final_dump_data.get(lang, {}), final_lang_data)

            write_json(lang_path, {lang: sort_dict_by_reference(final_lang_data, main_data)})
            write_json(dump_path_, final_dump_data)

    if shutdown_event.is_set():
        print("[INFO] Прервано пользователем.")
    else:
        print("[INFO] Перевод успешно завершен.")

if __name__ == '__main__':
    main()