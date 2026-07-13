# Модуль констант
import json
import json5
import re

def load_json_without_comments(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        # Remove single-line comments starting with //
        content = re.sub(r'//.*', '', content)
        return json.loads(content)
    except Exception:
        return {}


def load_const():
    with open('bot/json/dino_data.json', encoding='utf-8') as f: 
        DINOS = json.load(f) # type: dict

    with open('bot/json/mobs.json', encoding='utf-8') as f: 
        MOBS = json.load(f) # type: dict

    with open('bot/json/quests_data.json', encoding='utf-8') as f: 
        QUESTS = json.load(f) # type: list

    with open('bot/json/settings.json', encoding='utf-8') as f: 
        GAME_SETTINGS = json5.load(f) # type: dict

    try:
        with open('bot/json/premium_shop.json', encoding='utf-8') as f:
            GAME_SETTINGS['products'] = json.load(f)
    except Exception:
        GAME_SETTINGS['products'] = {}

    try:
        with open('bot/json/super_shop.json', encoding='utf-8') as f:
            GAME_SETTINGS['super_shop'] = json.load(f)
    except Exception:
        GAME_SETTINGS['super_shop'] = {}

    with open('bot/json/backgrounds.json', encoding='utf-8') as f: 
        BACKGROUNDS = json.load(f) # type: dict

    with open('bot/json/achievements.json', encoding='utf-8') as f:
        ACHIEVEMENTS = json.load(f) # type: dict

    COMBAT_STRATEGIES = load_json_without_comments('bot/json/combat_strategies.json')

    try:
        with open('bot/json/custom_emojis.json', encoding='utf-8') as f:
            CUSTOM_EMOJIS = json.load(f)
        import os
        ids_path = 'data/custom_emojis.json'
        if os.path.exists(ids_path):
            with open(ids_path, encoding='utf-8') as f:
                saved_ids = json.load(f)
            for k, val in saved_ids.items():
                if k in CUSTOM_EMOJIS:
                    if isinstance(val, dict):
                        CUSTOM_EMOJIS[k]['id'] = val.get('id', '')
                    else:
                        CUSTOM_EMOJIS[k]['id'] = str(val)
    except Exception:
        CUSTOM_EMOJIS = {}

    try:
        with open('bot/json/items_custom_emojis.json', encoding='utf-8') as f:
            ITEMS_CUSTOM_EMOJIS = json.load(f)
        import os
        ids_path = 'data/items_custom_emojis.json'
        if os.path.exists(ids_path):
            with open(ids_path, encoding='utf-8') as f:
                saved_ids = json.load(f)
            for k, val in saved_ids.items():
                if k in ITEMS_CUSTOM_EMOJIS:
                    if isinstance(val, dict):
                        ITEMS_CUSTOM_EMOJIS[k]['id'] = val.get('id', '')
                        ITEMS_CUSTOM_EMOJIS[k]['rare_id'] = val.get('rare_id', '')
                    else:
                        ITEMS_CUSTOM_EMOJIS[k]['id'] = str(val)
    except Exception:
        ITEMS_CUSTOM_EMOJIS = {}

    return DINOS, MOBS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES, CUSTOM_EMOJIS, ITEMS_CUSTOM_EMOJIS

DINOS, MOBS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES, CUSTOM_EMOJIS, ITEMS_CUSTOM_EMOJIS = load_const()

def reload_const():
    global DINOS, MOBS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES, CUSTOM_EMOJIS, ITEMS_CUSTOM_EMOJIS
    DINOS, MOBS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES, CUSTOM_EMOJIS, ITEMS_CUSTOM_EMOJIS = load_const()