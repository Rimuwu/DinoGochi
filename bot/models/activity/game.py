from bson.objectid import ObjectId
import time
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity

class GameActivity(Activity):
    game_percent: float = 1.0

    @classmethod
    async def start(cls, dino_id: ObjectId, duration: int = 1800, percent: float = 1.0) -> bool:
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            {'dino_id': {'$in': [dino_oid, str(dino_oid)]}},
            with_children=True
        )
        if not existing:
            act = cls(
                dino_id=str(dino_id),
                activity_type="game",
                start_time=int(time.time()),
                end_time=int(time.time()) + duration,
                game_percent=percent
            )
            try:
                await act.insert()
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, send_notif: bool = True):
        from bot.modules.notifications import dino_notification
        await cls.find(cls.dino_id == ObjectId(dino_id)).delete()
        if send_notif:
            await dino_notification(dino_id, 'game_end')
