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
from openai import OpenAI
from threading import Thread, Lock, Event

from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Настройка логов
logger = logging.getLogger()
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

# Загрузка настроек
with open(os.path.join(ex, 'settings.json'), encoding='utf-8') as f: 
    settings = json.load(f)
    main_code = settings['main_code']
    langs_path = settings['langs_path']
    dump_path = settings['dump_path']
    ignore_translate_keys = settings['ignore_translate_keys']
    no_edit = settings['no_edit']

# Поддержка нескольких API-ключей через запятую
raw_keys = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Используем автоподбор или конкретную модель
MODEL_NAME = "openrouter/free" 

# Лимит символов на один пакет
MAX_BATCH_CHAR_LIMIT = 1500

if not OPENROUTER_API_KEYS:
    print("[ERROR] Не найдены токены OPENROUTER_API_KEY в файле .env!")
    sys.exit(1)

print(f"[INFO] Загружено API-ключей: {len(OPENROUTER_API_KEYS)}.")

file_lock = Lock()  # Блокировка для безопасной записи в файлы из разных потоков
print_lock = Lock() # Блокировка для красивого вывода в консоль

# Глобальный флаг для мягкой остановки
shutdown_event = Event()

def only_translate_batch(client, client_idx, batch_items, from_language, to_language):
    if shutdown_event.is_set():
        return None, False

    payload = {item[0]: item[1] for item in batch_items}

    system_prompt = (
        f"You are a professional localization engine for a Telegram bot DinoGochi.\n"
        f"Task: Translate the values inside the provided JSON object from '{from_language}' to '{to_language}'.\n\n"
        f"CRITICAL RULES:\n"
        f"1. Output ONLY a valid raw JSON object containing the translations. Do not wrap it in markdown codeblocks (like ```json). Never include explanations, greetings, or commentary.\n"
        f"2. Keep the original keys exactly as they are in the input JSON.\n"
        f"3. Preserve all variable placeholders inside text exactly as they are. Examples: {{name}}, {{count}}, #1042#, /start, <b>, </b>, etc. Do not translate or format them.\n"
        f"4. Keep all emojis exactly in their original positions.\n"
        f"5. Maintain the exact original structure, line breaks (\\n), trailing/leading spaces, and markdown style (**bold**, _italic_).\n"
        f"6. Maintain the gaming slang and context of a virtual pet (tamagotchi) game."
    )

    try:
        with print_lock:
            print(f"\n[Поток-{client_idx}] Отправка пакета на перевод ({len(batch_items)} ключей)...")
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
                "HTTP-Referer": "[https://github.com/dinogochi](https://github.com/dinogochi)", 
                "X-Title": "DinoGochi Localization Engine"
            }
        )
        
        if shutdown_event.is_set():
            return None, False

        res_text = response.choices[0].message.content.strip()
        res_text = re.sub(r'^```json\s*|\s*```$', '', res_text, flags=re.IGNORECASE).strip()
        json_match = re.search(r'(\{.*\})', res_text, re.DOTALL)
        if json_match:
            res_text = json_match.group(1).strip()
        else:
            with print_lock:
                logger.error(f"\n[Поток-{client_idx}] [ERROR] Модель вернула текст вместо JSON: {res_text[:150]}")
            return None, False
            
        data = json.loads(res_text)
        
        with print_lock:
            print(f"\n[Поток-{client_idx}] Успешно получен перевод:")
            for path, _ in batch_items[:3]:
                translated = data.get(path, "NOTEXT")
                print(f"  <- [{path}]: {repr(translated)}")
            if len(batch_items) > 3:
                print(f"  ... всего переведено строк: {len(data)}")
                
        return data, False

    except json.JSONDecodeError:
        with print_lock:
            logger.error(f"\n[Поток-{client_idx}] [ERROR] Ошибка парсинга JSON. Ответ модели: {res_text[:200]}")
        return None, False
    except Exception as e:
        is_rate_limit = False
        err_msg = str(e)
        if "429" in err_msg or "Rate limit exceeded" in err_msg or "rate-limited" in err_msg:
            is_rate_limit = True
            with print_lock:
                logger.critical(f"\n[Поток-{client_idx}] [RATE LIMIT 429] Токен исчерпал лимит! Отключаем поток.")
        else:
            with print_lock:
                logger.error(f"\n[Поток-{client_idx}] [API ERROR]: {e}")
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

def build_structure(data):
    if isinstance(data, dict): return {k: build_structure(v) for k, v in data.items()}
    if isinstance(data, list): return [build_structure(v) for v in data]
    return 'NOTEXT'

def worker_lifecycle(task_queue, progress_bar, client, client_idx, lang, lang_path, dump_path_, main_data):
    # Небольшая задержка перед стартом воркеров
    time.sleep(random.uniform(1.0, 3.0))

    while not shutdown_event.is_set():
        try:
            # Получаем задачу без блокировки на вечность, чтобы чекать shutdown_event
            batch = task_queue.get(timeout=1)
        except queue.Empty:
            break

        rep = 0
        success = False
        killed_by_429 = False

        while rep < 5 and not success and not shutdown_event.is_set():
            translated_dict, is_rate_limit = only_translate_batch(client, client_idx, batch, main_code, lang)
            
            if is_rate_limit:
                # Возвращаем задачу обратно в начало очереди и завершаем работу воркера
                task_queue.put(batch)
                killed_by_429 = True
                break

            if shutdown_event.is_set():
                break

            if translated_dict and isinstance(translated_dict, dict):
                with file_lock:
                    lang_data_current = read_json(lang_path).get(lang, {})
                    dump_data_current = read_json(dump_path_)

                    for path, orig_value in batch:
                        translated_value = translated_dict.get(path, "NOTEXT")
                        set_by_path(lang_data_current, path, translated_value)
                        set_by_path(dump_data_current, f'{lang}.'+path, orig_value if translated_value != "NOTEXT" else "NOTEXT")
                    
                    write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                    write_json(dump_path_, dump_data_current)
                    
                success = True
                progress_bar.update(1)
            else:
                rep += 1
                wait_time = (2 ** rep) * 5 + random.uniform(1.0, 3.0)
                with print_lock:
                    print(f"\n[Поток-{client_idx}][RETRY] Ошибка пакета. Попытка {rep}/5. Пауза {wait_time:.1f} сек...")
                
                for _ in range(int(wait_time * 2)):
                    if shutdown_event.is_set():
                        break
                    time.sleep(0.5)

        if killed_by_429:
            task_queue.task_done()
            break  # Выходим из жизненного цикла текущего потока (он закрыт)

        if not success and not shutdown_event.is_set():
            with file_lock:
                lang_data_current = read_json(lang_path).get(lang, {})
                dump_data_current = read_json(dump_path_)
                for path, _ in batch:
                    set_by_path(lang_data_current, path, "NOTEXT")
                    set_by_path(dump_data_current, f'{lang}.'+path, "NOTEXT")
                write_json(lang_path, {lang: sort_dict_by_reference(lang_data_current, main_data)})
                write_json(dump_path_, dump_data_current)
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
    if lang_arg: lang_codes = [l for l in lang_codes if l == lang_arg]

    for lang in lang_codes:
        if shutdown_event.is_set():
            break

        print(f"\n=== Перевод через OpenRouter [{MODEL_NAME}]: {lang} ===")
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

            if current_batch_chars + len(value) > MAX_BATCH_CHAR_LIMIT and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_batch_chars = 0

            current_batch.append((path, value))
            current_batch_chars += len(value)

        if current_batch:
            batches.append(current_batch)

        write_json(lang_path, {lang: sort_dict_by_reference(lang_data, main_data)})
        write_json(dump_path_, dump_data)

        if not batches:
            print("[INFO] Нет изменений для перевода.")
            continue

        # Заполняем потокобезопасную очередь задач
        task_queue = queue.Queue()
        for batch in batches:
            task_queue.put(batch)

        # Пересоздаем список активных API клиентов
        clients_pool = [OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL) for key in OPENROUTER_API_KEYS]
        num_threads = len(clients_pool)
        
        print(f"[INFO] Запускаем {num_threads} потока(ов) для обработки {len(batches)} пакетов...")
        
        with tqdm(total=len(batches), desc="Общий прогресс пакетов") as pbar:
            threads = []
            for idx, client in enumerate(clients_pool):
                t = Thread(
                    target=worker_lifecycle,
                    args=(task_queue, pbar, client, idx + 1, lang, lang_path, dump_path_, main_data)
                )
                t.start()
                threads.append(t)

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

    if shutdown_event.is_set():
        print("[INFO] Выполнение скрипта прервано. Состояние сохранено.")
    else:
        print("[INFO] Перевод успешно завершен.")

if __name__ == '__main__':
    main()