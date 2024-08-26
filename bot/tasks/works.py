
from random import choice, randint, uniform
from time import time

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.data_format import transform
from bot.modules.dinosaur.dino_status import end_skill_activity
from bot.modules.dinosaur.dinosaur import Dino, mutate_dino_stat
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.mood import add_mood
from bot.modules.dinosaur.skills import add_skill_point, check_skill
from bot.modules.dinosaur.works import end_work
from bot.modules.items.item import get_items_names
from bot.modules.items.item_tools import use_item
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang, t
from bot.modules.notifications import dino_notification
from bot.modules.user.user import get_inventory_from_i
from bot.taskmanager import add_task

from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

data = {
    'bank': 'recipe',
    'mine': 'ore',
    'sawmill': 'wood'
}

async def work():
    res_list = await long_activity.find(
        {'activity_type': {'$in': ['bank', 'mine', 'sawmill']},
         'last_check': {'$lte': int(time()) - 0}
         }
    )

    for work in res_list:
        save = True

        dp_chance = 0
        if work['activity_type'] == 'sawmill':
            dexterity = await check_skill(work['dino_id'], 'dexterity')
            dp_chance = randint(0, transform(dexterity, 20, 50) + 50) > 60

        elif work['activity_type'] == 'bank':
            charisma = await check_skill(work['dino_id'], 'charisma')
            dp_chance = randint(0, transform(charisma, 20, 50) + 50) > 60

        elif work['activity_type'] == 'mine':
            power = await check_skill(work['dino_id'], 'power')
            dp_chance = randint(0, transform(power, 20, 50) + 50) > 60

        if int(time()) >= work['end_time']:
            save = False
            dino = await Dino().create(work['dino_id'])
            lang = await get_lang(work['sended'])

            if 'coins' in work:
                text = t('works.stop.coins', lang, coins=work['coins'])

            elif 'items' in work:
                text = t('works.stop.items', lang, items=get_items_names(list(work['items'].values()), lang))

            await end_work(dino._id)
            await dino_notification(dino._id, 
                                    f'{work["activity_type"]}_end', 
                                    results=text
                                    )

        elif save and (randint(0, 1) or dp_chance):
            # Добавляем прдеметы / монеты
            if 'coins' in work:
                if work['coins'] < work['max_coins']:
                    coins += randint(100, 400)
                    if coins + work['coins'] > work['max_coins']:
                        min_coins = coins + work['coins'] - work['max_coins']
                        coins -= min_coins
                    await long_activity.update_one({'_id': work['_id']}, {
                        '$inc': {
                            'coins': coins
                        }
                    })
            else:
                count_items = 0
                for key, item in work['items'].items(): count_items += item['count']

                if count_items < work['max_items']:
                    if work['max_items'] - count_items == 1:
                        count = 1
                    else: count = randint(1, 2)

                    items_group_ids = get_group(data[work["activity_type"]])
                    random_item = choice(items_group_ids)

                    if random_item not in work['items']:
                        work['items'][random_item] = {
                            'items_data': {'item_id': random_item},
                            'count': count
                        }
                    else:
                        work['items'][random_item]['count'] += count

                    await long_activity.update_one({'_id': work['_id']}, {
                        '$set': {
                            'items': work['items']
                        }
                    })
        elif save:
            # Отбираем прдеметы / монеты
            if 'coins' in work:
                if work['coins'] != 0:
                    coins = randint(-400, -100)
                    if coins + work['coins'] <= 0:
                        coins = -work['coins']

                    await long_activity.update_one({'_id': work['_id']}, {
                        '$inc': {
                            'coins': coins
                        }
                    })
            
            else:
                count_items = 0
                for key, item in work['items'].items(): count_items += item['count']

                if count_items != 0:
                    count = randint(1, 2)
                    random_item = choice(list(work['items'].keys()))

                    if count >= work['items'][random_item]['count']:
                        del work['items'][random_item]
                    else:
                        work['items'][random_item]['count'] -= count

                    await long_activity.update_one({'_id': work['_id']}, {
                        '$set': {
                            'items': work['items']
                        }
                    })

        if save:
            await long_activity.update_one({'_id': work['_id']}, {
                '$set': {
                    'last_check': int(time())
                    }
            })


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(work, 300.0, 10.0)