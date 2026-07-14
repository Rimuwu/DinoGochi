# Модуль констант
import json
import json5
import re

# Initialize global containers to keep their object identity (id()) constant across reloads.
# This avoids duplicate memory allocation in modules that imported them using "from bot.const import ...".
DINOS = {}
MOBS = {}
QUESTS = []
GAME_SETTINGS = {}
BACKGROUNDS = {}
ACHIEVEMENTS = {}
COMBAT_STRATEGIES = {}
CUSTOM_EMOJIS = {}
ITEMS_CUSTOM_EMOJIS = {}

def load_json_without_comments(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        # Remove single-line comments starting with //
        content = re.sub(r'//.*', '', content)
        return json.loads(content)
    except Exception:
        return {}


def _load_const_files():
    with open('bot/json/dino_data.json', encoding='utf-8') as f: 
        loaded_dinos = json.load(f) # type: dict

    with open('bot/json/mobs.json', encoding='utf-8') as f: 
        loaded_mobs = json.load(f) # type: dict

    with open('bot/json/quests_data.json', encoding='utf-8') as f: 
        loaded_quests = json.load(f) # type: list

    with open('bot/json/settings.json', encoding='utf-8') as f: 
        loaded_settings = json5.load(f) # type: dict

    try:
        with open('bot/json/premium_shop.json', encoding='utf-8') as f:
            loaded_settings['products'] = json.load(f)
    except Exception:
        loaded_settings['products'] = {}

    try:
        with open('bot/json/super_shop.json', encoding='utf-8') as f:
            loaded_settings['super_shop'] = json.load(f)
    except Exception:
        loaded_settings['super_shop'] = {}

    with open('bot/json/backgrounds.json', encoding='utf-8') as f: 
        loaded_bg = json.load(f) # type: dict

    with open('bot/json/achievements.json', encoding='utf-8') as f:
        loaded_ach = json.load(f) # type: dict

    loaded_combat = load_json_without_comments('bot/json/combat_strategies.json')

    try:
        with open('bot/json/custom_emojis.json', encoding='utf-8') as f:
            loaded_emojis = json.load(f)
        import os
        ids_path = 'data/custom_emojis.json'
        if os.path.exists(ids_path):
            with open(ids_path, encoding='utf-8') as f:
                saved_ids = json.load(f)
            for k, val in saved_ids.items():
                if k in loaded_emojis:
                    if isinstance(val, dict):
                        loaded_emojis[k]['id'] = val.get('id', '')
                    else:
                        loaded_emojis[k]['id'] = str(val)
    except Exception:
        loaded_emojis = {}

    try:
        with open('bot/json/items_custom_emojis.json', encoding='utf-8') as f:
            loaded_item_emojis = json.load(f)
        import os
        ids_path = 'data/items_custom_emojis.json'
        if os.path.exists(ids_path):
            with open(ids_path, encoding='utf-8') as f:
                saved_ids = json.load(f)
            for k, val in saved_ids.items():
                if k in loaded_item_emojis:
                    if isinstance(val, dict):
                        loaded_item_emojis[k]['id'] = val.get('id', '')
                        loaded_item_emojis[k]['rare_id'] = val.get('rare_id', '')
                    else:
                        loaded_item_emojis[k]['id'] = str(val)
    except Exception:
        loaded_item_emojis = {}

    return (loaded_dinos, loaded_mobs, loaded_quests, loaded_settings, 
            loaded_bg, loaded_ach, loaded_combat, loaded_emojis, loaded_item_emojis)

def update_in_place(target, source):
    if isinstance(target, dict) and isinstance(source, dict):
        target.clear()
        target.update(source)
    elif isinstance(target, list) and isinstance(source, list):
        target.clear()
        target.extend(source)

def reload_const():
    (new_dinos, new_mobs, new_quests, new_settings, 
     new_bg, new_ach, new_combat, new_emojis, new_item_emojis) = _load_const_files()
     
    update_in_place(DINOS, new_dinos)
    update_in_place(MOBS, new_mobs)
    update_in_place(QUESTS, new_quests)
    update_in_place(GAME_SETTINGS, new_settings)
    update_in_place(BACKGROUNDS, new_bg)
    update_in_place(ACHIEVEMENTS, new_ach)
    update_in_place(COMBAT_STRATEGIES, new_combat)
    update_in_place(CUSTOM_EMOJIS, new_emojis)
    update_in_place(ITEMS_CUSTOM_EMOJIS, new_item_emojis)

# Initial load
reload_const()