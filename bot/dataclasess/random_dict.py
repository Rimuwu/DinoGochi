from dataclasses import dataclass, field
from typing import Literal

TYPES = Literal['random', 'choice', 'static']

@dataclass
class RandomDict:
    """ Предоставляет общий формат данных, подерживающий 
       случайные и статичные элементы.

        Типы словаря:
        { "min": 1, "max": 2, "type": "random" }
        >>> Случайное число от 1 до 2
        { "act": [12, 42, 1], "type": "choice" } 
        >>> Случайный элемент
        { "act": 1, "type": "static" }
        >>> Статичное число 1
    """

    act: int | list = field(default=0)
    min: int | None = field(default=None)
    max: int | None = field(default=None)
    type: TYPES = field(default='static')
