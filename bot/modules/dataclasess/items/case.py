from dataclasses import dataclass, field
from base import BaseItem


@dataclass
class Case(BaseItem):
    col_repit: dict = field(default_factory=lambda: {
        "act": 1,
        "type": "static"
    })
    drop_items: list = field(default_factory=list)