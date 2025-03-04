from tkinter import N
from typing import Literal, Any
from dataclasses import dataclass, field

from bot.modules.dataclasess.ns_craft import NSelement

TYPES = Literal[
    'special', 'sleep', 'recipe', 
    'material', 'eat', 'weapon', 
    'armor', 'backpack', 'case', 
    'book', 'dummy'
]

RANKS = Literal[
    'common', 'uncommon', 'rare', 
    'legendary', 'mystical'
]

@dataclass
class BaseItem:
    # ID из json файла
    data_id: str

    # Тип предмета
    type: TYPES = field(default='dummy')
    
    # Ранг предмета
    rank: RANKS = field(default='common')

    # Название файла .png с изображением предмета
    image: str = field(default='')

    # Можно ли продать предмет скупщику
    buyer: bool = field(default=True)

    # Есть ли запрет на продажу или передачу предмета
    cant_sell: bool = field(default=False)

    # Группы предметов для запросов
    groups: list[str] = field(default_factory=list)

    # Уникальные характеристики предмета
    abilities: dict[str, Any] = field(default_factory=dict)

    # Настольный крафт, доступный без рецепта
    ns_craft: dict[str, NSelement] = field(default_factory=dict)