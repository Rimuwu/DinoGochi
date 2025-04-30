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
    start_symbols = settings['start_symbols']

    zero_translator = settings['zero_translator']
    ignore_translate_keys = settings['ignore_translate_keys']
    strat_sym, end_sym = settings['sp_sym']

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

def save_replace(code: int, text: str, translate: bool, data = '' ):
    global cash_replaces
    """
    Сохраняет замену в словаре cash_replaces.
    """
    new_code = f'{code}'
    if new_code not in cash_replaces and new_code not in cash_replaces.keys():
        cash_replaces[new_code] = {"text": text, 
                               "translate": translate, "data": data}
        return new_code
    else:
        return save_replace(random.randint(1, 10000), text, translate, data)

def replace_specials(text):
    # "(121)": {"text": "_", "translate": false},
    """
    Заменяет спецсимволы и эмодзи на коды для защиты от перевода.
    """
    if not isinstance(text, str):
        return text

    for _ in range(6):
        # Заменяем спецсимволы
        for key, item in replace_words.items():
            code = save_replace(int(key), item['text'], item['translate'])
            text = text.replace(
                item['text'], f"{strat_sym}{code}{end_sym}")

        # Прячем эмодзи
        for em in emoji.emoji_list(text):
            code = save_replace(int(ord(em['emoji'][0])), 
                                em['emoji'], False)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(em['emoji'], text_code)

        # Прячем переменные вида {name}
        matches = re.findall(r'\{.*?\}', text)
        for match in matches:
            code = save_replace(int(ord(match[1])), 
                                match, False)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)

        # Прячем переменные вида /слово (только первое целое слово после /)
        matches = re.findall(r'/\w+', text)
        for match in matches:
            code = save_replace(int(ord(match[1])),
                    match, False)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)
        
        matches = re.findall(r'<\s*[^<>]+\s*>', text)
        for match in matches:
            code = save_replace(int(ord(match[1])),
                    match, True)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)
        
        # Прячем переменные вида <b>word</b>
        matches = re.findall(r'<\s*[^<>]+\s*>', text)
        for match in matches:
            code = save_replace(int(ord(match[1])),
                    match, True)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)

        # Прячем переменные вида *Слово*
        for one_repl in one_replace_s:
            tx = fr'\{one_repl}\s*.*?\s*\{one_repl}'
            matches = re.findall(tx, text)
            for match in matches:
                code = save_replace(int(ord(match[1])),
                                    match[1:-1], True, one_repl)
                text_code = f"{strat_sym}{code}{end_sym}"
                text = text.replace(match, text_code)

    return text

def smart_contains(text, word):
    """
    Проверяет, содержится ли подстрока word в тексте text.
    """
    if not isinstance(text, str) or not isinstance(word, str) or not word:
        return False
    return word in text

def restore_specials(text, to_lang, from_lang):
    """
    Восстанавливает спецсимволы и эмодзи после перевода.
    """
    if not isinstance(text, str): return text

    for _ in range(6):
        # for key, item in replace_words.items():
        #     word_text = item['text']

        #     if smart_contains(text, key):
        #         if item['translate']:
        #             stage_text = translate_text(word_text, to_lang, from_lang)
        #             if not isinstance(stage_text, str):
        #                 stage_text = str(stage_text)
        #             text = text.replace(key, stage_text)
        #         else:
        #             text = text.replace(key, word_text)

        for code, item in cash_replaces.copy().items():
            word_text = item['text']
            for code_in_text in [
                f'{strat_sym}{code}{end_sym}',
                f'{strat_sym} {code}{end_sym}',
                f'{strat_sym}{code} {end_sym}',
                f'{strat_sym} {code} {end_sym}',
                # f'{code}{end_sym}',
                # f'{strat_sym}{code}',
                # f'{code} {end_sym}',
                # f'{strat_sym} {code}',
            ]:
            
                if smart_contains(text, code_in_text):
                    if item['translate']:
                        stage_text = translate_text(word_text, to_lang, from_lang)
                        if not isinstance(stage_text, str):
                            stage_text = str(stage_text)
                        if item['data']:
                            # Оборачиваем только восстановленный текст, а не весь text
                            stage_text = f"{item['data']}{stage_text}{item['data']}"
                        text = text.replace(code_in_text, stage_text)
                    else:
                        text = text.replace(code_in_text, word_text)

                    text = text.replace(code_in_text, word_text)

    # Восстановление эмодзи (пример: #128512# -> 😀)
    return text

# Проверяем стиль регистра исходного текста
def match_case(original, translated):
    if original.isupper():
        return translated.upper()
    elif original.istitle():
        return translated.title()
    elif original.islower():
        return translated.lower()
    else:
        return translated

def translate_text(text, to_lang, from_lang, trans=zero_translator):
    global cash_replaces
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

    if lang is None: lang = from_lang

    if lang in ['en', 'it'] and len(langs) == 1:
        translated = safe_text
        print(f"Не переводим: {text} - {lang}")
    
    elif safe_text[1:-1] in cash_replaces.keys():
        cash_replaces[safe_text[1:-1]]['translated'] = False
        translated = safe_text
        print(f"Не переводим (замена): {text} - {lang}")

    elif lang or len(langs) == 0:
        try:
            translated = translators.translate_text(safe_text, from_language=from_lang, to_language=to_lang, translator=trans)
            dict_data = {
                "text": safe_text,
                "lang": lang,
                "to_lang": to_lang,
                "translated": translated
            }
            pprint(dict_data)
        except Exception as e:
            print(f"Ошибка перевода: {text} - {str(e)}")
            translated = safe_text

        translated = match_case(text, translated)

    else:
        translated = safe_text
        print(f"Не переведено {len(langs)} {lang} -> {text}")
    return restore_specials(translated, to_lang, from_lang)


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
    Корректно работает с вложенными списками и словарями.
    Если на последнем уровне ожидается список, но найден dict — индекс становится ключом.
    """
    keys = path.split('.')
    cur = dct

    for idx, k in enumerate(keys[:-1]):
        next_k = keys[idx + 1]
        if k.isdigit():
            k = int(k)
            # Если текущий уровень - не список, преобразуем
            if not isinstance(cur, list):
                # Если cur пустой, превращаем в список
                if isinstance(cur, dict) and not cur:
                    cur = []
                    # Нужно обновить ссылку в родителе
                    parent = dct
                    for pk in keys[:idx]:
                        parent = parent[int(pk)] if pk.isdigit() else parent[pk]
                    if keys[idx-1].isdigit():
                        parent[int(keys[idx-1])] = cur
                    else:
                        parent[keys[idx-1]] = cur
                else:
                    # Если не пустой dict, то ошибка структуры
                    raise TypeError(f"Ожидался список на уровне {k}, но найден dict с данными: {cur}")
            while len(cur) <= k:
                cur.append({})
            cur = cur[k]
        else:
            if not isinstance(cur, dict):
                # Если cur список, но нужен dict
                raise TypeError(f"Ожидался dict на уровне {k}, но найден список: {cur}")
            if k not in cur:
                # Если следующий ключ - число, создаём список, иначе dict
                cur[k] = [] if next_k.isdigit() else {}
            cur = cur[k]

    last = keys[-1]
    if last.isdigit():
        last = int(last)
        if isinstance(cur, list):
            while len(cur) <= last:
                cur.append(None)
            cur[last] = value
        elif isinstance(cur, dict):
            # Если на последнем уровне dict, индекс становится ключом-строкой
            cur[str(last)] = value
        else:
            raise TypeError(f"Ожидался список или dict на последнем уровне, но найден: {type(cur)}")
    else:
        if not isinstance(cur, dict):
            raise TypeError(f"Ожидался dict на последнем уровне, но найден список: {cur}")
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

# Проверяем, начинается ли path с любого из new_keys или changed_keys
def is_prefix_in_keys(keys, path):
    for key in keys:
        if path.endswith(f"{key}") or path == key:
            return True
    return False

def main():
    global cash_replaces

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
        # Если дамп пустой, создаём структуру только для новых/изменённых ключей
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
                global cash_replaces

                if is_prefix_in_keys(new_keys, path) or is_prefix_in_keys(changed_keys, path):
                    if isinstance(value, str):
                        path_set = set(path.split('.'))
                        ignore_set = set(ignore_translate_keys)

                        if path_set & ignore_set:
                            translated = value  # Не переводим, если есть совпадение
                            print(f"Пропускаем перевод для {path}: {value}")
                        elif len(value) < 2:
                            translated = value
                            print(f"Пропускаем перевод для {path} (малая длинна): {value}")
                        else:
                            translated = translate_text(value, lang, main_code)
                            print(f"Переводим {path}: {value} -> {translated}")
                        
                        # Сброс тегов
                        cash_replaces = {}

                        set_by_path(lang_data, path, translated)
                        set_by_path(damp_data, f'{lang}.'+path, value)
                    else:
                        set_by_path(lang_data, path, value)
                        set_by_path(damp_data, f'{lang}.'+path, value)
    
                    write_json(lang_path, {lang: lang_data})
                    write_json(damp_path_, damp_data)

            walk_keys(main_data, update_callback)

        # # 7. Сохранить результат
        # write_json(lang_path, {lang: lang_data})
        # write_json(damp_path_, {lang: damp_data})

if __name__ == '__main__':
    main()