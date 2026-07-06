from typing import Dict, Optional
from beanie import Link
from bson.objectid import ObjectId
import time
from pydantic import Field
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.user import User
from bot.models.dinosaur import Dino

class CollectingActivity(Activity):
    user: Optional[Link[User]] = None
    collecting_type: str = "collecting"
    max_count: int = 0
    now_count: int = 0
    items: Dict[str, int] = Field(default_factory=dict)

    @classmethod
    async def start(cls, dino_id: ObjectId, owner_id: int, coll_type: str, max_count: int) -> bool:
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            user_obj = await User.find_one(User.userid == owner_id)
            if not user_obj:
                return False
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False

            act = cls(
                dino=dino_obj,
                activity_type="collecting",
                start_time=int(time.time()),
                end_time=int(time.time()) + 86400 * 365,
                user=user_obj,
                collecting_type=coll_type,
                max_count=max_count,
                now_count=0,
                items={}
            )
            try:
                await act.insert()
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, items: Dict[str, int], recipient: int, items_names: str, send_notif: bool = True):
        from bot.modules.items.item import AddItemToUser
        from bot.modules.notifications import dino_notification

        await cls.find(cls.dino.id == ObjectId(dino_id)).delete()
        for key_id, count in items.items():
            await AddItemToUser(recipient, key_id, count)
        if send_notif:
            await dino_notification(dino_id, 'end_collecting', items_names=items_names)
