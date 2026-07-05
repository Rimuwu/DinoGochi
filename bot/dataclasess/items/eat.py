from typing import Dict, Any, List
from pydantic import Field
from bot.dataclasess.items.base import BaseItem

class Eat(BaseItem):
    act: int = 0
    class_name: str = Field(default='ALL', alias='class')
    buffs: Dict[str, Any] = Field(default_factory=dict)
    drink: bool = False
    states: List[Any] = Field(default_factory=list)
