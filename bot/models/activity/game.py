from bson.objectid import ObjectId
import time
from bot.models.activity.base import Activity

class GameActivity(Activity):
    game_percent: float = 1.0

    @classmethod
    async def start(cls, dino_id: ObjectId, duration: int = 1800, percent: float = 1.0) -> bool:
        existing = await cls.find_one(cls.dino_id == str(dino_id))
        if not existing:
            act = cls(
                dino_id=str(dino_id),
                activity_type="game",
                start_time=int(time.time()),
                end_time=int(time.time()) + duration,
                game_percent=percent
            )
            await act.insert()
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, send_notif: bool = True):
        from bot.modules.notifications import dino_notification
        await cls.find(cls.dino_id == str(dino_id)).delete()
        if send_notif:
            await dino_notification(dino_id, 'game_end')
