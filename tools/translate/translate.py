import json
import time
import random
import os
import emoji
from pprint import pprint
import requests

import translators
from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0
ex = os.path.dirname(__file__) # Путь к этому файлу
#"langs_path": "../../bot/localization",

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
    langs_path = settings['langs_path']
    damp_path = settings['damp_path']

    zero_translator = settings['zero_translator']
    ignore_translate_keys = settings['ignore_translate_keys']

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

def undoreplace(text: str, to_lang: str):
    """ Функция из закодированного для переводчика текста, превращает его в читаемый
    """
    replaces = dict(list(cash_replaces.items()) + list(replace_words.items())) # Объединяем словари для проверки кодов

    for _ in range(6): # 6 раз - потому что в коде уже может быть ссылка на другой код
        for key, data in replaces.items(): # Перебираем все ключи с сохранённым текстом
            txt = None

            if key in text: # Исправлено условие проверки наличия ключа в тексте
                if data['translate']:
                    if len(data['text']) > 3 and data['text'][1] == '#' and data['text'][-2] == '#': 
                        # Если текста состоит из ключа, то его нет смысла переводить
                        txt = data['text']
                    else:
                        txt = translator(data['text'], to_lang)
                else:
                    txt = data['text']

                if 'sml' in data:
                    # Если мы должны вставить символ форматирования
                    txt = data['sml'] + txt + data['sml']

                if not txt: txt = key
                text = text.replace(key, txt)

                lst_key = list(key)
                lst_key.insert(1, ' ')
                new_key = ''.join(lst_key)
                text = text.replace(new_key, txt)

                lst_key = list(key)
                lst_key.insert(-1, ' ')
                new_key = ''.join(lst_key)
                text = text.replace(new_key, txt)

                lst_key = list(key)
                lst_key.insert(-1, ' ')
                lst_key.insert(1, ' ')
                new_key = ''.join(lst_key)
                text = text.replace(new_key, txt)
    return text

def replace_simbols(text: str):
    """ Функция заменяет специальные символы на коды, для корректности работы словаря
    """
    if not text:  # Проверка на пустой текст
        return text

    # Заменяем все заранее известные символы
    for key, item in replace_words.items(): text = text.replace(item['text'], key)
    word, st = '', False

    for i1 in emoji.emoji_list(text): # Получеам эмоджи из текста
        # Прячем за кодом эмоджи
        k_name = f'#{len(cash_replaces)}{len(cash_replaces)}#'
        cash_replaces[k_name] = {
            'text': i1['emoji'],
            'translate': False
        }
        text = text.replace(i1['emoji'], k_name)
        word = ''

    word, st = '', False

    for i2 in text:
        # Убираем все конструкции вставки переменных (прячем за кодом)
        # {name} -> (1111)
        k_name = ''
        if i2 == '{':
            st = True
            word += i2

        elif i2 == '}':
            st = False
            word += i2
            word = word[1:]

            # Это означает, что название вставки перемнной закончена, можем сохранять
            add = True
            for repl_key, repl_value in cash_replaces.items():
                if repl_value['text'] == word:
                    add = False
                    k_name = repl_key
            if add:
                k_name = f'#{len(cash_replaces)}{len(cash_replaces)}#'
                cash_replaces[k_name] = {
                    'text': word,
                    'translate': False
                }
            text = text.replace(word, k_name)
            word = ''

        if st: word += i2

    for i3 in text:
        k_name = '1'
        # Замена конструкций форматирования *такие например* -> (1212)
        # if i3 == '/' and st: st = False
        if i3 in one_replace_s and st: 
            st = False
            translate_st = True
            word += i3
            end_word = word[1:-1]

            if len(end_word) == 1: translate_st = False
            if end_word in cash_replaces.keys(): translate_st = False

            add = True
            for repl_key, repl_value in cash_replaces.items():
                if repl_value['text'] == end_word and repl_value['sml'] == i3:
                    add = False
                    k_name = repl_key
                    break
            if add:
                k_name = f'#{len(cash_replaces)}{len(cash_replaces)}#'
                cash_replaces[k_name] = {
                    'text': end_word,
                    'translate': translate_st,
                    'sml': i3
                }
            text = text.replace(word, k_name)
            word = ''

        elif i3 in one_replace_s and not st: st = True
        if st: word += i3
    return text

def translator(text: str, to_lang:str, trans='bing') -> str:
    """ Единственная функция в этом коде перевода, которая переводит!
    """
    global base_names

    if not text:  # Проверка на пустой текст
        return text

    # Замены ключей
    from_language = main_code
    if trans in replace_codes:
        if from_language in replace_codes[trans]:
            from_language = replace_codes[trans][from_language]

        if to_lang in replace_codes[trans]:
            to_lang = replace_codes[trans][to_lang]

    try: 
        lang = detect(text) # Определяем язык текста
    except: 
        lang = 'emoji'

    if lang not in ['en', 'it', 'emoji']:
        # Если текст есть в базе, его не надо переводить снова
        if text in base_names: 
            return base_names[text]
        else:
            try:
                # --- Случайный user-agent и proxy ---
                headers = {'User-Agent': random.choice(user_agents)}
                proxy = None
                if proxies:
                    proxy_url = random.choice(proxies)
                    proxy = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                # --- Передаём headers и proxies если поддерживается ---
                kwargs = {
                    'from_language': from_language,
                    'to_language': to_lang,
                    'translator': trans
                }
                # translators.translate_text поддерживает proxies и headers только для некоторых сервисов
                if proxy:
                    kwargs['proxies'] = proxy
                if headers:
                    kwargs['headers'] = headers
                ret = translators.translate_text(text, **kwargs)

                pprint({
                    "Text in": text, 'translator': trans, 
                    'Text out': ret, 'from_language': from_language,
                    'to_lang': to_lang, 'detect': lang,
                    'proxy': proxy, 'headers': headers
                })
                
                if ret:  # Проверка на пустой результат перевода
                    base_names[text] = ret
                    return ret
                return text
                
            except Exception as e: 
                print(e)
                print(trans)
                return translator(text, to_lang, translators_names[ 
                                translators_names.index(trans) - 1])
    return text

def text_translate(text: str, to_lang: str, 
                   trans:str = zero_translator, repl:bool = True):
    """ Перевод """
    if not text: return text
    if repl: text = replace_simbols(text)
    new_text = ''

    try:
        new_text = translator(text, to_lang, trans)
    except Exception as e:
        print(f"Translation error: {e}")
        pass

    if not new_text:
        # Если переводчик возвращает пустоту, значит он вызывает ошибку, значит он скорее всего перегрелся от запросов, рандомим другой переводчик
        rand_trans = random.choice(translators_names)
        new_text = text_translate(text, to_lang, rand_trans, False)

    return new_text

def remove_non_dict_or_list(dct):
    """ Функция заменяет вcе значения ключей на NOTEXT, тем самым копируя структуру словаря
    """
    if not dct:  # Проверка на пустой словарь
        return dct
        
    keys_to_remove = []
    for key, value in dct.items():
        if not isinstance(value, (dict, list)):
            keys_to_remove.append(key)
        elif isinstance(value, dict):
            remove_non_dict_or_list(value)  # Рекурсивный вызов для проверки вложенных словарей
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    remove_non_dict_or_list(item)  # Рекурсивный вызов для проверки вложенных словарей в списке
                else:
                    value[value.index(item)] = 'NOTEXT'

    for key in keys_to_remove: dct[key] = 'NOTEXT'
    return dct

def replace_data(dct: dict, way: str, new) -> dict:
    """ Заменяет данные в ключе словаря, идя по пути ключей way
    """
    if not dct or not way:  # Проверка на пустые входные данные
        return dct
        
    lst = way.split('.')
    new_dct = dct.copy()
    current_dict = new_dct

    for key in lst[:-1]:
        if isinstance(current_dict, list):
            if key.isdigit():
                key = int(key)
            current_dict = current_dict[key] # type: ignore
        else:
            current_dict = current_dict.get(key, {})

    if isinstance(current_dict, list) and lst[-1].isdigit():
        lst[-1] = int(lst[-1])  # type: ignore

    if new is None:
        if isinstance(current_dict, list):
            current_dict.pop(lst[-1]) # type: ignore
        elif isinstance(current_dict, dict):
            del current_dict[lst[-1]] # type: ignore
    else:
        if isinstance(current_dict, list):
            if lst[-1] + 1 >= len(current_dict): # type: ignore
                current_dict.insert(lst[-1], new) # type: ignore
            else:
                current_dict[lst[-1]] = new # type: ignore
        elif isinstance(current_dict, dict):
            current_dict[lst[-1]] = new # type: ignore
    return new_dct

def get_damp(lang_code:str):
    """Получает данные дампа"""
    if not lang_code:  # Проверка на пустой код языка
        return {}
        
    path = f'{ex}{damp_path}/{lang_code}.json'

    if not os.path.exists(path):
        with open(path, 'w') as f: f.write('{}')
        damp = {}
    else:
        with open(path, encoding='utf-8') as f:
            damp = json.load(f) # type: dict
    return damp

def get_lang(lang_code:str):
    """Получает данные файла"""
    if not lang_code:  # Проверка на пустой код языка
        return {}

    with open(f'{ex}{langs_path}/{lang_code}.json', encoding='utf-8') as f: 
        lang = json.load(f) # type: dict
    return lang

def get_translate_langs():
    """Проверяет дерикторию langs_path и получает оттуда название файлов (языки на которые надо переводить текст)"""
    if not os.path.exists(ex + langs_path):  # Проверка существования директории
        return []

    lst = os.listdir(ex + langs_path)

    res = []
    for i in lst:
        if i.endswith('.json'):
            i = i.replace('.json', '')
            res.append(i)

    if main_code in res: res.remove(main_code)
    return res

def translate(data, to_lang:str):
    """ Распределяет какие типы надо переводить, а что надо оставить в том же виде
    """
    if not to_lang:  # Проверка на пустой код языка
        return data

    if isinstance(data, (int, float)): data = data
    elif isinstance(data, str): 
        data = text_translate(data, to_lang)
        data = undoreplace(data, to_lang)

    elif isinstance(data, dict):
        out_data = data.copy()

        for key, value in data.items():
            if key not in ignore_translate_keys:
                out_data[key] = translate(value, to_lang)
            else:
                out_data[key] = value
        return out_data

    elif isinstance(data, list):
        lst = []
        for i in data: lst.append(translate(i, to_lang))
        data = lst

    else: print(f"Не переведено {data}")
    return data

def save(data, lang, dr='languages'):
    """Сохраняет файл языка"""
    if not data or not lang:  # Проверка на пустые входные данные
        return
        
    if dr == 'languages':
        path = f'{ex}{langs_path}/{lang}.json'
    else:
        path = f'{ex}{damp_path}/{lang}.json'

    with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


def dict_way(dct:dict, way:str):
    """ Получает значение следуя по пути ключей way"""
    if not dct or not way:  # Проверка на пустые входные данные
        return None
        
    dct = dct.copy()
    new_dct = dct

    for way_key in way.split('.'):
        if way_key.isdigit() and isinstance(new_dct, list):
            way_key = int(way_key)

        if way_key in new_dct or isinstance(way_key, int):
            try:
                new_dct = new_dct[way_key]  # type: ignore
            except: 
                return None
        else:
            return None

    return new_dct

def key_check(direct, way: str):
    """ Проверяет есть ли в словаре ключ следуя по пути way
    """
    if not direct or not way:  # Проверка на пустые входные данные
        return []
        
    way_main = dict_way(direct, way)
    if way_main is None: return [way]

    if isinstance(way_main, dict):
        lst = []
        for key in way_main.keys():
            res = key_check(way_main, key)
            if res: lst += res

        if lst: return lst

    elif isinstance(way_main, list):
        lst = []
        for i in way_main: # type: ignore
            ind = way_main.index(i)
            res = key_check(way_main, str(ind))
            if not res: lst += res

        if lst: return lst

    return []


def way_check(main_direct, damp_direct, way: str, non: bool = True):
    """ Проверяет есть ли отличия в сохранённом дампе языка и в главном языковом файле
        На вход получает словари и проверяет их на совпадение
        На выход передаёт список с путём ключей
    """
    if not main_direct or not damp_direct or not way:  # Проверка на пустые входные данные
        return []
        
    main_direct = main_direct.copy()
    damp_direct = damp_direct.copy()

    way_main = dict_way(main_direct, way)
    way_damp = dict_way(damp_direct, way)

    if way_damp is None and non: 
        return [way]

    if isinstance(way_main, (int, str, float, list)):
        if way_main != way_damp: return [way]

    elif isinstance(way_main, dict):
        lst = []
        for key in way_main.keys():
            res = way_check(main_direct, damp_direct, way+f'.{key}')
            if res: lst += res

        if lst: return lst
    return []


def main(pp=False):
    global base_names, cash_replaces
    to_langs = get_translate_langs() # Языки на которые надо переводить

    data = {}

    for lang_code in to_langs:
        cash_replaces = {}
        base_names = {}
        data = {
            lang_code: {
                "del": [],
                "upd": []
            }
        }

        damp = get_damp(lang_code)
        trs_lang = get_lang(lang_code)

        main_lang = get_lang(main_code)[main_code] # Данные главного языка

        """ Создаёт главный ключ языка если нет """
        if lang_code not in trs_lang:
            trs_lang = {lang_code:{}}
            save(trs_lang, lang_code)

        if lang_code not in damp:
            damp = {lang_code:{}}
            save(damp, lang_code, 'damps')


        """ Удаление удалённых ключей """
        for key in damp[lang_code].keys():
            res = key_check(main_lang, key)
            data[lang_code]['del'] += res

            for way in res:
                trs_lang[lang_code] = replace_data(
                    trs_lang[lang_code].copy(), way, None)

                damp[lang_code] = replace_data(
                    damp[lang_code].copy(), way, None)

            if res:
                save(trs_lang, lang_code)
                save(damp, lang_code, 'damps')
                damp = get_damp(lang_code)
                trs_lang = get_lang(lang_code)


        if pp: pprint.pprint(data[lang_code]['del'])

        """ Создание структуры данных """
        rm_dct = remove_non_dict_or_list(main_lang.copy())
        main_lang = get_lang(main_code)[main_code] # Данные главного языка

        rm_trs_dct = remove_non_dict_or_list(trs_lang.copy())
        trs_lang = get_lang(lang_code)

        ed = False
        for key in rm_dct.keys():
            res = key_check(rm_trs_dct[lang_code].copy(), key)

            if res: 
                ed = True
                for nn_way in res:
                    trs_lang[lang_code] = replace_data(trs_lang[lang_code].copy(), nn_way, dict_way(rm_dct.copy(), nn_way))

                    damp[lang_code] = replace_data(damp[lang_code].copy(), nn_way, dict_way(rm_dct.copy(), nn_way))
        if ed:
            save(trs_lang, lang_code)
            save(damp, lang_code, 'damps')
            main_lang = get_lang(main_code)[main_code]
            damp = get_damp(lang_code)


        """ Определение не достающих ключей"""
        nt_keys = []
        for key in main_lang.keys():
            res = way_check(main_lang.copy(), damp[lang_code].copy(), key, False)
            if res: nt_keys += res

        damp = get_damp(lang_code)

        """ Перевод ключей """
        for way in nt_keys:
            data[lang_code]['upd'].append(way)

            # if len(cash_replaces.keys()) >= 400:
            #     cash_replaces = {}

            last_key = way.split('.')[-1]

            if last_key in ignore_translate_keys:
                trs_lang[lang_code] = replace_data(
                    trs_lang[lang_code].copy(), way, 
                        dict_way(main_lang.copy(), way)
                            )
            else:
                trs_lang[lang_code] = replace_data(
                    trs_lang[lang_code].copy(), way, 
                        translate(dict_way(main_lang.copy(), way), lang_code)
                            )

            damp[lang_code] = replace_data(
                damp[lang_code].copy(), way, 
                    dict_way(main_lang.copy(), way)
                        )

            save(trs_lang, lang_code)
            save(damp, lang_code, 'damps')

    return data

if __name__ == '__main__':
    main()