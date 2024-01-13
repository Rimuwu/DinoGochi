import json
import time
import random
import os
import emoji

# import translators
# from langdetect import DetectorFactory, detect


"""
Процесс

0. Проверить есть ли сохранение языка и его перевод
  1.1 Если нет перевода - перевести
  1.2 Если есть перевод и дамп текста на main_lang языке - анализ всех ключей
1. Если есть несоответсвующие / отсутсвующие ключи - Перевести
2. Сохранить новые данные ключ в дамп памяти

"""

main_code = 'ru'
langs_path = '/languages/'
damp_path = '/damps/'

ex = os.path.dirname(__file__) # Путь к этому файлу

def get_damp(lang_code:str):
    """Получает данные дампа"""
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

    with open(f'{ex}{langs_path}/{lang_code}.json', encoding='utf-8') as f: 
        lang = json.load(f) # type: dict
    return lang

def get_translate_langs():
    """Проверяет дерикторию langs_path и получает оттуда название файлов (языки на которые надо переводить текст)"""

    lst = os.listdir(ex + langs_path)

    res = []
    for i in lst:
        if i.endswith('.json'):
            i = i.replace('.json', '')
            res.append(i)

    if main_code in res: res.remove(main_code)
    return res

def translate(data, to_lang:str):
    """Возвращает переведённый текст"""
    if type(data) == int: return data
    if type(data) == str: return f'{data} - {to_lang}'
    
    print(f"Не переведено {data}")
    return data

def check_damp():
    """Проверяет на наличие и отличие ключа в переведённом дампе"""

def save(data, lang, dr='languages'):
    """Сохраняет файл языка"""

    with open(f'{ex}\{dr}\{lang}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def dict_way(dct:dict, way:str):
    """ Получает значение следуя по пути"""

    for way_key in way.split('.'):
        if way_key.isdigit() and type(dct) == list:
            way_key = int(way_key)

        if way_key in dct or type(way_key) == int:
            if way_key or way_key == 0:
                try:
                    dct = dct[way_key]  # type: ignore
                except: return None
        else: return None
    return dct

def save_key_to_way(dct:dict, way:str, new_data):
    """ Получает значение следуя по пути"""
    lst = way.split('.')
    last = lst[-1]
    lst.remove(last)

    for way_key in lst:
        if way_key.isdigit() and type(dct) == list:
            way_key = int(way_key)

        if way_key in dct or type(way_key) == int:
            if way_key or way_key == 0:
                dct = dct[way_key]  # type: ignore

    print(last, 'last', dct)
    if last.isdigit():
        dct[int(last)] = new_data
    else:
        dct[last] = new_data # type: ignore
    return dct

def way_check(main_direct, damp_direct, way: str):
    """ Проверяет есть ли отличия в сохранённом дампе языка и в главном языковом файле
        На вход получает словари и проверяет их на совпадение
        На выход передаёт список с путём ключей
    """
    way_main = dict_way(main_direct, way)
    way_damp = dict_way(damp_direct, way)
    print(way, way_main, way_damp, 'cchk')

    if way_damp is None: return way
    
    if type(way_main) in [int, str]:
        if way_main != way_damp: return way

    elif type(way_main) == dict:
        lst = []
        for key in way_main.keys():
            res = way_check(main_direct, damp_direct, way+f'.{key}')
            if res: 
                if type(res) == list: lst += res
                else: lst.append(res)

        if lst: return lst

    elif type(way_main) == list:
        lst = []
        for i in way_main:
            ind = way_main.index(i)
            res = way_check(main_direct, damp_direct, way+f'.{ind}')
            if res: 
                if type(res) == list: lst += res
                else: lst.append(res)

        if lst: return lst


to_langs = get_translate_langs() # Языки на которые надо переводить
main_lang = get_lang(main_code)[main_code] # Данные главного языка

for lang_code in to_langs:
    damp = get_damp(lang_code)
    trs_lang = get_lang(lang_code)

    if lang_code not in trs_lang:
        trs_lang = {lang_code:{}}
        save(trs_lang, lang_code)

    nt_keys = []
    for key, value in main_lang.items():
        res = way_check(main_lang, damp[lang_code], key)
        if res: 
            if type(res) == list: nt_keys += res
            else: nt_keys.append(res)
    
    print(nt_keys, 'nt')
    
    for way in nt_keys:
        trs_lang[lang_code] = save_key_to_way(trs_lang[lang_code], way,  # type: ignore
            translate(dict_way(main_lang, way), lang_code))

        damp[lang_code] = save_key_to_way(damp[lang_code], way, dict_way(main_lang, way))

        save(trs_lang, lang_code)
        save(damp, lang_code, 'damps')