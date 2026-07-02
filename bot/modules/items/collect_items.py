from bot.modules.data_format import deepcopy
from bot.modules.logs import log
import os
import json
import sys
from pydantic import ValidationError

# Import all Pydantic item models
from bot.dataclasess.items.eat import Eat
from bot.dataclasess.items.case import Case
from bot.dataclasess.items.nullitems import Book, Dummy, EggItem, Recipe, Special, IncubationBoost, TrainingBoost
from bot.dataclasess.items.accessories import Accessories, DamageAccessories, DefenseAccessories, EquipmentAccessories, Ammunition

ITEM_CLASSES = {
    'eat': Eat,
    'case': Case,
    'book': Book,
    'weapon': DamageAccessories,
    'armor': DefenseAccessories,
    'backpack': DefenseAccessories,
    'sleep': Accessories,
    'special': Special,
    'recipe': Recipe,
    'material': Dummy,
    'dummy': Dummy,
    'collecting': Accessories,
    'game': Accessories,
    'journey': Accessories,
    'egg': EggItem,
    'heal': Dummy,
    'ammunition': Ammunition,
    'rune': Dummy,
    'incubation_boost': IncubationBoost,
    'training_boost': TrainingBoost
}

def validate_item(item_id: str, item_data: dict, file_path: str):
    item_type = item_data.get('type', 'dummy')
    cls = ITEM_CLASSES.get(item_type, Dummy)
    try:
        return cls(data_id=item_id, **item_data)
    except ValidationError as e:
        log_msg = f"\n[❌] Validation Error in item '{item_id}' (file: {file_path}):\n"
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            msg = error['msg']
            input_val = error.get('input', 'N/A')
            log_msg += f"    - Field: {loc}\n      Error: {msg}\n      Provided Value: {input_val}\n"
        log(log_msg, 4)
        print(log_msg, file=sys.stderr)
        raise e

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
                    
                    # Validate and convert to Pydantic object
                    validated_item = validate_item(key, value, file_path)
                    json_data[key] = validated_item

    return json_data

directory_path = 'bot/json/items'
ITEMS = gather_json_files(directory_path)
log(f'Предметы загружены в колличестве {len(ITEMS)} шутк.')

def get_all_items() -> dict: return deepcopy(ITEMS) # type: ignore

def reload_items() -> None:
    global ITEMS
    new_items = gather_json_files(directory_path)
    ITEMS.clear()
    ITEMS.update(new_items)
    log(f'Предметы перезагружены в колличестве {len(ITEMS)} шутк.')