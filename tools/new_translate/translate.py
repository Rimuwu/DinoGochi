import json
import time
import random
import os
import emoji
from pprint import pprint
import copy

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

def remove_non_dict_or_list(dct):
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

    for key in keys_to_remove:
        dct[key] = 'NOTEXT'

    return dct

def replace_data(dct: dict, way: str, new) -> dict:
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
            if lst[-1] + 1 >= len(current_dict):
                current_dict.insert(lst[-1], new) # type: ignore
            else:
                current_dict[lst[-1]] = new # type: ignore
        elif isinstance(current_dict, dict):
            current_dict[lst[-1]] = new # type: ignore
    return new_dct

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

    if isinstance(data, (int, float)): data = data
    elif isinstance(data, str): data =  f'{data} - {to_lang}'

    elif isinstance(data, dict):
        out_data = data.copy()

        for key, value in data.items():
            out_data[key] = translate(value, to_lang)
        return out_data

    elif isinstance(data, list):
        lst = []
        for i in data: lst.append(translate(i, to_lang))
        data = lst

    else: print(f"Не переведено {data}")
    return data

def save(data, lang, dr='languages'):
    """Сохраняет файл языка"""
    print('Сохранение данных')

    with open(f'{ex}\{dr}\{lang}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def dict_way(dct:dict, way:str):
    """ Получает значение следуя по пути"""
    dct = dct.copy()
    new_dct = dct

    for way_key in way.split('.'):
        if way_key.isdigit() and isinstance(new_dct, list):
            way_key = int(way_key)

        if way_key in new_dct or isinstance(way_key, int):
            if way_key or way_key == 0:
                try:
                    new_dct = new_dct[way_key]  # type: ignore
                except: 
                    return None
        else:
            return None

    return new_dct

def key_check(direct, way: str, non: bool = True):
    """ 
    """
    way_main = dict_way(direct, way)

    if way_main is None and non: 
        return [way]

    if isinstance(way_main, dict):
        lst = []
        for key in way_main.keys():
            res = key_check(way_main, key)
            if res: lst += res

        if lst: return lst

    elif isinstance(way_main, list):
        lst = []
        for i in way_main:
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
    main_direct = main_direct.copy()
    damp_direct = damp_direct.copy()

    way_main = dict_way(main_direct, way)
    way_damp = dict_way(damp_direct, way)

    if way_damp is None and non: 
        return [way]

    if isinstance(way_main, (int, str, float)):
        if way_main != way_damp: return [way]

    elif isinstance(way_main, dict):
        lst = []
        for key in way_main.keys():
            res = way_check(main_direct, damp_direct, way+f'.{key}')
            if res: lst += res

        if lst: return lst

    elif isinstance(way_main, list):
        lst = []
        for i in way_main:
            ind = way_main.index(i)
            res = way_check(main_direct, damp_direct, way+f'.{ind}')
            if res: lst += res

        if lst: return lst
    
    else:
        print(type(way_main), 'error')
    return []


def main():
    to_langs = get_translate_langs() # Языки на которые надо переводить

    for lang_code in to_langs:
        damp = get_damp(lang_code)
        trs_lang = get_lang(lang_code)

        main_lang = get_lang(main_code)[main_code] # Данные главного языка

        if lang_code not in trs_lang:
            trs_lang = {lang_code:{}}
            save(trs_lang, lang_code)

        if lang_code not in damp:
            damp = {lang_code:{}}
            save(damp, lang_code, 'damps')

        """ Удаление удалённых ключей """
        for key, value in damp[lang_code].items():
            res = key_check(main_lang.copy(), key)
            print(res, 'del')

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

        """ Создание структуры данных """
        rm_dct = remove_non_dict_or_list(main_lang.copy())
        main_lang = get_lang(main_code)[main_code] # Данные главного языка

        rm_trs_dct = remove_non_dict_or_list(trs_lang.copy())
        trs_lang = get_lang(lang_code)

        ed = False
        for key, value in rm_dct.items():
            res = key_check(rm_trs_dct[lang_code].copy(), key)

            print(res, 'struct')

            if res: 
                ed = True
                for nn_way in res:
                    trs_lang[lang_code] = replace_data(trs_lang[lang_code].copy(), nn_way, dict_way(rm_dct.copy(), nn_way))
        if ed:
            save(trs_lang, lang_code)
            save(trs_lang, lang_code, 'damps')
            main_lang = get_lang(main_code)[main_code]

        """ Определение не достающих ключей"""
        nt_keys = []
        for key, value in main_lang.items():
            res = way_check(main_lang.copy(), damp[lang_code].copy(), key, False)
            if res: nt_keys += res

        print(nt_keys, 'nt')
        damp = get_damp(lang_code)

        """ Перевод ключей """
        for way in nt_keys:
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
        
main()