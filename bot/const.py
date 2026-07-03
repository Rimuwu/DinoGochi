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

    with open('bot/json/floors_dungeon.json', encoding='utf-8') as f: 
        FLOORS = json.load(f) # type: dict

    with open('bot/json/quests_data.json', encoding='utf-8') as f: 
        QUESTS = json.load(f) # type: list

    with open('bot/json/settings.json', encoding='utf-8') as f: 
        GAME_SETTINGS = json5.load(f) # type: dict

    with open('bot/json/backgrounds.json', encoding='utf-8') as f: 
        BACKGROUNDS = json.load(f) # type: dict

    with open('bot/json/achievements.json', encoding='utf-8') as f:
        ACHIEVEMENTS = json.load(f) # type: dict

    COMBAT_STRATEGIES = load_json_without_comments('bot/json/combat_strategies.json')

    return DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES

DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES = load_const()

def reload_const():
    global DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES
    DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS, COMBAT_STRATEGIES = load_const()