from typing import Optional
from beanie import Link
from bson.objectid import ObjectId
import time
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.user import User
from bot.models.dinosaur import Dino

class CraftActivity(Activity):
    user: Optional[Link[User]] = None
    last_check: int
    alt_code: str

    @classmethod
    async def start(cls, dino_id: ObjectId, sended: int, duration: int) -> bool:
        from bot.modules.data_format import random_code
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            user_obj = await User.find_one(User.userid == sended)
            if not user_obj:
                return False
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False

            act = cls(
                dino=dino_obj,
                activity_type="craft",
                start_time=int(time.time()),
                end_time=int(time.time()) + duration,
                user=user_obj,
                last_check=int(time.time()),
                alt_code=random_code()
            )
            try:
                await act.insert()
            except DuplicateKeyError:
                return False
            return True
        return False
