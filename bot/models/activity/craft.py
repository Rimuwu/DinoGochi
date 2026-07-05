from bson.objectid import ObjectId
import time
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity

class CraftActivity(Activity):
    send: int
    last_check: int
    alt_code: str

    @classmethod
    async def start(cls, dino_id: ObjectId, sended: int, duration: int) -> bool:
        from bot.modules.data_format import random_code
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            {'dino_id': {'$in': [dino_oid, str(dino_oid)]}},
            with_children=True
        )
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
            try:
                await act.insert()
            except DuplicateKeyError:
                return False
            return True
        return False
