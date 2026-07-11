from typing import List, Optional, Dict, Any
from bson.objectid import ObjectId
import time
from pydantic import Field
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.dinosaur import Dino

class TrainingActivity(Activity):
    userid: int = 0
    use_energy: bool = False
    up_skill: str
    sec_skill: str
    up_unit: List[float] = Field(default_factory=list)
    sec_unit: List[float] = Field(default_factory=list)
    last_check: int
    alt_code: str
    up: float = 0.0
    min_time: int
    max_time: int
    ahtung_lvl: int = 0
    training_boost: Optional[Dict[str, Any]] = None

    @classmethod
    async def start(cls, dino_id: ObjectId, activity: str, up: str, sec: str, 
                    up_unit: list[float], sec_unit: list[float], sended: int) -> Optional[dict]:
        from bot.modules.data_format import random_code

        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return None

            skl_time = Dino.get_skill_time(activity)
            act = cls(
                dino=dino_obj,
                activity_type=activity,
                start_time=int(time.time()),
                end_time=int(time.time()) + skl_time[1],
                userid=sended,
                use_energy=False,
                up_skill=up,
                sec_skill=sec,
                up_unit=up_unit,
                sec_unit=sec_unit,
                last_check=int(time.time()),
                alt_code=random_code(),
                up=0.0,
                min_time=skl_time[0],
                max_time=skl_time[1],
                ahtung_lvl=0
            )
            try:
                await act.insert()
                from bot.modules.dino_status_cache import invalidate_status_cache
                await invalidate_status_cache(dino_oid)
            except DuplicateKeyError:
                return None
            return act.model_dump()
        return None

    @classmethod
    async def end(cls, dino_id: ObjectId) -> int:
        act = await cls.find_one(cls.dino.id == ObjectId(dino_id))
        if act:
            await act.delete()
            from bot.modules.dino_status_cache import invalidate_status_cache
            await invalidate_status_cache(dino_id)
            return 1
        return 0
