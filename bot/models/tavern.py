from typing import Dict, Any, Optional
from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING, TEXT

class Quest(Document):
    owner_id: Optional[int] = None
    alt_id: str = ""
    quest_id: str = ""
    stage: int = 0
    time_end: int = 0

    class Settings:
        name = "quests"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], name="owner_id"),
            IndexModel([("alt_id", TEXT)], unique=True, name="alt_id"),
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

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
        indexes = [
            IndexModel([("owner_id", ASCENDING)], unique=True, name="owner_id"),
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

class InsideShop(Document):
    owner_id: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "inside_shop"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], unique=True, name="owner_id")
        ]
