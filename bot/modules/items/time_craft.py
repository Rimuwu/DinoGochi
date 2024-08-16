
from time import time
from bot.config import mongo_client

from bot.modules.data_format import random_code
from bot.modules.overwriting.DataCalsses import DBconstructor
item_craft = DBconstructor(mongo_client.items.item_craft)

async def add_time_craft(userid: int, time_craft: int, 
                         items: list[dict]):
    """ Создаёт задержку для выдачи предметов
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

        'dino_id': None,
        'dino_stats': {}
    }

    await item_craft.insert_one(tc)
    return tc

async def send_notif():
    ...