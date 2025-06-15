from typing import Any, Dict, List, Literal, Optional, Union
from bot.dataclasess.random_dict import RandomDict
from bot.modules.items import item
from bot.modules.items.collect_items import get_all_items
from typing import Type

ITEMS: dict = get_all_items()

RANKS = Literal[
    'common', 'uncommon', 'rare', 'mystical', 
    'legendary', 'mythical'
    ]

TYPES = Literal[
    'book', 'case', 'collecting', 'weapon', 
    'backpack', 'ammunition', 'armor', 'eat', 
    'egg', 'game', 'dummy', 'journey', 'material',
    'recipe', 'sleep', 'special', 'NO_TYPE'
    ]

JSON_TYPES = Union[int, float, str, bool]

class NullItem:
    
    item_id: str
    type: TYPES
    image: str
    rank: RANKS
    weight: float
    buyer: bool
    buyer_price: Optional[int]
    cant_sell: bool
    groups: List[str]
    abilities: Dict[str, JSON_TYPES]
    buffs: Dict[str, int]
    states: List[Dict[str, Any]]
    ns_craft: Dict[str, Dict[str, Any]]

    def __init__(self, item_id: str) -> None:
        self.item_id: str = item_id
        self.type: TYPES = 'NO_TYPE'
        self.image: str = 'null'
        self.rank: RANKS = 'common'
        # Вес предмета в киллограммах
        self.weight: float = 0.0

        # Можно ли продать предмет боту
        self.buyer: bool = True
        # Переназначение цены скупщика
        self.buyer_price: Optional[int] = None
        # Запрет на продажу
        self.cant_sell: bool = False

        # К каким группам относится предмет
        self.groups: list[str] = []

        # Личные харрактеристики предмета
        self.abilities: Dict[str, JSON_TYPES] = {}

        # Эффекты при использовании предмета
        self.buffs: Dict[str, int] = {}

        # Накладываемые состояния при использовании
        self.states: List[Dict[str, Any]] = []

        # Настольные крафты (без рецепта)
        self.ns_craft: Dict[str, Dict[str, Any]] = {}
        # Пример:
        # "1": {
        #     "time_craft": 7200,
        #     "create": [
        #         "recipe_chest_simple" / 
        #               {"item_id": "blank_piece_paper", "count": 2}
        #     ],
        #     "materials": [
        #         {"item_id": "blank_piece_paper",
        #          "count": 50}
        #     ]
        # }

    def from_json(self) -> Union['Eat', 'Book', 'Case', 'Collecting', 'Game', 'Journey', 'Sleep', 'Weapon', 'Backpack', 'Ammunition', 'Armor', 'Egg', 'Dummy', 'Material', 'Recipe', 'Special', 'NullItem']:
        self.__dict__.update(ITEMS.get(self.item_id, {}))

        clas = get_item_class(self.type)(self.item_id)
        clas.__dict__.update(self.__dict__)
        return clas

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(item_id={self.item_id}, type={self.type}, rank={self.rank})"

    def copy(self):
        new_item = get_item_class(self.type)(self.item_id)
        new_item.__dict__.update(self.__dict__)
        return new_item

ITEM_CLASSES: Dict[str, Type[NullItem]] = {}
def register_item_class(cls):
    global ITEM_CLASSES
    """ Декоратор для регистрации класса предмета в ITEM_CLASSES """

    ITEM_CLASSES[getattr(cls, 'type')] = cls
    return cls

def get_item_class(item_type: TYPES) -> Type[NullItem]:
    """ Возвращает класс предмета по его типу """

    return ITEM_CLASSES.get(item_type, NullItem)

# Книга
@register_item_class
class Book(NullItem):
    type = 'book'

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Коробка удачи
@register_item_class
class Case(NullItem):
    type = 'case'
    col_repit: RandomDict | int | dict = 0
    drop_items: List[str] = []

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Аксессуар сбора пищи
@register_item_class
class Collecting(NullItem):
    type = 'collecting'

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Аксессуар для игры
@register_item_class
class Game(NullItem):
    type = 'game'

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Путешествие
@register_item_class
class Journey(NullItem):
    type = 'journey'

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Сон
@register_item_class
class Sleep(NullItem):
    type = 'sleep'

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Оружие
WEAPON_TYPES = Literal['near', 'far', 'magic']
@register_item_class
class Weapon(NullItem):
    type = 'weapon'
    item_class: WEAPON_TYPES = 'near'
    effectiv: int = 0
    damage: dict[str, int] = {
        "min": 0,
        "max": 0
    }
    ammunition: Optional[list[str]] = None

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Рюкзак
@register_item_class
class Backpack(NullItem):
    type = 'backpack'
    capacity: int = 0

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Боеприпасы
@register_item_class
class Ammunition(NullItem):
    type = 'ammunition'
    add_damage: int = 0
    add_effects: list[str] = []

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Броня
@register_item_class
class Armor(NullItem):
    type = 'armor'
    reflection: int = 0
    # Можно подумать над механикой того, что броня защищает, и например чтобы маленькие дино атаковали ноги / тело, большие - голову / тело

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Еда
EAT_TYPES = Literal['ALL', 'Flying', 'Carnivorous', 'Herbivorous']
@register_item_class
class Eat(NullItem):
    type = 'eat'
    act: int = 0
    item_class: EAT_TYPES = 'ALL'
    drink: bool = False

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Яйцо
INC_TYPES = Literal['random', 'com', 'unc', 'rar', 'mys', 'leg']
@register_item_class
class Egg(NullItem):
    type = 'egg'
    inc_type: INC_TYPES = 'random'
    incub_time: int = 0

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Пустышка / системный предмет
@register_item_class
class Dummy(NullItem):
    type = 'dummy'

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Материал
@register_item_class
class Material(NullItem):
    type = 'material'
    
    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Рецепт
@register_item_class
class Recipe(NullItem):
    type = 'recipe'
    create: dict[str, list[dict[str, Any]]] = {}
    materials: list[dict[str, Any]] = []

    # Время крафта в секундах
    time_craft: int = 0
    # То что не отображается в информации о предмете
    ignore_preview: list[str] = []

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

# Специальный предмет
@register_item_class
class Special(NullItem):
    type = 'special'
    item_class: str = ''

    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)

        if self.item_class == 'premium':
            self.premium_time: int = 0

        elif self.item_class == 'background':
            pass

        elif self.item_class == 'freezing':
            self.time: int | str = 0

        elif self.item_class == 'defrosting':
            pass

        elif self.item_class == 'reborn':
            pass

        elif self.item_class == 'transport':
            pass

        elif self.item_class == 'custom_book':
            pass

        elif self.item_class == 'dino_slot':
            pass

def GetItem(item_id: str):
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if item_id in ITEMS.keys():
        item = NullItem(item_id).from_json()
        return item
    else: 
        raise ValueError(f"Предмет с ID {item_id} не найден в базе данных предметов.")