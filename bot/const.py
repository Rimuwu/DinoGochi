# Модуль констант
import json


def load_const():
    with open('bot/json/items.json', encoding='utf-8') as f: 
        ITEMS = json.load(f) # type: dict

    with open('bot/json/dino_data.json', encoding='utf-8') as f: 
        DINOS = json.load(f) # type: dict

    with open('bot/json/mobs.json', encoding='utf-8') as f: 
        MOBS = json.load(f) # type: dict

    with open('bot/json/floors_dungeon.json', encoding='utf-8') as f: 
        FLOORS = json.load(f) # type: dict

    with open('bot/json/quests_data.json', encoding='utf-8') as f: 
        QUESTS = json.load(f) # type: list

    with open('bot/json/settings.json', encoding='utf-8') as f: 
        GAME_SETTINGS = json.load(f) # type: dict

    with open('bot/json/backgrounds.json', encoding='utf-8') as f: 
        BACKGROUNDS = json.load(f) # type: dict

    return ITEMS, DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS

ITEMS, DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS = load_const()

def reload_const():
    global ITEMS, DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS
    ITEMS, DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS = load_const()