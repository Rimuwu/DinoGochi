from datetime import datetime, timezone
from random import choice, randint, choices
from time import time

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import AddItemToUser, counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.notifications import dino_notification, user_notification
from bot.modules.user.user import experience_enhancement
from bot.taskmanager import add_task
from bot.modules.items.item import get_items_names

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
item_craft = DBconstructor(mongo_client.items.item_craft)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

async def check_items():

    data = await item_craft.find(
        {'time_end': {'$lte': int(time())}}, comment='check_craft_items')

    for craft in data:
        userid = craft['userid']
        lang = await get_lang(userid)
        add_way = 'standart'

        if craft['dino_id']:
            # Проверяем, если дино, смотрим на его навыки и рандомим 
            # Возожность добавления +1 к крафту
            add_way = 'bonus'
            dino = await Dino().create(craft['dino_id'])
            stat = dino.stats['intelligence']
            # Формула отвечает на вопрос - создать ли ещё 1 предмет
            # Главное условие - 20 уровень навыка = 60% успеха
            suc = randint(0, 1) < (0.6 - max(0, (20 - stat) * 0.03))

            if suc:
                r_item = choice(craft['items'])
                r_item['count'] += 1

            # Завершение активности динозавра
            await long_activity.delete_one({
                'dino_id': craft['dino_id'],
                'activity_type': 'craft'
            })
            await dino_notification(craft['dino_id'], 'craft_end')
            await experience_enhancement(userid, randint(1, 15))

        for item in craft['items']:
            await AddItemToUser(userid, item['item']['item_id'], 
                                item['count'], item['item']['abilities'])

        await item_craft.delete_one({'_id': craft['_id']})
        await user_notification(userid, 'item_crafted', lang,
                                items=get_items_names(craft['items'], lang),
                                add_way=add_way)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(check_items, 10.0, 1.0)