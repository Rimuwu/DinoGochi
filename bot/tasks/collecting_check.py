from random import randint, random

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.data_format import transform
# from bot.modules.items.accessory import check_accessory
from bot.modules.dinosaur.dino_status import end_collecting
from bot.modules.dinosaur.dinosaur import Dino, mutate_dino_stat
from bot.modules.items.item import counts_items
from bot.modules.items.item_dataformat import rare_random
from bot.modules.items.items_groups import get_group
from bot.modules.localization import  get_lang
from bot.modules.dinosaur.mood import check_inspiration
from bot.modules.quests import quest_process
from bot.modules.user.user import experience_enhancement
from bot.taskmanager import add_task
from bot.modules.managment.events import get_event
from bot.modules.logs import log


from bot.modules.overwriting.DataCalsses import DBconstructor
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

REPEAT_MINUTS = 2
ENERGY_DOWN = 0.1 * REPEAT_MINUTS
LVL_CHANCE = 0.125 * REPEAT_MINUTS

advanced_rank_for_items = {
    "mystical": ["ink", "skin", "fish_oil", "twigs_tree", "feather", "wool"],
}


async def stop_collect(coll_data):
    lang = await get_lang(coll_data['sended'])

    items_list = []
    for key, count in coll_data['items'].items():
        items_list += [key] * count
    items_names = counts_items(items_list, lang)

    await end_collecting(coll_data['dino_id'], 
                                 coll_data['items'], coll_data['sended'], 
                                 items_names)

    await quest_process(coll_data['sended'], coll_data['collecting_type'], coll_data['now_count'])

async def collecting_work(coll_data: dict):
    coll_type = coll_data["collecting_type"]

    if coll_data['now_count'] >= coll_data['max_count']:
        await stop_collect(coll_data)
    else:
        dino = await Dino().create(coll_data['dino_id'])
        if not dino: return

        special_chance = {}
        chances_add = {'common': 0, 'uncommon': 0, 
                       'rare': 0, 'mystical': 0, 'legendary': 0}

        # Понижение энергии
        if random() <= ENERGY_DOWN:
            if dino: await mutate_dino_stat(dino.__dict__, 'energy', -1)

        # Расчёт шанса
        res = await check_inspiration(coll_data['dino_id'], 'collecting')
        if res: chance = 0.9
        else: chance = 0.45

        # if await check_accessory(dino, 'tooling'): chance += 0.25

        # Выдача опыта
        if random() <= LVL_CHANCE:
            if await check_inspiration(dino._id, 'exp_boost'):
                await experience_enhancement(coll_data['sended'], 
                                            randint(1, 6))
            else:
                await experience_enhancement(coll_data['sended'], 
                                            randint(1, 3))

        # Шанс на доп опыт при высокой харизме
        if random() + transform(dino.stats['charisma'], 20, 0.3) >= 90:
            await experience_enhancement(coll_data['sended'], randint(1, 5))

        # Выдача еды
        if random() <= chance:
            # await check_accessory(dino, 'tooling', True)

            # Повышение шанса редкости
            # if coll_type == 'fishing' and \
            #     await check_accessory(dino, 'fishing-rod', True):
            #         # Аксессуар удочка задействован
            #         chances_add['rare'] += 10
            #         chances_add['mystical'] += 5
            #         chances_add['legendary'] += 2

            # elif coll_type == 'hunt' and \
            #     await check_accessory(dino, 'net', True):
            #         # Аксессуар сеть задействован
            #         chances_add['rare'] += 10
            #         chances_add['mystical'] += 5
            #         chances_add['legendary'] += 2

            # # ==== Повышение шанса в зависимости от навыка === #
            if coll_type == 'collecting':
                char = dino.stats['intelligence']

            elif coll_type == 'fishing':
                char = dino.stats['dexterity']

            elif coll_type == 'hunt':
                char = dino.stats['power']

            elif coll_type == 'all':
                char = dino.stats['charisma']

            # Распределно по принципу distribute_number()
            chances_add['rare'] += transform(char, 20, 22)
            chances_add['mystical'] += transform(char, 20, 13)
            chances_add['legendary'] += transform(char, 20, 2)

            # Получение предметов по занятию
            items = {}
            if coll_type == 'all':
                items = []
                for i in ['collecting', 'hunt', 'fishing']:
                    items += get_group(f'{i}-activity')
                items += get_group('all-activity')
            else:
                items = get_group(f'{coll_type}-activity')

            # Установка количества предметов
            count = randint(1, 3)
            if coll_data['now_count'] + count > coll_data['max_count']:
                count = coll_data['max_count'] - coll_data['now_count']

            # Добавление в шанс предметов события
            event = await get_event(f'add_{coll_type}')
            if event: 
                items += event['data']['items']
                if 'special_chance' in event['data']:
                    special_chance.update(event['data']['special_chance'])

            # Добавление в шанс предметов из аксессуара
            # trc_flag = False
            # if coll_type == 'collecting' and await check_accessory(dino, 'torch'):
            #     # Шанс на изысканные травы равен 15% если есть факел
            #     # Иначе шанс от редкости
            #     special_chance['gourmet_herbs'] = 15
            #     trc_flag = True

            rand_items = rare_random(items, count, chances_add, 
                            special_chance, None, advanced_rank_for_items)

            for item in rand_items:

                # if trc_flag: await check_accessory(dino, 'torch', True)

                if item in coll_data['items']:
                    coll_data['items'][item] += 1
                else: coll_data['items'][item] = 1

            await long_activity.update_one({'_id': coll_data['_id']}, 
                                                {'$set': {'items': coll_data['items'] },'$inc': {'now_count': count}}, comment = 'collecting_task_1')

            if coll_data['now_count'] + count == coll_data['max_count']:
                await stop_collect(coll_data)

async def collecting_process():
    data = await long_activity.find({'activity_type': 'collecting'}, comment='collecting_process_data')

    for coll_data in data:

        try:
            await collecting_work(coll_data)
        except Exception as e:
            log(f'Ошибка в работе задачи: {e}', prefix='Error', lvl=4)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(collecting_process, REPEAT_MINUTS * 60.0, 1.0)