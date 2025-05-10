import json
import os
import g4f

# Путь к файлу локализации
ex = os.path.dirname(__file__)
lang = 'ru'
LOCALE_PATH = f"{ex}/langs/{lang}.json"
DUMP_DIR = os.path.join(ex, '/dumps')
DUMP_PATH = os.path.join(DUMP_DIR, 'ru_correct_dump.json')

# Загрузка дампа
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

def correct_string(s):
    if s in dump:
        return dump[s]

    prompt = f"Исправь орфографию и пунктуацию в этом тексте на русском языке: {s}"
    try:
        response = g4f.ChatCompletion.create(
            model='gpt-4o',
            messages=[
                {"role": "user", "content": prompt},
                {"role": "system", "content": "Ты - помощник, который исправляет ошибки в тексте. Возвращай только исправленный текст, учитывай контекст. Если текст уже исправлен - просто верни его. Английский текст не исправляй, работай только с русским текстом. Если в тексте есть эмоджи, не удаляй их, а просто исправь текст. Если в тексте есть ссылки, не удаляй их, а просто исправь текст. Если в тексте есть конструкции типа {user} - не удаляй их, а просто оставь, это места для переменных. Не всегда надо учитывать правила полностью, например. там где не стоят точки - там и не надо значит. Текст в большинстве своём правильный, но где-то есть ошибки. Исправь только ошибки, не меняй стиль текста."}
            ],
            stream=False
        )
        corrected = str(response).strip()
    except Exception as e:
        print(f'Ошибка g4f: {e}')
        corrected = s
    if corrected != s:
        print(f'Исправление строки: {s}')
        print(f'Исправленная строка: {corrected}')
    dump[s] = corrected
    save_dump()
    return corrected

def recursive_correct(obj):
    if isinstance(obj, dict):
        return {k: recursive_correct(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_correct(i) for i in obj]
    elif isinstance(obj, str):
        return correct_string(obj)
    else:
        return obj

def main():
    with open(LOCALE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    corrected = recursive_correct(data)
    with open(LOCALE_PATH, 'w', encoding='utf-8') as f:
        json.dump(corrected, f, ensure_ascii=False, indent=4)
    print('Локализация успешно исправлена!')

if __name__ == '__main__':
    main()


