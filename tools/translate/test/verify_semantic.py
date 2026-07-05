import json
import os
import re
import sys
import time
import queue
from threading import Thread, Lock
from openai import OpenAI
import logging
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Silence third-party logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Setup terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Configure stdout encoding on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Constants
MODEL_NAME = "openrouter/free"
BATCH_SIZE = 15

# Retrieve API keys
raw_keys = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]
if not OPENROUTER_API_KEYS:
    print(f"{RED}[ERROR] OPENROUTER_API_KEY not found in .env!{RESET}")
    sys.exit(1)

# Threading locks
file_lock = Lock()
results_lock = Lock()

def should_skip_translation(val):
    if not isinstance(val, str):
        return True
    val_strip = val.strip()
    if not val_strip:
        return True
    if val_strip.lower() in ["true", "false"]:
        return True
    # Strip emojis, punctuation, spaces, numbers, and check if anything remains.
    no_emoji_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf\s\d\W_]', '', val_strip)
    if not no_emoji_text:
        return True
    return False

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_flat_keys(data, prefix=""):
    flat = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}.{k}" if prefix else k
            flat.update(extract_flat_keys(v, new_key))
    elif isinstance(data, list):
        for idx, v in enumerate(data):
            new_key = f"{prefix}.{idx}" if prefix else str(idx)
            flat.update(extract_flat_keys(v, new_key))
    else:
        flat[prefix] = data
    return flat

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

def sort_dict_by_reference(data, reference):
    if isinstance(reference, dict) and isinstance(data, dict):
        return {k: sort_dict_by_reference(data[k], reference[k]) for k in reference if k in data} | {k: data[k] for k in data if k not in reference}
    if isinstance(reference, list) and isinstance(data, list):
        return [sort_dict_by_reference(data[i], reference[i]) for i in range(min(len(data), len(reference)))] + data[len(reference):]
    return data

def validate_translation(ru_val, trans_val):
    if not trans_val or trans_val == "NOTEXT":
        return False, "Empty or NOTEXT translation"
    if ru_val.count('\n') != trans_val.count('\n'):
        return False, f"Newline count mismatch: RU has {ru_val.count(chr(10))}, Translation has {trans_val.count(chr(10))}"
    ru_vars = set(re.findall(r'\{([^}]+)\}', ru_val))
    trans_vars = set(re.findall(r'\{([^}]+)\}', trans_val))
    if ru_vars != trans_vars:
        return False, f"Variable mismatch: RU has {ru_vars}, Translation has {trans_vars}"
    if re.search(r'[а-яА-ЯёЁ]', trans_val):
        return False, "Translation contains Cyrillic characters"
    return True, ""

def translate_key(client, key, ru_val, lang_name):
    system_prompt = (
        f"You are a professional localization engine for a Telegram virtual pet game called DinoGochi.\n"
        f"Task: Translate the value for key '{key}' from Russian to '{lang_name}'.\n\n"
        f"CRITICAL RULES:\n"
        f"1. You MUST return ONLY the translated string value. Never wrap it in quotes, json, or markdown blocks. Do not write explanations.\n"
        f"2. Preserve all variable placeholders inside text exactly as they are. Examples: {{name}}, {{count}}, etc.\n"
        f"3. Keep all emojis exactly in their original positions.\n"
        f"4. Maintain the exact original text formatting: newlines (\\n), trailing/leading spaces, and specific alignment/indentation (like multiple spaces).\n"
        f"5. Maintain the gaming slang and context of a virtual pet (tamagotchi) game."
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ru_val}
            ],
            extra_headers={
                "HTTP-Referer": "https://github.com/dinogochi",
                "X-Title": "DinoGochi Localization Translator"
            }
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None

def auto_fix_and_translate(client, key, ru_val, lang_name, lang_code, lang_file, dump_file, ru_data):
    """Translates a key and validates it, saving directly if correct"""
    for attempt in range(1, 4):
        trans_val = translate_key(client, key, ru_val, lang_name)
        if trans_val:
            ok, reason = validate_translation(ru_val, trans_val)
            if ok:
                with file_lock:
                    current_lang_data = load_json(lang_file).get(lang_code, {})
                    current_dump_data = load_json(dump_file)
                    
                    set_by_path(current_lang_data, key, trans_val)
                    set_by_path(current_dump_data, f"{lang_code}.{key}", ru_val)
                    
                    write_json(lang_file, {lang_code: sort_dict_by_reference(current_lang_data, ru_data)})
                    write_json(dump_file, current_dump_data)
                return True, trans_val
            else:
                time.sleep(1)
    
    # If all translation attempts failed, set to NOTEXT
    with file_lock:
        current_lang_data = load_json(lang_file).get(lang_code, {})
        current_dump_data = load_json(dump_file)
        
        set_by_path(current_lang_data, key, "NOTEXT")
        set_by_path(current_dump_data, f"{lang_code}.{key}", "NOTEXT")
        
        write_json(lang_file, {lang_code: sort_dict_by_reference(current_lang_data, ru_data)})
        write_json(dump_file, current_dump_data)
    return False, "NOTEXT"

def verify_semantic_batch(client, batch_items, lang_name):
    """Sends a batch to AI for semantic verification"""
    items_to_check = []
    for key, ru_val, trans_val in batch_items:
        items_to_check.append({
            "key": key,
            "ru": ru_val,
            "translated": trans_val
        })

    system_prompt = (
        f"You are a professional localization quality auditor. You are auditing a virtual pet (tamagotchi) Telegram game called DinoGochi.\n"
        f"Task: Compare the source Russian text ('ru') with the translated version ('translated') in language '{lang_name}'.\n"
        f"Verify if the translation is logically, semantically, and contextually correct. Identify translations that are completely wrong, nonsensical, or have wrong meaning compared to the Russian text.\n\n"
        f"CRITICAL RULES:\n"
        f"1. You MUST return ONLY a valid raw JSON object. Do not wrap it in markdown code blocks. Never include explanations outside the JSON.\n"
        f"2. Return a list of keys that fail the logical/semantic check, with a reason in English.\n"
        f"3. The text formatting (alignment, spaces, indentation) forms the structure of the message. If there are multiple spaces (e.g. 10 spaces) or specific alignment/indentation, they MUST be preserved exactly in the translation.\n"
        f"Format:\n"
        f"{{\n"
        f"  \"bad_keys\": [\n"
        f"    {{\"key\": \"item_names.brokenkey.name\", \"reason\": \"Translated as a musical key instead of a door key\"}}\n"
        f"  ]\n"
        f"}}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(items_to_check, ensure_ascii=False)}
            ],
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": "https://github.com/dinogochi",
                "X-Title": "DinoGochi Localization Auditor"
            }
        )
        res_text = response.choices[0].message.content.strip()
        res_text = re.sub(r'^```json\s*|\s*```$', '', res_text, flags=re.IGNORECASE).strip()
        data = json.loads(res_text)
        return data.get("bad_keys", [])
    except Exception as e:
        return []

def worker_lifecycle(task_queue, progress_bar, client, client_idx, lang_name, lang_code, lang_file, dump_file, ru_data, results_list, should_fix):
    while not task_queue.empty():
        try:
            task = task_queue.get_nowait()
        except queue.Empty:
            break
        
        if task["type"] == "translate":
            key = task["key"]
            ru_val = task["ru_val"]
            with results_lock:
                print(f"\n    {YELLOW}⚙ [Поток-{client_idx}] Перевод на лету:{RESET} {key}")
            success, val = auto_fix_and_translate(client, key, ru_val, lang_name, lang_code, lang_file, dump_file, ru_data)
            if success:
                with results_lock:
                    print(f"      {GREEN}✓ Успешно переведено:{RESET} {key} -> {repr(val)}")
            else:
                with results_lock:
                    print(f"      {RED}❌ Ошибка перевода для:{RESET} {key}")
                    
        elif task["type"] == "verify":
            batch = task["batch"]
            bad_keys = verify_semantic_batch(client, batch, lang_name)
            if bad_keys:
                with results_lock:
                    for item in bad_keys:
                        print(f"\n    {RED}❌ Семантическая ошибка в {lang_code.upper()}:{RESET} {item.get('key')} - {item.get('reason')}")
                        results_list.append(item)

                if should_fix:
                    for item in bad_keys:
                        key = item.get('key')
                        ru_val = next((r for k, r, t in batch if k == key), None)
                        if ru_val:
                            with results_lock:
                                print(f"      {YELLOW}⚙ [Поток-{client_idx}] Исправление семантики:{RESET} {key}")
                            success, val = auto_fix_and_translate(client, key, ru_val, lang_name, lang_code, lang_file, dump_file, ru_data)
                            if success:
                                with results_lock:
                                    print(f"        {GREEN}✓ Исправлено:{RESET} {key} -> {repr(val)}")
                            else:
                                with results_lock:
                                    print(f"        {RED}❌ Ошибка исправления:{RESET} {key}")
        
        progress_bar.update(1)
        task_queue.task_done()

def main():
    should_fix = "--fix" in sys.argv
    print(f"{YELLOW}=== Starting AI Semantic Localization Quality Verification ==={RESET}\n")

    translate_dir = os.path.dirname(__file__)
    settings_path = os.path.join(translate_dir, "settings.json")
    with open(settings_path, encoding='utf-8') as f:
        settings = json.load(f)

    langs_dir = os.path.normpath(os.path.join(translate_dir, settings.get("langs_path", "../../bot/localization")))
    dump_dir = os.path.normpath(os.path.join(translate_dir, settings.get("dump_path", "./dumps/")))
    ru_path = os.path.join(langs_dir, "ru.json")
    
    ru_data = load_json(ru_path).get("ru", {})
    if not ru_data:
        print(f"{RED}[ERROR] Russian source not found!{RESET}")
        sys.exit(1)
        
    ru_flat = extract_flat_keys(ru_data)
    target_langs = {"en": "English", "es": "Spanish", "id": "Indonesian"}

    # Initialize OpenAI clients using the available API keys with strict timeout
    clients = [OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1", timeout=12.0) for key in OPENROUTER_API_KEYS]
    num_workers = len(clients)

    for lang_code, lang_name in target_langs.items():
        lang_file = os.path.join(langs_dir, f"{lang_code}.json")
        lang_data = load_json(lang_file).get(lang_code, {})
        dump_file = os.path.join(dump_dir, f"{lang_code}.json")
        dump_data = load_json(dump_file)

        if not lang_data:
            continue

        lang_flat = extract_flat_keys(lang_data)
        
        # Prepare lists for thread pool
        translate_tasks = []
        verify_items = []
        bad_results = []
        
        for key, ru_val in ru_flat.items():
            if not isinstance(ru_val, str):
                continue
            
            if should_skip_translation(ru_val):
                trans_val = lang_flat.get(key)
                if trans_val != ru_val and should_fix:
                    with file_lock:
                        current_lang_data = load_json(lang_file).get(lang_code, {})
                        current_dump_data = load_json(dump_file)
                        set_by_path(current_lang_data, key, ru_val)
                        set_by_path(current_dump_data, f"{lang_code}.{key}", ru_val)
                        write_json(lang_file, {lang_code: sort_dict_by_reference(current_lang_data, ru_data)})
                        write_json(dump_file, current_dump_data)
                continue

            trans_val = lang_flat.get(key)
            
            # If missing or NOTEXT, it goes directly to translate queue (if fix mode)
            if not trans_val or trans_val == "NOTEXT":
                if should_fix:
                    translate_tasks.append({"type": "translate", "key": key, "ru_val": ru_val})
                else:
                    bad_results.append({"key": key, "reason": "Missing or NOTEXT translation"})
                continue

            # Check existing formatting
            ok, reason = validate_translation(ru_val, trans_val)
            if not ok:
                if should_fix:
                    translate_tasks.append({"type": "translate", "key": key, "ru_val": ru_val})
                else:
                    bad_results.append({"key": key, "reason": reason})
                continue

            # Otherwise, verify semantically
            verify_items.append((key, ru_val, trans_val))

        # Chunk verify items into batches
        batches = [verify_items[i:i + BATCH_SIZE] for i in range(0, len(verify_items), BATCH_SIZE)]
        verify_tasks = [{"type": "verify", "batch": b} for b in batches]

        all_tasks = translate_tasks + verify_tasks

        if not all_tasks and not bad_results:
            print(f"No translated keys to verify for {lang_name}.")
            continue

        print(f"\n{YELLOW}Verifying {lang_name.upper()} ({len(translate_tasks)} keys to translate, {len(verify_tasks)} batches to verify)...{RESET}")

        if all_tasks:
            # Set up queue and thread safety structures
            task_queue = queue.Queue()
            for task in all_tasks:
                task_queue.put(task)

            # Progress bar
            with tqdm(total=len(all_tasks), desc="Auditing") as pbar:
                threads = []
                for idx in range(num_workers):
                    client = clients[idx]
                    t = Thread(
                        target=worker_lifecycle,
                        args=(task_queue, pbar, client, idx, lang_name, lang_code, lang_file, dump_file, ru_data, bad_results, should_fix),
                        daemon=True
                    )
                    t.start()
                    threads.append(t)
                    time.sleep(1.5)

                for t in threads:
                    t.join()

        # Output final count
        if bad_results:
            print(f"  {RED}❌ Total semantic/formatting errors found: {len(bad_results)}{RESET}")
        else:
            print(f"  {GREEN}✓ All translations are semantically correct!{RESET}")

    print(f"\n{GREEN}AI Semantic audit complete!{RESET}")

if __name__ == "__main__":
    main()
