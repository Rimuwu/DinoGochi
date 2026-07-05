from typing import Dict, List, Any
from pydantic import Field
from bot.dataclasess.items.base import BaseItem

class Case(BaseItem):
    col_repit: Dict[str, Any] = Field(default_factory=lambda: {
        "act": 1,
        "type": "static"
    })
    drop_items: List[Any] = Field(default_factory=list)