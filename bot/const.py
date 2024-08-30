# Модуль констант
import json


def load_const():
    with open('bot/json/dino_data.json', encoding='utf-8') as f: 
        DINOS = json.load(f).copy() # type: dict

    with open('bot/json/mobs.json', encoding='utf-8') as f: 
        MOBS = json.load(f).copy() # type: dict

    with open('bot/json/floors_dungeon.json', encoding='utf-8') as f: 
        FLOORS = json.load(f).copy() # type: dict

    with open('bot/json/quests_data.json', encoding='utf-8') as f: 
        QUESTS = json.load(f).copy() # type: list

    with open('bot/json/settings.json', encoding='utf-8') as f: 
        GAME_SETTINGS = json.load(f).copy() # type: dict

    with open('bot/json/backgrounds.json', encoding='utf-8') as f: 
        BACKGROUNDS = json.load(f).copy() # type: dict

    return DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS

DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS = load_const()

def reload_const():
    global DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS
    DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS = load_const()