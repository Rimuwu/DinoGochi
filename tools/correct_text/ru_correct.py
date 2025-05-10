import json
import os
import g4f
import time

# Путь к файлу локализации
ex = os.path.dirname(__file__)
lang = 'ru'
LOCALE_PATH = f"{ex}/langs/{lang}.json"
DUMP_DIR = f'{ex}/dumps'
DUMP_PATH = os.path.join(DUMP_DIR, 'ru_correct_dump.json')
BATCH_SIZE = 2  # Было 10, уменьшено для стабильности
SEP = '|||'  # Разделитель для батча
RETRY_COUNT = 3
RETRY_DELAY = 3  # секунд

if not os.path.exists(DUMP_DIR):
    os.makedirs(DUMP_DIR)
if os.path.exists(DUMP_PATH):
    with open(DUMP_PATH, 'r', encoding='utf-8') as f:
        dump = json.load(f)
else:
    dump = {}

def save_dump():
    with open(DUMP_PATH, 'w', encoding='utf-8') as f:
        json.dump(dump, f, ensure_ascii=False, indent=2)

def get_by_path(dct, path):
    cur = dct
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list) and isinstance(k, int) and k < len(cur):
            cur = cur[k]
        else:
            return None
    return cur

def set_by_path(dct, path, value):
    cur = dct
    for idx, k in enumerate(path[:-1]):
        next_k = path[idx + 1]
        if isinstance(k, int):
            while len(cur) <= k:
                cur.append({} if isinstance(next_k, (str, int)) else None)
            cur = cur[k]
        else:
            if k not in cur:
                cur[k] = [] if isinstance(next_k, int) else {}
            cur = cur[k]
    last = path[-1]
    if isinstance(last, int):
        while len(cur) <= last:
            cur.append(None)
        cur[last] = value
    else:
        cur[last] = value

def collect_strings(obj, path=None, result=None):
    if result is None:
        result = []
    if path is None:
        path = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            collect_strings(v, path + [k], result)
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            collect_strings(v, path + [idx], result)
    elif isinstance(obj, str):
        result.append((tuple(path), obj))
    return result

def correct_batch(strings):
    prompt = (
        f"Исправь орфографию и пунктуацию в каждом из этих текстов на русском языке. "
        f"Верни исправленные строки в том же порядке, разделяя их строкой '{SEP}'. "
        f"Если ошибок нет — верни исходное. Английский текст, эмодзи, ссылки и переменные вида {{user}} не изменяй. "
        f"Не всегда следуй правилам строго — стиль и смысл важнее. Исправляй только ошибки, не меняй стиль.\n\n"
    )
    prompt += f"\n{SEP}\n".join(strings)
    for attempt in range(RETRY_COUNT):
        try:
            response = g4f.ChatCompletion.create(
                model='gpt-4',
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            result = str(response).strip().split(SEP)
            result = [s.strip() for s in result]
            if len(result) != len(strings):
                print("⚠️  Количество строк в ответе не совпадает с исходным. Возвращаю исходные строки.")
                return strings
            print("\n--- Результаты исправления ---")
            for orig, corr in zip(strings, result):
                if orig == corr:
                    print(f"✅ Без изменений: {orig}")
                else:
                    print(f"✏️  Было: {orig}\n➡️  Стало: {corr}\n")
            print("--- Конец батча ---\n")
            return result
        except Exception as e:
            print(f'Ошибка g4f (попытка {attempt+1}/{RETRY_COUNT}): {e}')
            time.sleep(RETRY_DELAY)
    print('❌ Не удалось обработать батч после нескольких попыток, возвращаю исходные строки.')
    return strings

def main():
    with open(LOCALE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if lang in data:
        lang_data = data[lang]
    else:
        lang_data = data
    all_strings = collect_strings(lang_data)
    to_correct = [(p, s) for p, s in all_strings if get_by_path(dump, p) is None]

    print(f'Всего строк: {len(all_strings)}, новых для исправления: {len(to_correct)}')
    
    for i in range(0, len(to_correct), BATCH_SIZE):
        print(f'Обработка батча {i//BATCH_SIZE+1} из {((len(to_correct)-1)//BATCH_SIZE)+1}')
    
        batch = to_correct[i:i+BATCH_SIZE]
        batch_strings = [s for _, s in batch]
        corrected = correct_batch(batch_strings)
        for (path, orig), corr in zip(batch, corrected):
            set_by_path(dump, path, corr)
            set_by_path(lang_data, path, corr)
        save_dump()

        with open(LOCALE_PATH, 'w', encoding='utf-8') as f:
            json.dump({lang: lang_data}, f, ensure_ascii=False, indent=4)
        time.sleep(1)  # Пауза между батчами
    save_dump()
    with open(LOCALE_PATH, 'w', encoding='utf-8') as f:
        json.dump({lang: lang_data}, f, ensure_ascii=False, indent=4)
    print('Локализация успешно исправлена!')

if __name__ == '__main__':
    main()


