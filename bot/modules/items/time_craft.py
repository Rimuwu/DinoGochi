
from bot.models.dinosaur import DinoMood
from bot.models.items import ItemCraft

from time import time
from typing import Union

from bson import ObjectId
from bot.dbmanager import mongo_client

from bot.modules.data_format import random_code, transform

from bot.models.dinosaur import Dino
from bot.modules.notifications import dino_notification



async def add_time_craft(userid: int, time_craft: int, 
                         items: list[dict]):
    """ 
    Создаёт задержку для выдачи предметов
        items = [{
            'item': {
                item_id: str
                abilities: dict
            },
            count: int
        }]
    """

    tc = {
        'userid': userid,
        'alt_code': random_code(5) + str(userid),

        'time_start': int(time()),
        'time_end': int(time()) + time_craft,

        'items': items,
        'dino_id': None
    }

    craft_model = ItemCraft(**tc)
    await craft_model.insert()
    await ItemCraft.create_task(craft_model.id, craft_model.time_end)
    return tc

async def dino_craft(dino_id: ObjectId, craft_id: Union[ObjectId, str]):

    if isinstance(craft_id, ObjectId):
        craft_data = await ItemCraft.find_one(ItemCraft.id == craft_id)
    else:
        craft_data = await ItemCraft.find_one(ItemCraft.alt_code == craft_id)
    if craft_data:
        craft_dict = craft_data.dict()

        # Понижение времени в зависимости от ловкости
        dexterity = await Dino.check_skill(dino_id, 'dexterity')
        skip_percent = transform(dexterity, 20, 50)

        res = await DinoMood.check_inspiration(dino_id, 'craft')
        if res: 
            skip_percent *= 2
            await DinoMood.inspiration_end(dino_id, 'craft')

        minus_time = 0

        if skip_percent > 0:
            time_now = craft_dict['time_end'] - int(time())
            minus_time = (time_now // 100) * skip_percent

        craft_data.dino = await Dino.find_one(Dino.id == dino_id)
        craft_data.time_end -= minus_time
        await craft_data.save()
        await ItemCraft.create_task(craft_data.id, craft_data.time_end)
        return True, skip_percent

    else:
        return False, 0

async def stop_craft(craft_id: Union[ObjectId, str]):
    """ Завершение крафта до его окончания
    """

    if isinstance(craft_id, ObjectId):
        craft_data = await ItemCraft.find_one(ItemCraft.id == craft_id)
    else:
        craft_data = await ItemCraft.find_one(ItemCraft.alt_code == craft_id)

    if craft_data:
        if craft_data.dino:
            dino_id = craft_data.dino.ref.id if hasattr(craft_data.dino, 'ref') else craft_data.dino.id
            from bot.models.activity.base import Activity
            act = await Activity.find_one(
                Activity.dino.id == dino_id, Activity.activity_type == 'craft')
            if act:
                await act.delete()
            await dino_notification(dino_id, 'craft_end')
        await craft_data.delete()
        await ItemCraft.cancel_task(craft_data.id)