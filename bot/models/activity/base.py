from typing import Dict, Any, Optional, List, Union
from beanie import Document
from bson.objectid import ObjectId
import time

class KDActivity(Document):
    dino_id: str
    activity_type: str
    end_time: int

    class Settings:
        name = "kd_activity"

    @classmethod
    async def KDActivity.save_kd(cls, dino_id: ObjectId, activity_type: str, kd_time: int) -> dict:
        existing = await cls.find_one(cls.dino_id == str(dino_id), cls.activity_type == activity_type)
        if not existing:
            kd = cls(
                dino_id=str(dino_id),
                activity_type=activity_type,
                end_time=kd_time + int(time.time())
            )
            await kd.insert()
            return kd.model_dump()
        else:
            await existing.update({'$inc': {cls.end_time: kd_time}})
        return {}

    @classmethod
    async def KDActivity.check_activity(cls, dino_id: ObjectId, activity_type: str) -> int:
        fr = await cls.find_one(cls.dino_id == str(dino_id), cls.activity_type == activity_type)
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
    async def KDActivity.check_all_activity(cls, dino_id: ObjectId) -> dict:
        fr_l = await cls.find(cls.dino_id == str(dino_id)).to_list()
        result_dict = {}
        for i in fr_l:
            time_ost = i.end_time - int(time.time())
            if time_ost < 0:
                await i.delete()
            else:
                result_dict[i.activity_type] = time_ost
        return result_dict

class Activity(Document):
    dino_id: str
    activity_type: str
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    class Settings:
        name = "long_activity"
        is_root = True
