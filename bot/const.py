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
    with open('bot/json/dinosaurs.json', encoding='utf-8') as f:
        dinosaurs_data = json.load(f)
    
    with open('bot/json/eggs.json', encoding='utf-8') as f:
        eggs_data = json.load(f)
        
    with open('bot/json/families.json', encoding='utf-8') as f:
        families_data = json.load(f)
        
    with open('bot/json/cache/cache_quality.json', encoding='utf-8') as f:
        cache_quality = json.load(f)
        
    with open('bot/json/cache/cache_types.json', encoding='utf-8') as f:
        cache_types = json.load(f)

    elements_dict = {}
    families_lower = {k.lower(): v for k, v in families_data.items()}

    for dino_id, dino_prop in dinosaurs_data.items():
        family_name = dino_prop.get('family', '')
        family_data = families_lower.get(family_name.lower(), {})
        category = family_data.get('category', '')

        dino_element = {
            'class': category,
            'hp': dino_prop.get('hp', 0),
            'image': dino_prop.get('image', ''),
            'name': family_name,
            'type': 'dino',
            'egg': dino_prop.get('egg', 0)
        }
        for k, v in dino_prop.items():
            if k not in dino_element:
                dino_element[k] = v
        elements_dict[str(dino_id)] = dino_element

    for egg_id, egg_prop in eggs_data.items():
        egg_element = {
            'image': egg_prop.get('image', ''),
            'type': 'egg'
        }
        for k, v in egg_prop.items():
            if k not in egg_element:
                egg_element[k] = v
        elements_dict[str(egg_id)] = egg_element

    loaded_dinos = {
        'com': cache_quality.get('common', []),
        'unc': cache_quality.get('uncommon', []),
        'rar': cache_quality.get('rare', []),
        'mys': cache_quality.get('epic', []),
        'leg': cache_quality.get('legendary', []),
        'data': {
            'dino': cache_types.get('dino', []),
            'egg': cache_types.get('egg', [])
        },
        'elements': elements_dict,
        'number': len(dinosaurs_data) + len(eggs_data),
        'page': 700
    }

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

    try:
        with open('bot/json/lvl_awards.json', encoding='utf-8') as f:
            loaded_settings['lvl_award'] = json.load(f)
    except Exception:
        loaded_settings['lvl_award'] = {}

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
        # Propagate id/rare_id from master entries to clones
        for k, entry in loaded_item_emojis.items():
            master_key = entry.get('master')
            if master_key and master_key in loaded_item_emojis:
                master = loaded_item_emojis[master_key]
                entry['id'] = master.get('id', '')
                entry['rare_id'] = master.get('rare_id', '')
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