from typing import List, Optional
from bson.objectid import ObjectId
import time
from pydantic import Field
from bot.models.activity.base import Activity

class TrainingActivity(Activity):
    send: int
    use_energy: bool = False
    up_skill: str
    down_skill: str
    up_unit: List[float] = Field(default_factory=list)
    down_unit: List[float] = Field(default_factory=list)
    last_check: int
    alt_code: str
    up: float = 0.0
    min_time: int
    max_time: int
    ahtung_lvl: int = 0

    @classmethod
    async def start(cls, dino_id: ObjectId, activity: str, up: str, down: str, 
                    up_unit: list[float], down_unit: list[float], sended: int) -> Optional[dict]:
        from bot.modules.dinosaur.dino_status import get_skill_time
        from bot.modules.data_format import random_code

        existing = await cls.find_one(cls.dino_id == ObjectId(dino_id))
        if not existing:
            skl_time = get_skill_time(activity)
            act = cls(
                dino_id=str(dino_id),
                activity_type=activity,
                start_time=int(time.time()),
                end_time=int(time.time()) + skl_time[1],
                send=sended,
                use_energy=False,
                up_skill=up,
                down_skill=down,
                up_unit=up_unit,
                down_unit=down_unit,
                last_check=int(time.time()),
                alt_code=random_code(),
                up=0.0,
                min_time=skl_time[0],
                max_time=skl_time[1],
                ahtung_lvl=0
            )
            await act.insert()
            return act.model_dump()
        return None

    @classmethod
    async def end(cls, dino_id: ObjectId) -> int:
        act = await cls.find_one(cls.dino_id == ObjectId(dino_id))
        if act:
            await act.delete()
            return 1
        return 0
