from bson.objectid import ObjectId
import time
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.dinosaur import Dino

class SleepActivity(Activity):
    sleep_type: str = "long"

    @classmethod
    async def start(cls, dino_id: ObjectId, s_type: str = 'long', duration: int = 1) -> bool:
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False
            end_time = int(time.time()) + duration if s_type == 'short' else int(time.time()) + 86400 * 365
            act = cls(
                dino=dino_obj,
                activity_type="sleep",
                start_time=int(time.time()),
                end_time=end_time,
                sleep_type=s_type
            )
            try:
                await act.insert()
                # Инвалидируем кеш статуса
                from bot.modules.dino_status_cache import invalidate_status_cache
                await invalidate_status_cache(dino_oid)
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, sec_time: int = 0, send_notif: bool = True):
        from bot.modules.notifications import dino_notification
        from bot.modules.dino_status_cache import invalidate_status_cache
        await cls.find(cls.dino.id == ObjectId(dino_id), cls.activity_type == 'sleep').delete()
        await invalidate_status_cache(dino_id)
        if send_notif:
            await dino_notification(dino_id, 'sleep_end', add_time_end=True, secs=sec_time)
