from typing import Literal, Any, List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from bot.dataclasess.ns_craft import NSelement

TYPES = Literal[
    'special', 'sleep', 'recipe', 
    'material', 'eat', 'weapon', 
    'armor', 'backpack', 'case', 
    'book', 'dummy', 'collecting',
    'game', 'journey', 'egg', 'heal', 'rune', 'incubation_boost', 'training_boost'
]

RANKS = Literal[
    'common', 'uncommon', 'rare', 
    'legendary', 'mystical'
]

class BaseItem(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    # ID из json файла
    data_id: str

    # Тип предмета
    type: str = 'dummy'
    
    # Ранг предмета
    rank: str = 'common'

    # Настройки изображения предмета или название файла
    image: Dict[str, str] | str = ''

    # Стандартный эмодзи предмета
    emoji: str = ''

    # Можно ли продать предмет скупщику
    buyer: bool = True

    # Цена продажи скупщику
    buyer_price: Optional[int] = None

    # Есть ли запрет на продажу или передачу предмета
    cant_sell: bool = False

    # Группы предметов для запросов
    groups: List[str] = Field(default_factory=list)

    # Уникальные характеристики предмета
    abilities: Dict[str, Any] = Field(default_factory=dict)

    # Настольный крафт, доступный без рецепта
    ns_craft: Dict[str, NSelement] = Field(default_factory=dict)

    def __getitem__(self, item):
        if item == 'class':
            item = 'class_name'
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def get(self, item, default=None):
        if item == 'class':
            item = 'class_name'
        return getattr(self, item, default)

    def __contains__(self, item):
        if item == 'class':
            item = 'class_name'
        return hasattr(self, item)

    def keys(self):
        keys_set = set(self.model_fields.keys()).union(self.__pydantic_extra__ or {})
        if 'class_name' in keys_set:
            keys_set.remove('class_name')
            keys_set.add('class')
        return keys_set

    def values(self):
        return [self.get(k) for k in self.keys()]

    def items(self):
        return [(k, self.get(k)) for k in self.keys()]