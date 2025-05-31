# Модуль констант
import json5


def load_const():
    with open('bot/json/dino_data.json', encoding='utf-8') as f: 
        DINOS = json5.load(f) # type: dict

    with open('bot/json/mobs.json', encoding='utf-8') as f: 
        MOBS = json5.load(f) # type: dict

    with open('bot/json/floors_dungeon.json', encoding='utf-8') as f: 
        FLOORS = json5.load(f) # type: dict

    with open('bot/json/quests_data.json', encoding='utf-8') as f: 
        QUESTS = json5.load(f) # type: list

    with open('bot/json/settings.json', encoding='utf-8') as f: 
        GAME_SETTINGS = json5.load(f) # type: dict

    with open('bot/json/backgrounds.json', encoding='utf-8') as f: 
        BACKGROUNDS = json5.load(f) # type: dict

    with open('bot/json/achievements.json', encoding='utf-8') as f:
        ACHIEVEMENTS = json5.load(f) # type: dict

    return DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS

DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS = load_const()

def reload_const():
    global DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS
    DINOS, MOBS, FLOORS, QUESTS, GAME_SETTINGS, BACKGROUNDS, ACHIEVEMENTS = load_const()