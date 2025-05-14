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
# langs_path = "/langs"
# dump_path = "/dump_test"

# base_names = {}
cash_replaces = {}


with open(os.path.join(ex, 'settings.json'), encoding='utf-8') as f: 
    """ Загружаем константы из файла найстроек """
    settings = json.load(f) # type: dict
    settings = settings['new']

    replace_codes = settings['replace_codes']
    replace_words = settings['replace_words']
    one_replace_s = settings['one_replace_s']
    translators_names = settings['translators']

    main_code = settings['main_code']
    langs_path = settings['langs_path']
    dump_path = settings['dump_path']
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


def compare_structures(base, dump, path=""):
    """
    Сравнивает структуру base (исходный словарь) и dump (дамп перевода).
    Возвращает:
      - новые ключи (есть в base, нет в dump)
      - изменённые (значения отличаются)
      - удалённые (есть в dump, нет в base)
    """
    new_keys, changed_keys, deleted_keys = [], [], []
    if isinstance(base, dict):
        base_keys = set(base.keys())
        dump_keys = set(dump.keys()) if isinstance(dump, dict) else set()

        for k in base_keys:
            new_path = f"{path}.{k}" if path else k
            if k not in dump_keys:
                new_keys.append(new_path)
            else:
                n, c, d = compare_structures(base[k], dump[k], new_path)
                new_keys += n
                changed_keys += c
                deleted_keys += d

        for k in dump_keys - base_keys:
            new_path = f"{path}.{k}" if path else k
            deleted_keys.append(new_path)

    elif isinstance(base, list) and isinstance(dump, list):
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)

            if idx >= len(dump):
                new_keys.append(new_path)
            else:
                n, c, d = compare_structures(v, dump[idx], new_path)
                new_keys += n
                changed_keys += c
                deleted_keys += d

        for idx in range(len(base), len(dump)):
            new_path = f"{path}.{idx}" if path else str(idx)
            deleted_keys.append(new_path)
    else:
        if base != dump:
            changed_keys.append(path)
    return new_keys, changed_keys, deleted_keys

def save_replace(code: int, text: str, translate: bool, data = '' ):
    global cash_replaces
    """
    Сохраняет замену в словаре cash_replaces.
    """
    new_code = f'{code}'
    r_code = f'{strat_sym}{code}{end_sym}'

    s_1 = new_code not in cash_replaces
    s_2 = r_code not in cash_replaces
    s_3 = new_code not in replace_words
    s_4 = r_code not in replace_words

    # for k, v in cash_replaces.items():
    #     if v["text"] == text and v["translate"] == translate and v.get("data", "") == data:
    #         return k

    if all([s_1, s_3, s_2, s_4]):
        # if new_code.startswith(strat_sym) and new_code.endswith(end_sym):
        #     pass
        # else:
        #     new_code = r_code
        # new_code = f'{new_code}0{new_code}0'
        cash_replaces[new_code] = {"text": text, 
                               "translate": translate, "data": data}
        return new_code
    else:
        r = 0
        if type(code) == int:
            r = code + 1
        elif code.isdigit(): # type: ignore
            r += int(code) + 1
        else:
            r = int(code[1:-1]) + 1 # type: ignore
        # r = random.randint(1, 1000)
        return save_replace(r, text, translate, data)

def replace_specials(text):
    # "(121)": {"text": "_", "translate": false},
    """
    Заменяет спецсимволы и эмодзи на коды для защиты от перевода.
    """
    if not isinstance(text, str):
        return text

    for _ in range(3):
        # Заменяем спецсимволы
        for key, item in replace_words.items():
            if item['text'] in text:
                code = save_replace(800, item['text'], item['translate'])
                text = text.replace(
                    item['text'], f"{strat_sym}{code}{end_sym}")

        # Прячем эмодзи
        for em in emoji.emoji_list(text):
            code = save_replace(100, 
                                em['emoji'], False)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(em['emoji'], text_code)

        # Прячем переменные вида {name}
        matches = re.findall(r'\{.*?\}', text)
        for match in matches:
            code = save_replace(200, 
                                match, False)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)

        # Прячем переменные вида /слово (только первое целое слово после /)
        matches = re.findall(r'/\w+', text)
        for match in matches:
            code = save_replace(300,
                    match, False)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)
        
        matches = re.findall(r'<\s*[^<>]+\s*>', text)
        for match in matches:
            code = save_replace(400,
                    match, True)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)
        
        # Прячем переменные вида <b>word</b>
        matches = re.findall(r'<\s*[^<>]+\s*>', text)
        for match in matches:
            code = save_replace(500,
                    match, True)
            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)

        # Прячем переменные вида *Слово*
        for one_repl in one_replace_s:
            tx = fr'\{one_repl}\s*.*?\s*\{one_repl}'
            matches = re.findall(tx, text)
            for match in matches:
                code = save_replace(600,
                                    match[1:-1], True, one_repl)
                text_code = f"{strat_sym}{code}{end_sym}"
                text = text.replace(match, text_code)

    # # Прячем конструкции вида #число##число#... (любое количество подряд)
    # # Новый паттерн: ищет одну или более групп #число#, подряд идущих

    # matches = re.findall(r'(#[0-9]+#)+', text)
    # for match in matches:
    #     if strat_sym in match or end_sym in match:
    #         continue
    #     if len(match) >= 6:
    #         code = save_replace(700, match, False)
    #         text_code = f"{strat_sym}{code}{end_sym}"
    #         text = text.replace(match, text_code)
    #         print(f"Заменено: {match} -> {text_code}")

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

        #     fr_key = key[1:-1]
        #     for code_in_text in [
        #         f'{strat_sym}{fr_key}{end_sym}',
        #         f'{strat_sym} {fr_key}{end_sym}',
        #         f'{strat_sym}{fr_key} {end_sym}',
        #         f'{strat_sym} {fr_key} {end_sym}',
        #         # f'{fr_key}{end_sym}',
        #         # f'{strat_sym}{fr_key}',
        #         # f'{fr_key} {end_sym}',
        #         # f'{strat_sym} {fr_key}',
        #         # f'{fr_key}{end_sym}',
        #         # f' {strat_sym}{fr_key}'
        #     ]:

        #         if smart_contains(text, code_in_text):
        #             text = text.replace(code_in_text, word_text)

        for code, item in cash_replaces.copy().items():
            word_text = item['text']
            # repl = False

            for code_in_text in [
                f'{strat_sym}{code}{end_sym}',
                f'{strat_sym} {code}{end_sym}',
                f'{strat_sym}{code} {end_sym}',
                f'{strat_sym} {code} {end_sym}',
                f'{strat_sym}{strat_sym}{code}{end_sym}',
                f'{strat_sym}{code}{end_sym}{end_sym}',
                f'{strat_sym}{strat_sym} {code}{end_sym}',
                f'{strat_sym}{code} {end_sym}{end_sym}',
                f'{strat_sym} {code}{end_sym}{end_sym}',
                f'{code}{end_sym}',
                f'{strat_sym}{code}',
                f'{code} {end_sym}',
                f'{strat_sym} {code}',
                f'{code}{end_sym}',
                f' {strat_sym}{code}',
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

                    # text = text.replace(code_in_text, word_text)
                    # continue
                else:
                    text = text.replace(code_in_text, word_text)

    # Восстановление эмодзи (пример: #128512# -> 😀)
    return text


def match_case(original, translated, lang):
    orig_words = original.split()
    trans_words = translated.split()
    # Если количество слов совпадает, применяем стиль регистра для каждого слова
    if len(orig_words) == len(trans_words):
        result = []
        for i, word in enumerate(trans_words):
            if orig_words[i].isupper():
                result.append(word.capitalize())
            elif orig_words[i].islower():
                result.append(word.lower())
            elif orig_words[i].istitle():
                result.append(word.title())
            else:
                result.append(word)
        return ' '.join(result)

    # Новое: если весь оригинал в нижнем регистре — вернуть перевод в нижнем регистре
    if original.islower():
        return translated.lower()
    # Новое: если только первое слово с большой буквы, остальные маленькие
    if (
        original
        and original[0].isupper()
        and (len(original) == 1 or original[1:].islower())
    ):
        # Если перевод состоит из нескольких слов, делаем capitalize только первое слово
        if translated:
            return translated[0].capitalize() + translated[1:].lower()
        return translated

    # Если не совпадает — применяем общий стиль
    if original.isupper():
        return translated.capitalize()
    if original.istitle():
        return translated.title()
    return translated

def repl_code(trans, lang):
    code = replace_codes.get(trans.lower(), {}).get(lang, lang)
    return code

def translate_text(text, to_lang, from_lang, trans=zero_translator):
    global cash_replaces
    """
    Переводит текст, защищая спецсимволы и эмодзи.
    """
    
    if to_lang is None and from_lang is None:
        return text
    
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
        return restore_specials(translated, None, None)

    elif safe_text in replace_words.keys():
        cash_replaces[safe_text]['translated'] = False
        translated = safe_text
        print(f"Не переводим (замена): {text} - {lang}")
        return restore_specials(translated, None, None)

    elif lang or len(langs) == 0:
        try:
            # translators.translators_pool = translators_names
            translated = translators.translate_text(safe_text,
                                    from_language=repl_code(trans, from_lang), to_language=repl_code(trans, to_lang),
                                    translator=trans, 
                                    headers={'User-Agent': random.choice(user_agents)})
            translated = match_case(text, translated, to_lang)
            new_lang = detect(translated)
            if new_lang == 'ru':
                translated = translate_text(
                    translated, to_lang, from_lang,
                    trans=trans
                )

            dict_data = {
                "text": safe_text,
                "lang": lang,
                "to_lang": to_lang,
                "translated": translated,
                "trans": trans
            }

            pprint(dict_data)
        except Exception as e:
            print(f"Ошибка перевода: {text} - {str(e)}")
            translated = safe_text

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


def set_by_path(dct, path, value, dump=None):
    """
    Устанавливает значение по пути вида 'a.b.0.c' в словаре/списке.
    Если передан dump, сверяет ожидаемый тип на каждом уровне с dump.
    Если на последнем уровне ожидается список, но найден dict — индекс становится ключом.
    """
    keys = path.split('.')
    cur = dct
    dump_cur = dump
    for idx, k in enumerate(keys[:-1]):
        next_k = keys[idx + 1]
        # Определяем ожидаемый тип на этом уровне
        expected_type = None
        if dump_cur is not None:
            try:
                if isinstance(dump_cur, dict):
                    dump_next = dump_cur.get(k)
                elif isinstance(dump_cur, list) and k.isdigit():
                    dump_next = dump_cur[int(k)] if int(k) < len(dump_cur) else None
                else:
                    dump_next = None
                if isinstance(dump_next, list):
                    expected_type = list
                elif isinstance(dump_next, dict):
                    expected_type = dict
                else:
                    expected_type = None
            except Exception:
                expected_type = None
        # Если текущий уровень — список, используем int-индекс
        if isinstance(cur, list):
            if not k.isdigit():
                raise TypeError(f"Ожидался числовой индекс для списка, но получен ключ '{k}'")
            k_int = int(k)
            while len(cur) <= k_int:
                # Если dump подсказывает тип, используем его, иначе по next_k
                if expected_type is not None:
                    cur.append([] if expected_type is list else {})
                else:
                    cur.append([] if next_k.isdigit() else {})
            cur = cur[k_int]
            if dump_cur is not None and isinstance(dump_cur, list) and k_int < len(dump_cur):
                dump_cur = dump_cur[k_int]
            else:
                dump_cur = None
        elif isinstance(cur, dict):
            # Если dump подсказывает тип, используем его, иначе по next_k
            if k not in cur:
                if expected_type is not None:
                    cur[k] = [] if expected_type is list else {}
                else:
                    cur[k] = [] if next_k.isdigit() else {}
            cur = cur[k]
            if dump_cur is not None and isinstance(dump_cur, dict):
                dump_cur = dump_cur.get(k)
            else:
                dump_cur = None
        else:
            raise TypeError(f"Неожиданный тип: {type(cur)} для ключа {k}")
    last = keys[-1]
    # На последнем уровне сверяем с dump, если возможно
    if dump_cur is not None:
        if isinstance(cur, list) and last.isdigit() and isinstance(dump_cur, list):
            last = int(last)
            while len(cur) <= last:
                cur.append(None)
            cur[last] = value
        elif isinstance(cur, dict) and isinstance(dump_cur, dict):
            cur[last] = value
        else:
            # Если типы не совпадают, всё равно пытаемся записать
            if isinstance(cur, list) and last.isdigit():
                last = int(last)
                while len(cur) <= last:
                    cur.append(None)
                cur[last] = value
            elif isinstance(cur, dict):
                cur[last] = value
            else:
                raise TypeError(f"Неожиданный тип на последнем уровне: {type(cur)} для ключа {last}")
    else:
        if isinstance(cur, list) and last.isdigit():
            last = int(last)
            while len(cur) <= last:
                cur.append(None)
            cur[last] = value
        elif isinstance(cur, dict):
            cur[last] = value
        else:
            raise TypeError(f"Неожиданный тип на последнем уровне: {type(cur)} для ключа {last}")


def del_by_path(dct, path):
    """
    Удаляет значение по пути вида 'a.b.0.c' в словаре/списке.
    """
    keys = path.split('.')
    cur = dct
    for k in keys[:-1]:
        if isinstance(cur, list) and k.isdigit():
            cur = cur[int(k)]
        elif isinstance(cur, dict):
            cur = cur[k]
        else:
            raise TypeError(f"Неожиданный тип: {type(cur)} для ключа {k}")

    last = keys[-1]
    if isinstance(cur, list) and last.isdigit():
        last = int(last)
        del cur[last]
    elif isinstance(cur, dict):
        if last not in cur:
            raise KeyError(f"Ключ {last} не найден в словаре")
        del cur[last]
    else:
        raise TypeError(f"Неожиданный тип на последнем уровне: {type(cur)} для ключа {last}")

# Проверяем, начинается ли path с любого из new_keys или changed_keys
def is_prefix_in_keys(keys, path):
    """
    Проверяет, начинается ли path с любого из путей в keys.
    Например: keys = ['a.b', 'c'], path = 'a.b.1.d' -> True
    """
    for key in keys:
        if path == key or path.startswith(f"{key}."):
            return True
    return False
    

a_c_upd = 0

def main():
    global cash_replaces, a_c_upd

    # 1. Загрузка главного словаря
    main_lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{main_code}.json"))
    main_data = read_json(main_lang_path).get(main_code, {})

    # 2. Получение всех языков для перевода
    langs_dir = os.path.normpath(os.path.join(ex, langs_path))
    lang_files = [f for f in os.listdir(langs_dir) if f.endswith('.json')]
    lang_codes = [f.replace('.json', '') for f in lang_files if f.replace('.json', '') != main_code]
    print(translators.translators_pool)
    print(f"Языки для перевода: {lang_codes}")

    for lang in lang_codes:
        a_c_upd = 0
        print(f"\n=== Перевод для {lang} ===")
        # Определяем главный язык для перевода
        if lang == "en":
            main_lang = "ru"
        else:
            main_lang = "en"
        lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
        dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

        # Загружаем главный словарь для текущего языка
        main_lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{main_lang}.json"))
        main_data = read_json(main_lang_path).get(main_lang, {})

        lang_data = read_json(lang_path).get(lang, {})
        dump_data = read_json(dump_path_)

        # 3. Создать структуру дампа
        main_struct = build_structure(main_data)
        # Если дамп пустой, создаём структуру только для новых/изменённых ключей
        if not dump_data:
            dump_data = {lang: main_struct}
            write_json(dump_path_, dump_data)
        
        # if not lang_data:
        #     lang_data = {lang: main_struct}
        #     write_json(lang_path, lang_data)

        # 4. Сравнить структуры
        new_keys, changed_keys, deleted_keys = compare_structures(main_data, dump_data[lang])

        print(f'Новые ключи: {new_keys}')
        print(f'Изменённые ключи: {changed_keys}')
        print(f'Удалённые ключи: {deleted_keys}')

        # 5. Удалить лишние ключи
        for key in deleted_keys:
            try:
                del_by_path(lang_data, key)
            except Exception as e:
                print(f"Ошибка удаления {key} из lang_data: {e}")
            try:
                del_by_path(dump_data[lang], key)
            except Exception as e:
                print(f"Ошибка удаления {key} из dump_data: {e}")

            write_json(dump_path_, dump_data)
            write_json(lang_path, {lang: lang_data})

        if new_keys or changed_keys:
            print(f'\nНачало перевода...')

            # 6. Перевести новые/изменённые ключи
            def update_callback(path, value):
                global cash_replaces, a_c_upd

                # Проверяем, начинается ли path с любого из new_keys или changed_keys
                if is_prefix_in_keys(new_keys + changed_keys, path):
                    if isinstance(value, str):
                        path_set = set(path.split('.'))
                        ignore_set = set(ignore_translate_keys)

                        if path_set & ignore_set:
                            if path.endswith('text'):
                                translated = translate_text(value, lang, main_lang)
                                if translated == value:
                                    translated = translate_text(value, lang, main_lang)
                                print(f"Переводим {path}: {value} -> {translated}")
                            else:
                                translated = value  # Не переводим, если есть совпадение
                                print(f"Пропускаем перевод для {path}: {value}")
                        elif len(value) < 2:
                            translated = value
                            print(f"Пропускаем перевод для {path} (малая длинна): {value}")
                        else:
                            translated = translate_text(value, lang, main_lang)
                            if translated == value:
                                translated = translate_text(value, lang, main_lang)
                            print(f"Переводим {path}: {value} -> {translated}")

                        # Сброс тегов
                        cash_replaces = {}

                        set_by_path(lang_data, path, translated, dump_data[lang])
                        set_by_path(dump_data, f'{lang}.'+path, value)
                    else:
                        set_by_path(lang_data, path, value, dump_data[lang])
                        set_by_path(dump_data, f'{lang}.'+path, value)

                    a_c_upd += 1
                    if a_c_upd % 3 == 0:
                        write_json(lang_path, {lang: lang_data})
                        write_json(dump_path_, dump_data)

            walk_keys(main_data, update_callback)

            write_json(lang_path, {lang: lang_data})
            write_json(dump_path_, dump_data)

if __name__ == '__main__':
    main()