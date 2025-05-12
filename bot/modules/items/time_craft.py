
from time import time
from typing import Union

from bson import ObjectId
from bot.dbmanager import mongo_client

from bot.modules.data_format import random_code, transform

from bot.modules.dinosaur.mood import check_inspiration, inspiration_end
from bot.modules.dinosaur.skills import check_skill
from bot.modules.notifications import dino_notification
from bot.modules.overwriting.DataCalsses import DBconstructor

item_craft = DBconstructor(mongo_client.items.item_craft)

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

    await item_craft.insert_one(tc)
    return tc

async def dino_craft(dino_id: ObjectId, craft_id: Union[ObjectId, str]):

    if isinstance(craft_id, ObjectId):
        craft_data = await item_craft.find_one({'_id': craft_id})
    else:
        craft_data = await item_craft.find_one({'alt_code': craft_id})
    if craft_data:

        # Понижение времени в зависимости от ловкости
        dexterity = await check_skill(dino_id, 'dexterity')
        skip_percent = transform(dexterity, 20, 50)

        res = await check_inspiration(dino_id, 'craft')
        if res: 
            skip_percent *= 2
            await inspiration_end(dino_id, 'craft')

        minus_time = 0

        if skip_percent > 0:
            time_now = craft_data['time_end'] - int(time())
            minus_time = (time_now // 100) * skip_percent

        await item_craft.update_one(
            {'_id': craft_data['_id']},
            {'$set': {
                'dino_id': dino_id
            },
             '$inc': {
                 'time_end': -minus_time
             }}
            )
        return True, skip_percent

    else:
        return False, 0

async def stop_craft(craft_id: Union[ObjectId, str]):
    """ Завершение крафта до его окончания
    """

    if isinstance(craft_id, ObjectId):
        craft_data = await item_craft.find_one({'_id': craft_id})
    else:
        craft_data = await item_craft.find_one({'alt_code': craft_id})

    if craft_data:
        if craft_data['dino_id']:

            await dino_notification(craft_data['dino_id'], 'craft_end')
        await item_craft.delete_one({'_id': craft_data['_id']})