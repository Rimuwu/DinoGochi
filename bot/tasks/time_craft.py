from random import choice, randint, random
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.data_format import transform
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import AddItemToUser
from bot.modules.localization import get_lang
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
            dino = await Dino().create(craft['dino_id'])
            stat = dino.stats['intelligence']
            # Формула отвечает на вопрос - создать ли ещё 1 предмет
            # Главное условие - 20 уровень = 40% успеха
            suc =  transform(stat, 20, 0.4) + random() >= 0.8

            if suc:
                r_item = choice(craft['items'])
                r_item['count'] += 1
                add_way = 'bonus'

            # Завершение активности динозавра
            await long_activity.delete_one({
                'dino_id': craft['dino_id'],
                'activity_type': 'craft'
            })
            await dino_notification(craft['dino_id'], 'craft_end')
            await experience_enhancement(userid, randint(1, 15))

        for item in craft['items']:
            abil = item['item'].get('abilities', {})
            await AddItemToUser(userid, item['item']['item_id'], 
                                item['count'], abil)

        await item_craft.delete_one({'_id': craft['_id']})
        await user_notification(userid, 'item_crafted', lang,
                                items=get_items_names(craft['items'], lang),
                                add_way=add_way)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(check_items, 10.0, 1.0)