"""
   Данные которые хранятся в течение дня
   Сохраняются в формате json
"""
from datetime import date
import json
import os
from typing import Any

from bot.modules.logs import log


directory = 'bot/data/daytemp_data.json'

# Глобальный кэш и счётчик изменений
_daytemp_cache = None
_daytemp_cache_dirty = 0
_daytemp_cache_save_threshold = 10


def save(donat_data, force=False):
    """Сохраняет данные в json, если force=True — всегда, иначе только при накоплении изменений"""
    global _daytemp_cache_dirty
    if not force and _daytemp_cache_dirty < _daytemp_cache_save_threshold:
        return
    with open(directory, 'w', encoding='utf-8') as file:
        json.dump(donat_data, file, sort_keys=True, indent=4, ensure_ascii=False)
    _daytemp_cache_dirty = 0


def daytemp_open():
    """Загружает данные обработанных донатов (использует кэш)"""
    global _daytemp_cache
    if _daytemp_cache is not None:
        return _daytemp_cache
    daytemp_data: dict[str, Any] = {}

    try:
        with open(directory, encoding='utf-8') as f: 
            daytemp_data = json.load(f)
    except Exception as error:
        if not os.path.exists(directory):
            with open(directory, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'date': date.today().strftime('%Y-%m-%d')}, ensure_ascii=False, indent=4))
        else:
            log(prefix='daytemp_open', message=f'Error: {error}', lvl=4)
    _daytemp_cache = daytemp_data
    return daytemp_data

def reset_values(d):
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, int):
                d[k] = 0

            elif isinstance(v, list):
                d[k] = []

            elif isinstance(v, dict):
                reset_values(v)

    elif isinstance(d, list):
        d.clear()

def daytemp_processed():
    """ Обработка данных (работает с кэшем) """
    global _daytemp_cache_dirty
    daytemp_data = daytemp_open()
    changed = False

    if 'date' not in daytemp_data:
        daytemp_data['date'] = date.today().strftime('%Y-%m-%d')
        changed = True
    else:
        if daytemp_data['date'] != date.today().strftime('%Y-%m-%d'):
            for key in list(daytemp_data.keys()):
                if key != 'date':
                    reset_values(daytemp_data[key])

            daytemp_data['date'] = date.today().strftime('%Y-%m-%d')
            changed = True
    if changed:
        _daytemp_cache_dirty += 1
        save(daytemp_data)

    return daytemp_data

def add_int_value(path: str, value: int):
    """ Добавляет значение к числу в словаре (работает с кэшем) """
    global _daytemp_cache_dirty
    daytemp_data = daytemp_processed()
    path_lst = path.split('.')

    for key in path_lst[:-1]:
        if key not in daytemp_data:
            daytemp_data[key] = {}
        daytemp_data = daytemp_data[key]

    last_key = path_lst[-1]
    if last_key not in daytemp_data:
        daytemp_data[last_key] = 0

    daytemp_data[last_key] += value
    _daytemp_cache_dirty += 1
    save(_daytemp_cache)


def add_list_value(path: str, value: Any):
    """ Добавляет значение в список в словаре (работает с кэшем) """
    global _daytemp_cache_dirty
    daytemp_data = daytemp_processed()
    path_lst = path.split('.')

    for key in path_lst[:-1]:
        if key not in daytemp_data:
            daytemp_data[key] = {}
        daytemp_data = daytemp_data[key]

    last_key = path_lst[-1]
    if last_key not in daytemp_data:
        daytemp_data[last_key] = []

    if value not in daytemp_data[last_key]:
        daytemp_data[last_key].append(value)
        _daytemp_cache_dirty += 1
        save(_daytemp_cache)

def flush_daytemp_cache():
    """Принудительно сохраняет кэш в файл"""
    global _daytemp_cache
    if _daytemp_cache is not None:
        save(_daytemp_cache, force=True)

def get_daytemp_cache():
    """Возвращает текущий кэш данных дня"""
    global _daytemp_cache
    if _daytemp_cache is None:
        daytemp_open()
    return _daytemp_cache