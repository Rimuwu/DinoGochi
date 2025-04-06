
from random import choice, randint, random
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.data_format import transform
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.dinosaur.mood import check_inspiration
from bot.modules.dinosaur.skills import check_skill
from bot.modules.dinosaur.works import end_work
from bot.modules.items.item import get_items_names
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang, t
from bot.modules.notifications import dino_notification
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
         'last_check': {'$lte': int(time()) - 600}
         }
    )

    for work in res_list:
        save, insp = True, False
        dp_chance = 0

        work_percent = ((int(time()) - work['start_time']) / (work['end_time'] - work['start_time'])) * 100 # Процент времени работы

        if work_percent <= 10:
            main_chance = random() <= 0.2
        elif work_percent <= 50:
            main_chance = random() <= 0.5
        elif work_percent <= 80:
            main_chance = random() <= 0.6
        else:
            main_chance = random() <= 0.7

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

        # Увеличивает шанс дропа предмета, если хар-ка соответствует
        # типу работы
        elif work['activity_type'] == 'sawmill':
            # ловкость (dexterity)
            dexterity = await check_skill(work['dino_id'], 'dexterity')
            dp_chance = randint(0, transform(dexterity, 20, 50) + 50) > 60

        elif work['activity_type'] == 'bank':
            # харизма (charisma)
            charisma = await check_skill(work['dino_id'], 'charisma')
            dp_chance = randint(0, transform(charisma, 20, 50) + 50) > 60

        elif work['activity_type'] == 'mine':
            # сила (power)
            power = await check_skill(work['dino_id'], 'power')
            dp_chance = randint(0, transform(power, 20, 50) + 50) > 60

        insp = await check_inspiration(work['dino_id'], work['activity_type'])

        if save and (main_chance or dp_chance):
            # Добавляем прдеметы / монеты
            if 'coins' in work:
                if work['coins'] < work['max_coins']:

                    if insp: coins = randint(100, 800)
                    else: coins = randint(100, 400)

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
                    else:
                        if not insp: count = randint(1, 2)
                        else: count = randint(1, 4)

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