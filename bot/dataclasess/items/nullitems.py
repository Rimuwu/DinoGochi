from typing import Dict, List, Any, Union
from pydantic import Field
from bot.dataclasess.items.base import BaseItem

class Book(BaseItem):
    pass

class Dummy(BaseItem):
    pass

class EggItem(BaseItem):
    inc_type: str = ""
    incub_time: int = 0

class Recipe(BaseItem):
    create: Dict[str, Any] = Field(default_factory=dict)
    ignore_preview: List[str] = Field(default_factory=list)
    materials: List[Dict[str, Any]] = Field(default_factory=list)
    time_craft: int = 0

class Special(BaseItem):
    class_name: str = Field(default='', alias='class')
    premium_time: Union[int, str] = 0
    time: Union[int, str] = 0


class IncubationBoost(BaseItem):
    time_boost: int = 0
