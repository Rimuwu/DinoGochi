from typing import Dict, Any, Optional
from beanie import Document

class Quest(Document):
    owner_id: int
    alt_id: str
    quest_id: str
    stage: int = 0
    time_end: int

    class Settings:
        name = "quests"

class Tavern(Document):
    owner_id: int
    data: Dict[str, Any]

    class Settings:
        name = "tavern"

class DailyAward(Document):
    owner_id: int
    time_end: int
    streak: int = 0

    class Settings:
        name = "daily_award"

class InsideShop(Document):
    owner_id: int
    data: Dict[str, Any]

    class Settings:
        name = "inside_shop"
