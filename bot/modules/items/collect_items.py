from bot.modules.data_format import deepcopy
from bot.modules.logs import log
import os
import json

def gather_json_files(directory):
    json_data = {}

    # Перебираем все файлы в заданной директории
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                items = json.load(file)

                for key, value in items.items():
                    if key in json_data:
                        log(f'{key} уже находится в предметах и был добавлен повторно, проверьте на наличие повторов!', 4)
                    json_data[key] = value

    return json_data

directory_path = 'bot/json/items'
ITEMS = gather_json_files(directory_path)
log(f'Предметы загружены в колличестве {len(ITEMS)} шутк.')

def get_all_items() -> dict: 
    """Возвращает все предметы из json"""
    return deepcopy(ITEMS) # type: ignore