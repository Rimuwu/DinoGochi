from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import DinoMood, Dino
from bot.models.activity import Activity, WorkActivity

from random import choice, randint, random
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.data_format import transform
from bot.models.dinosaur import Dino
from bot.models.dinosaur import Dino
from bot.modules.items.item import get_items_names
from bot.modules.items.item_tools import rare_random
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang, t
from bot.modules.notifications import dino_notification
from bot.taskmanager import add_task
from bot.const import GAME_SETTINGS

dinosaurs = LazyCollection(Dino)
long_activity = LazyCollection(Activity)

data = {
    'bank': ['recipe', 'add_bank_items'],
    'mine': ['ore'],
    'sawmill': ['wood']
}

data_add_chance = {
    'bank': {},
    'mine': {
        'bone': 10
    },
    'sawmill': {
        'twigs_tree': 15
    }
}

async def work_task():
    res_list = await long_activity.find(
        {'activity_type': {'$in': ['bank', 'mine', 'sawmill']},
         'last_check': {'$lte': int(time()) - 1}
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
            lang = await get_lang(work['send'])

            if work.get('coins') is not None:
                text = t('works.stop.coins', lang, coins=work['coins'])

            elif work.get('items') is not None:
                text = t('works.stop.items', lang, items=get_items_names(list(work['items'].values()), lang))

            await WorkActivity.end_work(work['dino_id'])
            await dino_notification(work['dino_id'], 
                                    f'{work["activity_type"]}_end', 
                                    results=text
                                    )

        # Увеличивает шанс дропа предмета, если хар-ка соответствует
        # типу работы
        elif work['activity_type'] == 'sawmill':
            # ловкость (dexterity)
            dexterity = await Dino.check_skill(work['dino_id'], 'dexterity')
            dp_chance = randint(0, transform(dexterity, 20, 50) + 50) > 60

        elif work['activity_type'] == 'bank':
            # харизма (charisma)
            charisma = await Dino.check_skill(work['dino_id'], 'charisma')
            dp_chance = randint(0, transform(charisma, 20, 50) + 50) > 60

        elif work['activity_type'] == 'mine':
            # сила (power)
            power = await Dino.check_skill(work['dino_id'], 'power')
            dp_chance = randint(0, transform(power, 20, 50) + 50) > 60

        insp = await DinoMood.check_inspiration(work['dino_id'], work['activity_type'])

        if save and (main_chance or dp_chance):
            # Добавляем прдеметы / монеты
            if work.get('coins') is not None:
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

                    items_group_ids = []
                    for group in data[work["activity_type"]]:
                        items_group_ids += get_group(group)

                    bank_cfg = GAME_SETTINGS.get('bank', {})
                    rarity_chances = bank_cfg.get('rarity_chances') or None
                    special_chances = bank_cfg.get('special_chances') or None

                    random_items = rare_random(
                        items_group_ids, count,
                        data_add_chance[work["activity_type"]],
                        special_chances=special_chances,
                        rarity_chances=rarity_chances
                    ) if work["activity_type"] == 'bank' else rare_random(
                        items_group_ids, count, data_add_chance[work["activity_type"]]
                    )

                    for random_item in random_items:
                        if random_item in work['items']:
                            work['items'][random_item]['count'] += 1
                        else:
                            work['items'][random_item] = {
                                'items_data': {'item_id': random_item},
                                'count': 1
                            }

                    await long_activity.update_one({'_id': work['_id']}, {
                        '$set': {
                            'items': work['items']
                        }
                    })
        elif save:
            # Отбираем прдеметы / монеты
            if work.get('coins') is not None:
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
        add_task(work_task, 300.0, 10.0)