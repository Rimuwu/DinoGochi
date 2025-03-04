from dataclasses import dataclass, field
from typing import Literal
from base import BaseItem

EAT_CLASS = Literal['ALL', 'Carnivore', 'Herbivore']

@dataclass
class Eat(BaseItem):
    act: int = field(default=0)
    _class: EAT_CLASS = field(default='ALL')
