import json
import os
import re
import sys

# Configure stdout to handle unicode properly on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Setup colors for nice terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Regex patterns
VARIABLE_PATTERN = re.compile(r'\{([^}]+)\}')
EMOJI_PATTERN = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf]')
ARABIC_PATTERN = re.compile(r'[\u0600-\u06ff\u0750-\u077f\ufb50-\ufbc1\ufbd3-\ufd3f\ufd50-\ufdfd\ufe70-\ufefc]')

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

def verify_translations():
    should_fix = "--fix" in sys.argv
    if should_fix:
        print(f"{YELLOW}=== Running in FIX mode. Incorrect keys will be overwritten with NOTEXT ==={RESET}\n")
    else:
        print(f"{YELLOW}=== Starting Translation Quality Verification ==={RESET}\n")

    # Load settings to get correct paths
    translate_dir = os.path.dirname(__file__)
    settings_path = os.path.join(translate_dir, "settings.json")
    if not os.path.exists(settings_path):
        print(f"{RED}[ERROR] settings.json not found!{RESET}")
        sys.exit(1)
        
    with open(settings_path, encoding='utf-8') as f:
        settings = json.load(f)
    
    langs_path = settings.get("langs_path", "bot/localization/{lang}.json")
    langs_dir = os.path.normpath(os.path.join(translate_dir, settings.get("langs_path", "../../bot/localization")))
    dump_dir = os.path.normpath(os.path.join(translate_dir, settings.get("dump_path", "./dumps/")))
    ru_path = os.path.join(langs_dir, "ru.json")
    
    ru_data = load_json(ru_path).get("ru", {})
    if not ru_data:
        print(f"{RED}[ERROR] Russian source translation is empty or not found at {ru_path}{RESET}")
        sys.exit(1)
        
    ru_flat = extract_flat_keys(ru_data)
    print(f"Loaded {len(ru_flat)} keys from Russian source (ru.json).")

    target_langs = ["en", "es", "id"]
    has_errors = False

    for lang in target_langs:
        lang_file = os.path.join(langs_dir, f"{lang}.json")
        lang_data = load_json(lang_file).get(lang, {})
        dump_file = os.path.join(dump_dir, f"{lang}.json")
        dump_data = load_json(dump_file)
        
        if not lang_data:
            print(f"{YELLOW}[WARNING] Target language {lang} is empty or not found at {lang_file}{RESET}")
            continue

        lang_flat = extract_flat_keys(lang_data)
        print(f"\nVerifying {YELLOW}{lang.upper()}{RESET} ({len(lang_flat)} keys)...")
        
        errors = []
        warnings = []
        bad_keys = set()

        for key, ru_val in ru_flat.items():
            if not isinstance(ru_val, str):
                continue
                
            trans_val = lang_flat.get(key)
            if trans_val is None:
                errors.append((key, "Missing key in target translation"))
                bad_keys.add(key)
                continue
                
            if not isinstance(trans_val, str):
                continue

            if trans_val == "NOTEXT":
                warnings.append((key, "Flagged as NOTEXT"))
                continue

            # 1. Check placeholder variables mismatch
            ru_vars = set(VARIABLE_PATTERN.findall(ru_val))
            trans_vars = set(VARIABLE_PATTERN.findall(trans_val))
            if ru_vars != trans_vars:
                errors.append((key, f"Variable mismatch. RU: {ru_vars} | {lang.upper()}: {trans_vars}"))
                bad_keys.add(key)
                continue

            # 2. Check for Arabic/unexpected characters
            if ARABIC_PATTERN.search(trans_val) and not ARABIC_PATTERN.search(ru_val):
                errors.append((key, f"Unexpected Arabic characters found: {repr(trans_val)}"))
                bad_keys.add(key)
                continue

            # 3. Check for emoji loss
            ru_emojis = set(EMOJI_PATTERN.findall(ru_val))
            trans_emojis = set(EMOJI_PATTERN.findall(trans_val))
            missing_emojis = ru_emojis - trans_emojis
            if missing_emojis:
                warnings.append((key, f"Missing emojis from source: {''.join(missing_emojis)}"))
                bad_keys.add(key)

        # Print report for current language
        if errors:
            has_errors = True
            print(f"  {RED}❌ Errors found ({len(errors)}):{RESET}")
            for k, msg in errors[:20]:
                print(f"    - {k}: {msg}")
            if len(errors) > 20:
                print(f"    ... and {len(errors) - 20} more errors.")
        else:
            print(f"  {GREEN}✓ No critical errors found.{RESET}")

        if warnings:
            print(f"  {YELLOW}⚠ Warnings ({len(warnings)}):{RESET}")
            for k, msg in warnings[:10]:
                print(f"    - {k}: {msg}")
            if len(warnings) > 10:
                print(f"    ... and {len(warnings) - 10} more warnings.")

        # Apply fixes if flag is active
        if should_fix and bad_keys:
            print(f"  {GREEN}⚙ Overwriting {len(bad_keys)} bad/warned keys with NOTEXT...{RESET}")
            for key in bad_keys:
                set_by_path(lang_data, key, "NOTEXT")
                set_by_path(dump_data, f"{lang}.{key}", "NOTEXT")
            
            write_json(lang_file, {lang: sort_dict_by_reference(lang_data, ru_data)})
            write_json(dump_file, dump_data)

    print(f"\n{YELLOW}================================================={RESET}")
    if not should_fix and has_errors:
        print(f"{RED}Verification failed. Some keys have critical translation errors.{RESET}")
        sys.exit(1)
    elif should_fix:
        print(f"{GREEN}Fix complete! All bad keys have been marked as NOTEXT in translations and dumps.{RESET}")
    else:
        print(f"{GREEN}Verification successful! All translations look healthy.{RESET}")

if __name__ == "__main__":
    verify_translations()
