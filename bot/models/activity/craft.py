from bson.objectid import ObjectId
import time
from bot.models.activity.base import Activity

class CraftActivity(Activity):
    send: int
    last_check: int
    alt_code: str

    @classmethod
    async def start(cls, dino_id: ObjectId, sended: int, duration: int) -> bool:
        from bot.modules.data_format import random_code
        existing = await Activity.find_one(Activity.dino_id == ObjectId(dino_id), with_children=True)
        if not existing:
            act = cls(
                dino_id=str(dino_id),
                activity_type="craft",
                start_time=int(time.time()),
                end_time=int(time.time()) + duration,
                send=sended,
                last_check=int(time.time()),
                alt_code=random_code()
            )
            await act.insert()
            return True
        return False
