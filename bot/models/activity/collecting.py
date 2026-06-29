from typing import Dict
from bson.objectid import ObjectId
import time
from pydantic import Field
from bot.models.activity.base import Activity

class CollectingActivity(Activity):
    sended: int
    collecting_type: str = "collecting"
    max_count: int = 0
    now_count: int = 0
    items: Dict[str, int] = Field(default_factory=dict)

    @classmethod
    async def start(cls, dino_id: ObjectId, owner_id: int, coll_type: str, max_count: int) -> bool:
        existing = await cls.find_one(cls.dino_id == str(dino_id))
        if not existing:
            act = cls(
                dino_id=str(dino_id),
                activity_type="collecting",
                start_time=int(time.time()),
                end_time=int(time.time()) + 86400 * 365,
                sended=owner_id,
                collecting_type=coll_type,
                max_count=max_count,
                now_count=0,
                items={}
            )
            await act.insert()
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, items: Dict[str, int], recipient: int, items_names: str, send_notif: bool = True):
        from bot.modules.items.item import AddItemToUser
        from bot.modules.notifications import dino_notification
        
        await cls.find(cls.dino_id == str(dino_id)).delete()
        for key_id, count in items.items():
            await AddItemToUser(recipient, key_id, count)
        if send_notif:
            await dino_notification(dino_id, 'end_collecting', items_names=items_names)
