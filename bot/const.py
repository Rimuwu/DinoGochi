# Модуль констант
import os
from typing import Any
import json5
import orjson
from concurrent.futures import ThreadPoolExecutor

from bot.modules.time_counter import time_counter

DINOS: dict[str, Any]
MOBS: dict[str, Any]
FLOORS: dict[str, Any]
QUESTS: dict[str, Any]
GAME_SETTINGS: dict[str, Any]
BACKGROUNDS: dict[str, Any]
ACHIEVEMENTS: dict[str, Any]
MAP: dict[str, Any]
STRUCTURE_LEVELS: dict[str, Any]

files = {
    'DINOS': 'bot/json/dino_data.json',
    'MOBS': 'bot/json/mobs.json', 
    'FLOORS': 'bot/json/floors_dungeon.json',
    'QUESTS': 'bot/json/quests_data.json',
    'GAME_SETTINGS': 'bot/json/settings.json',
    'BACKGROUNDS': 'bot/json/backgrounds.json',
    'ACHIEVEMENTS': 'bot/json/achievements.json',
    "MAP": 'bot/json/map.json',
    "STRUCTURE_LEVELS": 'bot/json/structure_levels.json',
}

def load_json_auto(filepath, threshold_kb=500):
    size_kb = os.path.getsize(filepath) / 1024
    if size_kb > threshold_kb:
        with open(filepath, 'rb') as f:
            return orjson.loads(f.read())
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json5.load(f)

def load_constants():
    """Параллельная загрузка констант"""
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(load_json_auto, files.values()))
    return dict(zip(files.keys(), results))

time_counter('load_constants', 'Загрузка констант')
constants = load_constants()
globals().update(constants)
time_counter('load_constants', 'Загрузка констант')
