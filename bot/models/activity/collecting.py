from typing import Dict, Optional, List, Any
from bson.objectid import ObjectId
import time
from pydantic import Field
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.dinosaur import Dino

class CollectingActivity(Activity):
    userid: int = 0
    collecting_type: str = "collecting"
    max_count: int = 0
    now_count: int = 0
    items: Dict[str, int] = Field(default_factory=dict)
    pregenerated_ticks: List[Dict[str, Any]] = Field(default_factory=list)

    @classmethod
    async def start(cls, dino_id: ObjectId, owner_id: int, coll_type: str, max_count: int) -> bool:
        dino_oid = ObjectId(dino_id)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False

            start_time = int(time.time())
            
            # Import dynamically to avoid circular import issues
            from bot.tasks.collecting_check import presimulate_collecting
            ticks, end_time = await presimulate_collecting(dino_obj, owner_id, coll_type, max_count, start_time)

            act = cls(
                dino=dino_obj,
                activity_type="collecting",
                start_time=start_time,
                end_time=end_time,
                userid=owner_id,
                collecting_type=coll_type,
                max_count=max_count,
                now_count=0,
                items={},
                pregenerated_ticks=ticks
            )
            try:
                await act.insert()
                await cls.create_task(dino_id, end_time)
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId, items: Optional[Dict[str, int]] = None, recipient: Optional[int] = None, items_names: Optional[str] = None, send_notif: bool = True):
        from bot.modules.items.item import AddItemToUser
        from bot.modules.notifications import dino_notification
        from bot.models.items import Item
        from bot.models.user import User
        from bot.modules.quests import quest_process
        from bot.modules.localization import get_lang
        from bot.modules.items.item import counts_items

        activity = await cls.find_one(cls.dino.id == ObjectId(dino_id))
        if not activity:
            return

        current_time = int(time.time())
        # completed ticks
        completed_ticks = [t for t in activity.pregenerated_ticks if t["trigger_time"] <= current_time]
        
        # Calculate totals
        total_items = {}
        total_xp = 0
        total_energy_lost = 0
        all_downgrades = []
        now_count = 0
        
        for tick in completed_ticks:
            now_count = tick["count"]
            total_xp += tick.get("xp", 0)
            total_energy_lost += tick.get("energy_lost", 0)
            all_downgrades.extend(tick.get("downgrades", []))
            for it_id, cnt in tick.get("items", {}).items():
                total_items[it_id] = total_items.get(it_id, 0) + cnt

        # Delete activity first
        await activity.delete()
        await cls.cancel_task(dino_id)

        # Apply items
        for it_id, cnt in total_items.items():
            await AddItemToUser(activity.userid, it_id, cnt)

        # Apply xp
        if total_xp > 0:
            user_obj = await User.find_one(User.userid == activity.userid)
            if user_obj:
                await user_obj.add_xp_lvl(total_xp)

        # Apply energy loss
        if total_energy_lost > 0:
            dino = await Dino.find_one(Dino.id == ObjectId(dino_id))
            if dino:
                await Dino.mutate_stat(dino, 'energy', -total_energy_lost)

        # Apply downgrades
        for acc_type, item_id in all_downgrades:
            await Item.check_accessory(dino_id, item_id, downgrade=True)

        # Apply quest progress
        await quest_process(activity.userid, activity.collecting_type, now_count)

        # Notifications
        if send_notif:
            lang = await get_lang(activity.userid)
            items_list = []
            for it_id, cnt in total_items.items():
                items_list += [it_id] * cnt
            items_names = counts_items(items_list, lang)
            await dino_notification(dino_id, 'end_collecting', items_names=items_names)

    @classmethod
    async def create_task(cls, dino_id: ObjectId, end_time: int):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task("stop_collect", {"dino_id": str(dino_id)}, run_at=end_time, resource_id=f"collecting:{dino_id}")

    @classmethod
    async def cancel_task(cls, dino_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"collecting:{dino_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        current_time = int(time.time())
        collectings = await cls.find().to_list()
        for act in collectings:
            dino_id = act.dino.ref.id
            res_id = f"collecting:{dino_id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, act.end_time)
                await cls.create_task(dino_id, run_at)
