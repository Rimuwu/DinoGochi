from bson.objectid import ObjectId
import time
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.dinosaur import Dino

class GameActivity(Activity):
    game_percent: float = 1.0

    @classmethod
    async def start(cls, dino_id: ObjectId, duration: int = 1800, percent: float = 1.0) -> bool:
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False
            act = cls(
                dino=dino_obj,
                activity_type="game",
                start_time=int(time.time()),
                end_time=int(time.time()) + duration,
                game_percent=percent
            )
            try:
                await act.insert()
                await cls.create_task(dino_id, act.end_time)
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, send_notif: bool = True):
        from bot.modules.notifications import dino_notification
        await cls.find(cls.dino.id == ObjectId(dino_id)).delete()
        await cls.cancel_task(dino_id)
        if send_notif:
            await dino_notification(dino_id, 'game_end')

    @classmethod
    async def create_task(cls, dino_id: ObjectId, end_time: int):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task("game_end", {"dino_id": str(dino_id)}, run_at=end_time, resource_id=f"game:{dino_id}")

    @classmethod
    async def cancel_task(cls, dino_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"game:{dino_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        current_time = int(time.time())
        games = await cls.find().to_list()
        for act in games:
            dino_id = act.dino.ref.id
            res_id = f"game:{dino_id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, act.end_time)
                await cls.create_task(dino_id, run_at)
