import json
import random
import os
import emoji
from pprint import pprint

import translators
from langdetect import DetectorFactory, detect, detect_langs
import re

DetectorFactory.seed = 0
ex = os.path.dirname(__file__) # Путь к этому файлу
langs_path = "/langs"
damp_path = "/damp_test"

base_names = {}
cash_replaces = {}

with open(f'{ex}/settings.json', encoding='utf-8') as f: 
    """ Загружаем константы из файла найстроек """
    settings = json.load(f) # type: dict

    replace_codes = settings['replace_codes']
    replace_words = settings['replace_words']
    one_replace_s = settings['one_replace_s']
    translators_names = settings['translators']

    main_code = settings['main_code']
    # langs_path = settings['langs_path']
    # damp_path = settings['damp_path']

    zero_translator = settings['zero_translator']
    ignore_translate_keys = settings['ignore_translate_keys']
    sp_sym = settings['sp_sym']

# --- Добавляем списки user_agents и proxies ---
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Добавьте больше user-agent по желанию
]
proxies = [

    # Пример: 'http://user:pass@proxy_ip:port',
    # 'http://proxy_ip:port',
    # Оставьте пустым если не используете прокси, либо добавьте свои
]

# --- Новая реализация перевода по схеме ---

def walk_keys(data, callback, path=""):
    """
    Рекурсивно обходит словарь/список и вызывает callback для каждого текстового значения.
    path — путь до ключа (через точку)
    """
    if isinstance(data, dict):
        for k, v in data.items():
            new_path = f"{path}.{k}" if path else k
            walk_keys(v, callback, new_path)
    elif isinstance(data, list):
        for idx, v in enumerate(data):
            new_path = f"{path}.{idx}" if path else str(idx)
            walk_keys(v, callback, new_path)
    else:
        callback(path, data)


def build_structure(data):
    """
    Создаёт структуру дампа: все не-словарные/не-списковые значения заменяет на 'NOTEXT'.
    """
    if isinstance(data, dict):
        return {k: build_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [build_structure(v) for v in data]
    else:
        return 'NOTEXT'


def compare_structures(base, damp, path=""):
    """
    Сравнивает структуру base (исходный словарь) и damp (дамп перевода).
    Возвращает:
      - новые ключи (есть в base, нет в damp)
      - изменённые (значения отличаются)
      - удалённые (есть в damp, нет в base)
    """
    new_keys, changed_keys, deleted_keys = [], [], []
    if isinstance(base, dict):
        base_keys = set(base.keys())
        damp_keys = set(damp.keys()) if isinstance(damp, dict) else set()

        for k in base_keys:
            new_path = f"{path}.{k}" if path else k
            if k not in damp_keys:
                new_keys.append(new_path)
            else:
                n, c, d = compare_structures(base[k], damp[k], new_path)
                new_keys += n
                changed_keys += c
                deleted_keys += d

        for k in damp_keys - base_keys:
            new_path = f"{path}.{k}" if path else k
            deleted_keys.append(new_path)

    elif isinstance(base, list) and isinstance(damp, list):
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)

            if idx >= len(damp):
                new_keys.append(new_path)
            else:
                n, c, d = compare_structures(v, damp[idx], new_path)
                new_keys += n
                changed_keys += c
                deleted_keys += d

        for idx in range(len(base), len(damp)):
            new_path = f"{path}.{idx}" if path else str(idx)
            deleted_keys.append(new_path)
    else:
        if base != damp:
            changed_keys.append(path)
    return new_keys, changed_keys, deleted_keys

def save_replace(code: int, text: str, translate: bool):
    global cash_replaces
    """
    Сохраняет замену в словаре cash_replaces.
    """
    if code not in cash_replaces:
        cash_replaces[code] = {"text": text, 
                               "translate": translate}
        return code
    else:
        return save_replace(code + 1, text, translate)

def replace_specials(text):
    # "(121)": {"text": "_", "translate": false},
    # "(801)": {"text": "</code>", "translate": false},
    #     "(800)": {"text": "<code>", "translate": false},
    #     "(901)": {"text": "<i>", "translate": false},
    #     "(900)": {"text": "</i>", "translate": false},
    #     "(700)": {"text": "<b>", "translate": false},
    #     "(701)": {"text": "</b>", "translate": false}
    """
    Заменяет спецсимволы и эмодзи на коды для защиты от перевода.
    """
    if not isinstance(text, str):
        return text
    
    for _ in range(6):
        # Заменяем спецсимволы
        for key, item in replace_words.items():
            text = text.replace(item['text'], key)

        # Прячем эмодзи
        for em in emoji.emoji_list(text):
            code = save_replace(int(ord(em['emoji'][0])), 
                                em['emoji'], False)
            text_code = f"{sp_sym}{code}{sp_sym}"
            text = text.replace(em['emoji'], text_code)

        # Прячем переменные вида {name}
        matches = re.findall(r'\{.*?\}', text)
        for match in matches:
            code = save_replace(int(ord(match[1])), 
                                match, False)
            text_code = f"{sp_sym}{code}{sp_sym}"
            text = text.replace(match, text_code)
        
        # Прячем переменные вида /слово
        matches = re.findall(r'\/[^\/]+', text)
        for match in matches:
            code = save_replace(int(ord(match[1])), 
                                match, False)
            text_code = f"{sp_sym}{code}{sp_sym}"
            text = text.replace(match, text_code)
        
        # Прячем переменные вида <b>word</b>
        matches = re.findall(r'<\s*[^<>]+\s*>', text)
        for match in matches:
            code = save_replace(int(ord(match[1])),
                    match, True)
            text_code = f"{sp_sym}{code}{sp_sym}"
            text = text.replace(match, text_code)

        # Прячем переменные вида *Слово*
        for one_repl in one_replace_s:
            tx = fr'\{one_repl}\s*.*?\s*\{one_repl}'
            matches = re.findall(tx, text)
            for match in matches:
                code = save_replace(int(ord(match[1])),
                                    match, True)
                text_code = f"{sp_sym}{code}{sp_sym}"
                text = text.replace(match, text_code)

    return text


def restore_specials(text, to_lang):
    """
    Восстанавливает спецсимволы и эмодзи после перевода.
    """
    if not isinstance(text, str):
        return text

    for key, item in replace_words.items():
        text = item['text']
        if item['translate']:
            text = translate_text(item['text'], to_lang)
        text = text.replace(key, text)

    for code, item in cash_replaces.items():
        text = item['text']
        if item['translate']:
            text = translate_text(item['text'], to_lang)

        text = text.replace(f"{sp_sym}{code}{sp_sym}", 
                            text)

    # Восстановление эмодзи (пример: #128512# -> 😀)
    # (реализация зависит от вашего подхода к кодированию эмодзи)
    return text


def translate_text(text, to_lang, trans=zero_translator):
    """
    Переводит текст, защищая спецсимволы и эмодзи.
    """
    if not isinstance(text, str) or not text.strip():
        return text
    safe_text = replace_specials(text)

    try:
        lang = detect(safe_text)
        langs = detect_langs(safe_text)
    except Exception as e:
        lang = None
        langs = []

    if lang in ['en', 'it'] and len(langs) == 1:
        translated = safe_text
        print(f"Не переводим: {text} - {lang}")

    elif lang:
        try:
            translated = translators.translate_text(safe_text, from_language=main_code, to_language=to_lang, translator=trans)
            print(safe_text, '->', translated, '\n', lang, '->', to_lang)
        except Exception as e:
            print(f"Ошибка перевода: {text} - {str(e)}")
            translated = safe_text

    else:
        translated = safe_text
        print(f"Не переведено -> {text}")
    return restore_specials(translated, to_lang)


def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def set_by_path(dct, path, value):
    """
    Устанавливает значение по пути вида 'a.b.0.c' в словаре/списке.
    """
    keys = path.split('.')
    cur = dct

    for k in keys[:-1]:
        if k.isdigit():
            k = int(k)
            while len(cur) <= k:
                cur.append({})
            cur = cur[k]
        else:
            if k not in cur:
                cur[k] = {}
            cur = cur[k]

    last = keys[-1]
    if last.isdigit():
        last = int(last)
        while len(cur) <= last:
            cur.append(None)
        cur[last] = value
    else:
        cur[last] = value


def del_by_path(dct, path):
    """
    Удаляет значение по пути вида 'a.b.0.c' в словаре/списке.
    """
    keys = path.split('.')
    cur = dct
    for k in keys[:-1]:
        if k.isdigit():
            k = int(k)
            cur = cur[k]
        else:
            cur = cur[k]

    last = keys[-1]
    if last.isdigit():
        last = int(last)
        del cur[last]
    else:
        del cur[last]


def main():
    # 1. Загрузка главного словаря
    main_lang_path = f"{ex}{langs_path}/{main_code}.json"
    main_data = read_json(main_lang_path).get(main_code, {})

    # 2. Получение всех языков для перевода
    langs_dir = ex + langs_path
    lang_files = [f for f in os.listdir(langs_dir) if f.endswith('.json')]
    lang_codes = [f.replace('.json', '') for f in lang_files if f.replace('.json', '') != main_code]
    print(f"Языки для перевода: {lang_codes}")

    for lang in lang_codes:
        print(f"\n=== Перевод для {lang} ===")
        lang_path = f"{ex}{langs_path}/{lang}.json"
        damp_path_ = f"{ex}{damp_path}/{lang}.json"

        lang_data = read_json(lang_path).get(lang, {})
        damp_data = read_json(damp_path_)

        # 3. Создать структуру дампа
        main_struct = build_structure(main_data)
        if not damp_data:
            damp_data = {lang: main_struct}
            write_json(damp_path_, damp_data)

        # 4. Сравнить структуры
        new_keys, changed_keys, deleted_keys = compare_structures(main_data, damp_data[lang])

        print(f'Новые ключи: {new_keys}')
        print(f'Изменённые ключи: {changed_keys}')
        print(f'Удалённые ключи: {deleted_keys}')

        # 5. Удалить лишние ключи
        for key in deleted_keys:
            del_by_path(lang_data, key)
            del_by_path(damp_data[lang], key)

        if new_keys or changed_keys:
            print(f'\nНачало перевода...')

            # 6. Перевести новые/изменённые ключи
            def update_callback(path, value):
                # Проверяем, начинается ли path с любого из new_keys или changed_keys
                def is_prefix_in_keys(keys, path):
                    for key in keys:
                        if path == key or path.startswith(f"{key}."):
                            return True
                    return False

                if is_prefix_in_keys(new_keys, path) or is_prefix_in_keys(changed_keys, path):
                    if isinstance(value, str):
                        path_set = set(path.split('.'))
                        ignore_set = set(ignore_translate_keys)

                        if path_set & ignore_set:
                            translated = value  # Не переводим, если есть совпадение
                            print(f"Пропускаем перевод для {path}: {value}")
                        else:
                            translated = translate_text(value, lang)

                        set_by_path(lang_data, path, translated)
                        set_by_path(damp_data, path, value)
                    else:
                        set_by_path(lang_data, path, value)
                        set_by_path(damp_data, path, value)
            walk_keys(main_data, update_callback)

        # 7. Сохранить результат
        write_json(lang_path, {lang: lang_data})
        write_json(damp_path_, {lang: main_data})

if __name__ == '__main__':
    main()