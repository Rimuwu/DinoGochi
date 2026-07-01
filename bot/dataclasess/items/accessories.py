from typing import Dict, Any, List
from pydantic import Field
from bot.dataclasess.items.base import BaseItem

class Accessories(BaseItem):
    """ Все типы аксессуаров
        Если нет act, то = 0
    """
    act: int = 0

class DamageAccessories(BaseItem):
    """ Оружия
    """
    damage: Dict[str, int] = Field(default_factory=lambda: {
        "max": 1,
        "min": 0
    })
    effectiv: int = 1
    class_name: str = Field(default='', alias='class')
    ammunition: List[str] = Field(default_factory=list)

class DefenseAccessories(BaseItem):
    """ Щиты, доспехи
    """
    reflection: int = 1
    capacity: int = 0  # Вместимость рюкзаков

class EquipmentAccessories(BaseItem):
    """ Инструменты
    """
    damage: Dict[str, int] = Field(default_factory=lambda: {
        "max": 1,
        "min": 0
    })
    effectiv: int = 1

class Ammunition(BaseItem):
    """ Боеприпасы (стрелы и т.д.)
    """
    add_damage: int = 0
    add_effects: List[Any] = Field(default_factory=list)