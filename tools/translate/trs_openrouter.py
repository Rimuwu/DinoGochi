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
from openai import OpenAI
from threading import Thread, Lock, Event

from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Настройка логов
logger = logging.getLogger("trs_openrouter")
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

# Отключаем спам-логи от http/api библиотек
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Загрузка настроек
with open(os.path.join(ex, 'settings.json'), encoding='utf-8') as f: 
    settings = json.load(f)
    main_code = settings['main_code']
    langs_path = settings['langs_path']
    dump_path = settings['dump_path']
    ignore_translate_keys = settings['ignore_translate_keys']
    ignore_path_entries = settings.get('ignore_path_entries', [])
    no_edit = settings['no_edit']

# Цветовая разметка вывода в консоль
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"

# Поддержка нескольких API-ключей через запятую
raw_keys = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

def should_skip_translation(val):
    if not isinstance(val, str):
        return True
    val_strip = val.strip()
    if not val_strip:
        return True
    if val_strip.lower() in ["true", "false", "notext"]:
        return True
    # Strip emojis, punctuation, spaces, numbers, and check if anything remains.
    no_emoji_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf\s\d\W_]', '', val_strip)
    if not no_emoji_text:
        return True
    return False

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

def should_ignore_path_entry(path, ignore_path_entries):
    """Returns True if path starts with any prefix from ignore_path_entries."""
    for entry in ignore_path_entries:
        if path == entry or path.startswith(entry + '.'):
            return True
    return False

# Используем автоподбор или конкретную модель
MODEL_NAME = "openrouter/free" 

# Лимит символов на один пакет
MAX_BATCH_CHAR_LIMIT = 2000

if not OPENROUTER_API_KEYS:
    print(f"{COLOR_RED}[ERROR] Не найдены токены OPENROUTER_API_KEY в файле .env!{COLOR_RESET}")
    sys.exit(1)

print(f"[INFO] Загружено API-ключей: {len(OPENROUTER_API_KEYS)}.")

file_lock = Lock()  # Блокировка для безопасной записи в файлы из разных потоков
print_lock = Lock() # Блокировка для красивого вывода в консоль

# Глобальный флаг для мягкой остановки
shutdown_event = Event()

def repair_and_extract_json(text):
    """Attempts to salvage key-value translation pairs from incomplete/broken JSON strings."""
    try:
        return json.loads(text)
    except Exception:
        pass
    
    extracted = {}
    pattern = r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"'
    matches = re.findall(pattern, text)
    for k, v in matches:
        try:
            extracted[k] = json.loads(f'"{v}"')
        except Exception:
            extracted[k] = v
    return extracted

def only_translate_batch(client, client_idx, batch_items, from_language, to_language):
    if shutdown_event.is_set():
        return None, False

    payload = {item[0]: item[1] for item in batch_items}

    system_prompt = (
        f"You are a professional localization engine for a Telegram bot DinoGochi.\n"
        f"Task: Translate the values inside the provided JSON object from '{from_language}' to '{to_language}'.\n\n"
        f"CRITICAL RULES:\n"
        f"You are a translation API. You must translate game localization strings from language code '{from_language}' to '{to_language}'.\n"
        "Rules:\n"
        "1. Return ONLY a valid JSON object map.\n"
        "2. Do NOT add any markdown formatting (like ```json), explanations, or notes.\n"
        "3. Keep all key names exactly as they are in the input JSON.\n"
        "4. Keep variable placeholders in curly braces like {dino}, {name}, {count} exactly the same (translate the rest of the text).\n"
        "5. Preserve original formatting, emojis, line breaks (\\n), and tags.\n"
        "6. Do NOT translate technical strings, codes, or IDs.\n"
        "7. Ensure translation sounds natural and fits the game context.\n"
        "8. Double check that your output JSON is fully valid and not truncated.\n"
        f"9. Note that text inside angle brackets representing command parameter hints (e.g. <тип_квеста>, <userid>) is NOT an HTML formatting tag and MUST be translated into the target language (e.g. to <quest_type>, <userid>)."
    )

    res_text = ""  # Initialize so JSONDecodeError handler never hits UnboundLocalError
    try:
        with print_lock:
            print(f"\n{COLOR_CYAN}[Поток-{client_idx}][{to_language.upper()}] Отправка пакета на перевод ({len(batch_items)} ключей)...{COLOR_RESET}")
            for path, val in batch_items[:3]: 
                print(f"  -> [{path}]: {repr(val)}")
            if len(batch_items) > 3:
                print(f"  ... и еще {len(batch_items) - 3} ключей.")

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
            ],
            response_format={"type": "json_object"}, 
            timeout=50,
            extra_headers={
                "HTTP-Referer": "https://github.com/dinogochi", 
                "X-Title": "DinoGochi Localization Engine"
            }
        )
        
        if shutdown_event.is_set():
            return None, False

        content = response.choices[0].message.content
        if content is None:
            with print_lock:
                logger.error(f"\n{COLOR_RED}[Поток-{client_idx}][{to_language.upper()}] [ERROR] Ответ модели пуст (None content){COLOR_RESET}")
            return None, False
        res_text = content.strip()
        res_text = re.sub(r'^```json\s*|\s*```$', '', res_text, flags=re.IGNORECASE).strip()
        json_match = re.search(r'(\{.*\})', res_text, re.DOTALL)
        if json_match:
            res_text = json_match.group(1).strip()
        else:
            # Try to find a partial JSON structure starting with {
            brace_idx = res_text.find('{')
            if brace_idx != -1:
                res_text = res_text[brace_idx:]
            else:
                with print_lock:
                    logger.error(f"\n{COLOR_RED}[Поток-{client_idx}][{to_language.upper()}] [ERROR] Модель вернула текст вместо JSON: {res_text[:150]}{COLOR_RESET}")
                return None, False
            
        try:
            data = json.loads(res_text)
        except Exception:
            data = repair_and_extract_json(res_text)
            if not data:
                raise json.JSONDecodeError("Failed to parse or repair JSON", res_text, 0)
            with print_lock:
                print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{to_language.upper()}] [WARNING] JSON поврежден, но удалось восстановить {len(data)}/{len(batch_items)} ключей.{COLOR_RESET}")
        
        with print_lock:
            print(f"\n{COLOR_GREEN}[Поток-{client_idx}][{to_language.upper()}] Успешно получен перевод:{COLOR_RESET}")
            for path, _ in batch_items[:3]:
                translated = data.get(path, "NOTEXT")
                print(f"  <- [{path}]: {repr(translated)}")
            if len(batch_items) > 3:
                print(f"  ... всего переведено строк: {len(data)}")
                
        return data, False

    except json.JSONDecodeError:
        with print_lock:
            logger.error(f"\n{COLOR_RED}[Поток-{client_idx}][{to_language.upper()}] [ERROR] Ошибка парсинга JSON. Ответ модели: {res_text[:200]}{COLOR_RESET}")
        return None, False
    except Exception as e:
        is_rate_limit = False
        err_msg = str(e)
        if "429" in err_msg or "Rate limit exceeded" in err_msg or "rate-limited" in err_msg:
            # Distinguish daily limit (unrecoverable) from per-second rate limit (retryable)
            if "free-models-per-day" in err_msg or "per-day" in err_msg:
                is_rate_limit = "FATAL"  # Daily limit exhausted — don't retry
            else:
                is_rate_limit = True
            with print_lock:
                logger.warning(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{to_language.upper()}] [429] Ответ API: {err_msg[:300]}{COLOR_RESET}")
        else:
            with print_lock:
                logger.error(f"\n{COLOR_RED}[Поток-{client_idx}][{to_language.upper()}] [API ERROR]: {e}{COLOR_RESET}")
        return None, is_rate_limit

def read_json(path):
    if not os.path.exists(path): return {}
    with open(path, encoding='utf-8') as f: return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def set_by_path(dct, path, value):
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

def get_by_path(dct, path):
    keys = path.split('.')
    cur = dct
    for k in keys:
        if isinstance(cur, list) and k.isdigit():
            cur = cur[int(k)] if int(k) < len(cur) else None
        else: cur = cur.get(k) if isinstance(cur, dict) else None
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

    # 9. Foreign scripts check (Armenian, Hebrew, Arabic, Indic, Thai, Georgian, Tibetan, Myanmar, Mongolian, Khmer, etc.)
    contains_foreign_script = bool(re.search(r'[\u0530-\u1CFF\u1E00-\u1FFF\ufb50-\ufd3f\ufd50-\ufdfd\ufe70-\ufefc]', trans_str))
    if contains_foreign_script:
        found = ''.join(set(re.findall(r'[\u0530-\u1CFF\u1E00-\u1FFF\ufb50-\ufd3f\ufd50-\ufdfd\ufe70-\ufefc]', trans_str)))
        return False, f"Foreign script characters found: '{found}'"

    # 10. Hieroglyphs / CJK characters check
    contains_hieroglyphs = bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', trans_str))
    if contains_hieroglyphs:
        return False, "Hieroglyphs / CJK characters found"

    return True, ""

def sync_structure(base, target, lang, path=""):
    if isinstance(base, dict):
        res = {}
        for k, v in base.items():
            new_path = f"{path}.{k}" if path else k
            target_v = target.get(k) if isinstance(target, dict) else None
            is_no_edit = k in no_edit or (path and path.split('.')[-1] in no_edit)
            if is_no_edit:
                res[k] = target_v if target_v is not None else v
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

def sync_dump_structure(base, target, path=""):
    if isinstance(base, dict):
        res = {}
        for k, v in base.items():
            new_path = f"{path}.{k}" if path else k
            target_v = target.get(k) if isinstance(target, dict) else None
            res[k] = sync_dump_structure(v, target_v, new_path)
        return res
    elif isinstance(base, list):
        res = []
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)
            target_v = target[idx] if (isinstance(target, list) and idx < len(target)) else None
            res.append(sync_dump_structure(v, target_v, new_path))
        return res
    else:
        if should_skip_translation(base) or (path and should_ignore_path(path, ignore_translate_keys)):
            return base
        if target is not None and target != "NOTEXT":
            return target
        return "NOTEXT"

def build_structure(data):
    if isinstance(data, dict): return {k: build_structure(v) for k, v in data.items()}
    if isinstance(data, list): return [build_structure(v) for v in data]
    return 'NOTEXT'

def worker_lifecycle(task_queue, progress_bar, client, client_idx, main_data):
    # Небольшая задержка перед стартом воркеров
    time.sleep(random.uniform(1.0, 3.0))

    consec_429 = 0          # Счётчик подряд идущих рейт-лимитов без успешного перевода
    MAX_CONSEC_429 = 10     # Порог отключения токена

    while not shutdown_event.is_set():
        try:
            item = task_queue.get(timeout=1)
        except queue.Empty:
            break

        lang, lang_path, dump_path_, batch = item
        rep = 0
        success = False
        killed_by_429 = False

        batch = list(batch)  # Преобразуем в список для изменения при ретраях
        while rep < 5 and batch and not success and not shutdown_event.is_set():
            translated_dict, is_rate_limit = only_translate_batch(client, client_idx, batch, main_code, lang)
            
            if is_rate_limit == "FATAL":
                # Daily limit exhausted — kill this worker immediately
                with print_lock:
                    print(f"\n{COLOR_RED}[Поток-{client_idx}] Токен отключён: суточный лимит запросов исчерпан (free-models-per-day).{COLOR_RESET}")
                task_queue.put(item)  # Return batch to queue for other workers
                return

            if is_rate_limit:
                consec_429 += 1
                task_queue.put(item)
                wait_time = random.uniform(15.0, 25.0)
                with print_lock:
                    print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{lang.upper()}][RATE LIMIT 429] Токен исчерпал лимит запросов в секунду. Спим {wait_time:.1f} сек. и пробуем снова... ({consec_429}/{MAX_CONSEC_429}){COLOR_RESET}")
                if consec_429 >= MAX_CONSEC_429:
                    with print_lock:
                        print(f"\n{COLOR_RED}[Поток-{client_idx}] Токен отключён: {MAX_CONSEC_429} рейт-лимитов подряд без единого успешного перевода.{COLOR_RESET}")
                    return  # Завершаем воркер полностью
                for _ in range(int(wait_time * 2)):
                    if shutdown_event.is_set():
                        break
                    time.sleep(0.5)
                break  # Выходим из цикла ретраев для этого пакета, так как он вернулся в очередь

            if shutdown_event.is_set():
                break

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
                    if len(bad_paths) <= 2:
                        # Too few keys to warrant an immediate retry (conserves API rate limits)
                        with file_lock:
                            lang_data_current = read_json(lang_path).get(lang, {})
                            dump_data_current = read_json(dump_path_)
                            for path in bad_paths:
                                set_by_path(lang_data_current, path, "NOTEXT")
                                set_by_path(dump_data_current, f'{lang}.'+path, "NOTEXT")
                            write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                            write_json(dump_path_, dump_data_current)
                        with print_lock:
                            print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{lang.upper()}] Пропущено {len(bad_paths)} некачественных ключей (слишком малый батч для ретрая, отложено).{COLOR_RESET}")
                        success = True
                        progress_bar.update(1)
                    elif rep < 4:
                        rep += 1
                        # Оставляем в батче только ошибочные ключи
                        batch = [item for item in batch if item[0] in bad_paths]
                        wait_time = (2 ** rep) * 5 + random.uniform(1.0, 3.0)
                        with print_lock:
                            print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{lang.upper()}][RETRY] Некачественный перевод для:")
                            for p in bad_paths:
                                print(f"  -> [{p}] Ошибка: {reasons[p]}")
                            print(f"Повторная отправка только ошибочных ключей ({len(batch)} шт.). Попытка {rep}/5. Пауза {wait_time:.1f} сек...{COLOR_RESET}")
                        for _ in range(int(wait_time * 2)):
                            if shutdown_event.is_set():
                                break
                            time.sleep(0.5)
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
                    wait_time = (2 ** rep) * 5 + random.uniform(1.0, 3.0)
                    with print_lock:
                        print(f"\n{COLOR_YELLOW}[Поток-{client_idx}][{lang.upper()}][RETRY] Ошибка пакета. Попытка {rep}/5. Пауза {wait_time:.1f} сек...{COLOR_RESET}")
                    for _ in range(int(wait_time * 2)):
                        if shutdown_event.is_set():
                            break
                        time.sleep(0.5)
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

        task_queue.task_done()

def main():
    def handle_signal(signum, frame):
        with print_lock:
            print("\n[INFO] Получен сигнал отмены (Ctrl+C). Корректно завершаем активные пакеты...")
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
        if shutdown_event.is_set():
            break

        print(f"\n=== Подготовка локализации [{MODEL_NAME}]: {lang} ===")
        lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
        dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

        lang_data = read_json(lang_path).get(lang, {})
        dump_data = read_json(dump_path_)

        # Synchronize and clean up initial files to strictly match main_data structure
        lang_data = sync_structure(main_data, lang_data, lang)
        dump_data[lang] = sync_dump_structure(main_data, dump_data.get(lang, {}))

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

        new_keys, changed_keys, deleted_keys = compare_structures(main_data, dump_data[lang])
        changed_keys = [p for p in changed_keys if not should_ignore_path(p, ignore_translate_keys)]
        new_keys = [p for p in new_keys if not should_ignore_path_entry(p, ignore_path_entries)]
        changed_keys = [p for p in changed_keys if not should_ignore_path_entry(p, ignore_path_entries)]

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

        all_main_leafs = collect_leafs(main_data)
        
        # We want to translate:
        # 1. Keys that are in new_keys or changed_keys
        # 2. Keys that have value "NOTEXT" in lang_data
        # 3. Keys that have value "NOTEXT" in dump_data[lang]
        keys_to_translate = set(new_keys + changed_keys)
        for path, orig in all_main_leafs:
            curr_val = get_by_path(lang_data, path)
            curr_dump_val = get_by_path(dump_data.get(lang, {}), path)
            if (curr_val is None or (isinstance(curr_val, str) and curr_val.strip().upper() == "NOTEXT") or
                curr_dump_val is None or (isinstance(curr_dump_val, str) and curr_dump_val.strip().upper() == "NOTEXT")):
                keys_to_translate.add(path)

        for path, orig in all_main_leafs:
            if path in keys_to_translate:
                paths_to_translate.append((path, orig))

        valid_items = []
        for path, value in paths_to_translate:
            if should_ignore_path_entry(path, ignore_path_entries):
                # Keep existing translation without re-translating
                curr_val = get_by_path(lang_data, path)
                if curr_val is not None:
                    set_by_path(dump_data, f'{lang}.'+path, curr_val)
                continue
            if should_skip_translation(value):
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue
            if should_ignore_path(path, ignore_translate_keys):
                curr_val = get_by_path(lang_data, path)
                if curr_val is not None:
                    set_by_path(dump_data, f'{lang}.'+path, curr_val)
                    continue
                set_by_path(lang_data, path, value)
                set_by_path(dump_data, f'{lang}.'+path, value)
                continue
            valid_items.append((path, value))

        to_translate_count = len(valid_items)
        print(f"[INFO] Найдено {len(paths_to_translate)} потенциальных ключей для перевода. Будет переведено: {to_translate_count}")

        # Вычисляем динамический лимит символов на пакет для распределения по всем потокам
        num_threads = len(OPENROUTER_API_KEYS) if OPENROUTER_API_KEYS else 1
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

        if current_batch:
            if lang_batches and len(current_batch) < 4:
                lang_batches[-1].extend(current_batch)
            else:
                lang_batches.append(current_batch)

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

        for b in lang_batches:
            all_batches.append((lang, lang_path, dump_path_, b))

    if not all_batches:
        print("[INFO] Нет изменений для перевода ни на один язык.")
        return

    # Заполняем потокобезопасную очередь задач
    task_queue = queue.Queue()
    for item in all_batches:
        task_queue.put(item)

    # Пересоздаем список активных API клиентов с таймаутом
    clients_pool = [OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL, timeout=12.0) for key in OPENROUTER_API_KEYS]
    num_threads = len(clients_pool)
    
    print(f"[INFO] Запускаем {num_threads} потока(ов) для обработки {len(all_batches)} пакетов по всем языкам...")
    
    with tqdm(total=len(all_batches), desc="Общий прогресс пакетов") as pbar:
        threads = []
        for idx, client in enumerate(clients_pool):
            t = Thread(
                target=worker_lifecycle,
                args=(task_queue, pbar, client, idx + 1, main_data)
            )
            t.start()
            threads.append(t)
            time.sleep(1.5)

        # Мониторим выполнение в главном потоке для работы Ctrl+C
        while any(t.is_alive() for t in threads):
            if shutdown_event.is_set():
                # Очищаем очередь, чтобы освободить простаивающие потоки
                while not task_queue.empty():
                    try:
                        task_queue.get_nowait()
                        task_queue.task_done()
                    except queue.Empty:
                        break
                break
            time.sleep(0.5)

        # Ждем завершения всех живых потоков
        for t in threads:
            t.join()

    # Финальная синхронизация для всех языков после завершения
    if not shutdown_event.is_set():
        for lang in lang_codes:
            lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
            dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

            final_lang_data = read_json(lang_path).get(lang, {})
            final_dump_data = read_json(dump_path_)

            final_lang_data = sync_structure(main_data, final_lang_data, lang)
            final_dump_data[lang] = sync_dump_structure(main_data, final_dump_data.get(lang, {}))

            write_json(lang_path, {lang: sort_dict_by_reference(final_lang_data, main_data)})
            write_json(dump_path_, final_dump_data)

    if shutdown_event.is_set():
        print("[INFO] Выполнение скрипта прервано. Состояние сохранено.")
    else:
        print("[INFO] Перевод успешно завершен.")

if __name__ == '__main__':
    main()