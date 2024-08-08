
from time import time
from bot.config import mongo_client

from bot.modules.overwriting.DataCalsses import DBconstructor
item_craft = DBconstructor(mongo_client.items.item_craft)

async def add_time_craft(userid: int, time_craft: int, 
                         items: list[dict]):
    """ Создаёт задержку для выдачи предметов
    """

    tc = {
        'userid': userid,
        'time': time() + time_craft,
        'items': items
    }

    await item_craft.insert_one(tc)

async def send_notif():
    ...