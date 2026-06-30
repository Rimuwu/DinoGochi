from typing import Dict, Any, Optional, List, Union
from beanie import Document, PydanticObjectId
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT
import time
from datetime import datetime, timezone
from bot.models.enums import ActivityType

class KDActivity(Document):
    dino_id: Optional[PydanticObjectId] = None
    activity_type: str = ""
    end_time: int = 0
    expireat: Optional[datetime] = None

    class Settings:
        name = "kd_activity"
        indexes = [
            IndexModel([("activity_type", TEXT)], name="activity_type"),
            IndexModel([("dino_id", ASCENDING)], name="dino_id"),
            IndexModel([("expireat", ASCENDING)], expireAfterSeconds=0, name="expireat")
        ]

    @classmethod
    async def save_kd(cls, dino_id: ObjectId, activity_type: str, kd_time: int) -> dict:
        existing = await cls.find_one(cls.dino_id == dino_id, cls.activity_type == activity_type)
        now_time = int(time.time())
        end_time = now_time + kd_time
        expireat = datetime.fromtimestamp(end_time, tz=timezone.utc)
        if not existing:
            kd = cls(
                dino_id=dino_id,
                activity_type=activity_type,
                end_time=end_time,
                expireat=expireat
            )
            await kd.insert()
            return kd.model_dump()
        else:
            new_end = existing.end_time + kd_time
            new_expire = datetime.fromtimestamp(new_end, tz=timezone.utc)
            await existing.update({'$set': {cls.end_time: new_end, cls.expireat: new_expire}})
        return {}

    @classmethod
    async def check_activity(cls, dino_id: ObjectId, activity_type: str) -> int:
        fr = await cls.find_one(cls.dino_id == dino_id, cls.activity_type == activity_type)
        if not fr: 
            return 0
        else:
            time_ost = fr.end_time - int(time.time())
            if time_ost < 0:
                await fr.delete()
                return 0
            else: 
                return time_ost

    @classmethod
    async def check_all_activity(cls, dino_id: ObjectId) -> dict:
        fr_l = await cls.find(cls.dino_id == dino_id).to_list()
        result_dict = {}
        for i in fr_l:
            time_ost = i.end_time - int(time.time())
            if time_ost < 0:
                await i.delete()
            else:
                result_dict[i.activity_type] = time_ost
        return result_dict

class Activity(Document):
    dino_id: Optional[PydanticObjectId] = None
    activity_type: str = ""
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    class Settings:
        name = "long_activity"
        is_root = True
        indexes = [
            IndexModel([("dino_id", ASCENDING)], unique=True, name="dino_id"),
            IndexModel([("activity_type", ASCENDING), ("sleep_end", ASCENDING)], name="activity_type_sleep_end", sparse=True),
            IndexModel([("activity_type", ASCENDING), ("journey_end", ASCENDING)], name="activity_type_journey_end", sparse=True),
            IndexModel([("activity_type", ASCENDING), ("last_check", ASCENDING)], name="activity_type_last_check", sparse=True)
        ]
