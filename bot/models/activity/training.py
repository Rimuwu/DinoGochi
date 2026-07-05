from typing import List, Optional, Dict, Any
from bson.objectid import ObjectId
import time
from pydantic import Field
from bot.models.activity.base import Activity

class TrainingActivity(Activity):
    send: int
    use_energy: bool = False
    # Первичный навык для прокачки
    up_skill: str
    # Вторичный навык (тоже прокачивается, хотя и медленнее)
    sec_skill: str
    up_unit: List[float] = Field(default_factory=list)
    sec_unit: List[float] = Field(default_factory=list)
    last_check: int
    alt_code: str
    up: float = 0.0
    min_time: int
    max_time: int
    ahtung_lvl: int = 0
    # Активный бустер: { bonus_percent: float, expires_at: int }
    training_boost: Optional[Dict[str, Any]] = None

    @classmethod
    async def start(cls, dino_id: ObjectId, activity: str, up: str, sec: str, 
                    up_unit: list[float], sec_unit: list[float], sended: int) -> Optional[dict]:
        from bot.modules.dinosaur.dino_status import get_skill_time
        from bot.modules.data_format import random_code

        existing = await Activity.find_one(Activity.dino_id == ObjectId(dino_id), with_children=True)
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
