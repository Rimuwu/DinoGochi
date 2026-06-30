from typing import Dict, Any, Optional
from beanie import Document
from pydantic import Field

class Quest(Document):
    owner_id: Optional[int] = None
    alt_id: str = ""
    quest_id: str = ""
    stage: int = 0
    time_end: int = 0

    class Settings:
        name = "quests"

class Tavern(Document):
    owner_id: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "tavern"

class DailyAward(Document):
    owner_id: Optional[int] = None
    time_end: int = 0
    streak: int = 0

    class Settings:
        name = "daily_award"

class InsideShop(Document):
    owner_id: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "inside_shop"
