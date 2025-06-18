# Модуль загрузки локлизации

import json
import os
from typing import Any
from bot.modules.logs import log
from bot.dbmanager import mongo_client
from bot.modules.time_counter import time_counter

languages = {}
available_locales = []

from bot.modules.overwriting.DataCalsses import DBconstructor
import re
langs = DBconstructor(mongo_client.user.lang)
users = DBconstructor(mongo_client.user.users)

def load() -> None:
    global languages, available_locales
    """Загрузка локализации"""

    for filename in os.listdir("./bot/localization"):
        with open(f'./bot/localization/{filename}', encoding='utf-8') as f:
            languages_f = json.load(f)

        for l_key in languages_f.keys():
            available_locales.append(l_key)
            languages[l_key] = languages_f[l_key]

    log(f"Загружено {len(languages.keys())} файла(ов) локализации.", 1)

def alternative_language(lang: str):
    languages = {
        'ua': 'ru'
    }
    try:
        if lang in languages: return languages[lang]
    except:
        log(f"Not found lang {lang}", 3)
    return lang

def resolve_translate_urls(data: Any, locale: str) -> Any:
    """
    Рекурсивно проходит по всем ключам локализации, ищет текстовые значения,
    заменяет {translate_url:...} на переводы.
    """
    if isinstance(data, dict):
        return {k: resolve_translate_urls(v, locale) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_translate_urls(item, locale) for item in data]
    elif isinstance(data, str):
        text = data
        matches = list(re.finditer(r'\{translate_url:([^}]+)\}', text))
        for match in matches:
            inner_key = match.group(1)
            translated = str(get_data(inner_key, locale))
            text = text.replace(match.group(0), translated, 1)
        return text
    else:
        return data

def get_data(key: str, locale: str | None) -> Any:
    """Возвращает данные локализации

    Args:
        key (str): ключ
        locale (str, optional): язык. Defaults to "en".

    Returns:
        str | dict: возвращаемое
    """
    if not locale: locale = 'en'
    locale = alternative_language(locale)
    if locale not in available_locales:
        locale = 'en' # Если язык не найден, установить тот что точно есть

    localed_data = languages[locale]

    for way_key in key.split('.'):
        if way_key.isdigit() and type(localed_data) == list:
            way_key = int(way_key)

        if way_key in localed_data or type(way_key) == int:
            if way_key or way_key == 0:
                try:
                    localed_data = localed_data[way_key] 
                except Exception as e:
                    log(f'localiztion.get_data {e}\nway_key - {way_key} locale - {locale} key - {key}', 4)
        else:
            log(f'Ключ {key} ({locale}) не найден!', 4)
            return languages[locale]["no_text_key"].format(key=key)

    localed_data = resolve_translate_urls(localed_data, locale)
    return localed_data

def t(key: str, locale: str | None = "en", formating: bool = True, **kwargs) -> str:
    """Возвращает текст на нужном языке
    Ключи типа "text {translate_url:key.key}" это внутренние ключи на какой либо текст

    Args:
        key (str): ключ для текста
        locale (str, optional): код языка. Defaults to "en".

    Returns:
        str: текст на нужном языке
    """
    if not locale:
        locale = 'en'
    text = str(get_data(key, locale))  # Добавляем переменные в текст

    # Ищем все вхождения {translate_url:...} и заменяем их на перевод
    matches = list(re.finditer(r'\{translate_url:([^}]+)\}', text))
    for match in matches:
        inner_key = match.group(1)
        translated = str(get_data(inner_key, locale))
        # Заменяем только первое вхождение, чтобы избежать повторной замены уже изменённого текста
        text = text.replace(match.group(0), translated, 1)

    if formating:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            log(f'Не удалось выполнить форматирование, ошибка -> {e}', 2)

    return text


def tranlate_data(data, locale: str = "en", key_prefix = '', **kwargs) -> Any:
    """ Переводит текст внутри словаря или списка
        
        Args:
        key_prefix - добавляет ко всем ключам префикс

        Example:
            > data = ['enable', 'disable']
            > key_prefix = 'commands_name.'
        >> ['✅ Включить', '❌ Выключить']

        Чтобы отменить префикс, добавьте "noprefix." перед элементом.
        Чтобы отменить перевод добавьте "notranslate." перед элементом.
    """

    if type(data) == list:

        def tr_list(lst):
            result_list = []
            for element in lst:
                if type(element) == str:
                    if key_prefix:
                        if not element.startswith('noprefix.') and not element.startswith('notranslate.'):
                            element = key_prefix + element
                        else:
                            element = element.replace('noprefix.', '')

                    if not element.startswith('notranslate.'):
                        result_list.append(t(element, locale, **kwargs))
                    else:
                        result_list.append(
                            element.replace('notranslate.', ''))
                else:
                    result_list.append(tr_list(element))

            return result_list

        result_list = tr_list(data)
        return result_list

    elif type(data) == dict:
        result_dict = {}
        for key, value in data:
            if key_prefix:
                if not value.startswith('noprefix.'):
                    value = key_prefix + value
                else:
                    value.replace('noprefix.', '')

            result_dict[key] = t(value, locale, **kwargs)

        return result_dict

def get_all_locales(key: str, **kwargs) -> dict:
    """Возвращает текст с ключа key из каждой локализации
    
    Args:
        key (str): ключ для текста

    Returns:
        dict[str]: ключ в словаре - код языка
    """
    locales_dict = {}

    for locale in available_locales:
        locales_dict[locale] = get_data(key, locale, **kwargs)

    return locales_dict

async def get_lang(userid: int, alternative: str = 'en') -> str:
    """ Получает язык пользователя
    """
    lang = alternative
    data = await langs.find_one({'userid': userid}, comment='get_lang')

    if data: lang = data['lang']
    else:
        if await users.find_one({'userid': userid}):
            await langs.insert_one({'userid': userid, 'lang': lang}, comment='get_lang_isert_lang')
    return lang

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")
else: 
    time_counter('localization', 'Загрузка локализации')
    load()
    time_counter('localization', 'Загрузка локализации')
