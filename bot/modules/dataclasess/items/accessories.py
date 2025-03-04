from dataclasses import dataclass, field
from base import BaseItem


@dataclass
class Accessories(BaseItem):
    """ Все типы аксессуаров
        Если нет act, то = 0
    """
    act: int = field(default=0)

@dataclass
class DamageAccessories(BaseItem):
    """ Оружия
    """
    damage: dict[str, int] = field(default_factory=lambda: {
        "max": 1,
        "min": 0
    })

@dataclass
class DefenseAccessories(BaseItem):
    """ Щиты, доспехи
    """
    reflection: int = field(default=1)

@dataclass
class EquipmentAccessories(BaseItem):
    """ Инструменты
    """
    damage: dict[str, int] = field(default_factory=lambda: {
        "max": 1,
        "min": 0
    })
    effectiv: int = field(default=1)