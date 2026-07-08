from bot.models.user import User
from bot.models.items import ItemCraft
from bot.models.activity.base import Activity
from random import choice, randint, random
from time import time
from bson import ObjectId

from bot.config import conf
from bot.models.dinosaur import Dino
from bot.modules.items.item import AddItemToUser
from bot.modules.localization import get_lang
from bot.modules.notifications import dino_notification, user_notification
from bot.modules.items.item import get_items_names
from bot.modules.task_queue import task_handler

@task_handler("check_items")
async def check_items_task(data: dict):
    craft_id = data.get("craft_id")
    if craft_id:
        craft = await ItemCraft.find_one(ItemCraft.id == ObjectId(craft_id))
        if craft:
            user_obj = await User.find_one(
                User.userid == craft.userid) if craft.userid else None
            if not user_obj:
                return
            userid = craft.userid
            lang = await get_lang(userid)
            add_way = 'standart'

            if craft.dino:
                dino_id = craft.dino.ref.id if hasattr(craft.dino, 'ref') else craft.dino.id
                dino = await Dino().create(dino_id)
                if dino:
                    stat = dino.stats.get('intelligence', 0)
                    suc = transform(stat, 20, 0.4) + random() >= 0.8

                    if suc:
                        r_item = choice(craft.items)
                        r_item['count'] += 1
                        add_way = 'bonus'

                # Завершение активности динозавра
                act = await Activity.find_one(
                    Activity.dino.id == dino_id, Activity.activity_type == 'craft')
                if act:
                    await act.delete()
                await dino_notification(dino_id, 'craft_end')
                await user_obj.add_xp_lvl(randint(1, 15))

            for item in craft.items:
                abil = item['item'].get('abilities', {})
                await AddItemToUser(userid, item['item']['item_id'], 
                                    item['count'], abil)

            await craft.delete()
            await user_notification(userid, 'item_crafted', lang,
                                    items=get_items_names(craft.items, lang),
                                    add_way=add_way)

def transform(value: float, target: float, chance: float) -> float:
    # helper for formula
    if target == 0:
        return 0.0
    return (value / target) * chance