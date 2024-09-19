from random import randint, random, choices, choice

from bot.config import conf, mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.data_format import transform
from bot.modules.items.accessory import check_accessory
from bot.modules.dinosaur.dinosaur import Dino, end_collecting, mutate_dino_stat
from bot.modules.items.item import counts_items
from bot.modules.localization import  get_lang
from bot.modules.dinosaur.mood import check_inspiration
from bot.modules.quests import quest_process
from bot.modules.user.user import experience_enhancement
from bot.taskmanager import add_task
from bot.modules.managment.events import get_event


from bot.modules.overwriting.DataCalsses import DBconstructor
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

REPEAT_MINUTS = 2
ENERGY_DOWN = 0.1 * REPEAT_MINUTS
LVL_CHANCE = 0.125 * REPEAT_MINUTS

async def stop_collect(coll_data):
    try:
        chat_user = await bot.get_chat_member(coll_data['sended'], coll_data['sended'])
        lang = await get_lang(chat_user.user.id)
    except: lang = 'en'
    
    items_list = []
    for key, count in coll_data['items'].items():
        items_list += [key] * count
    items_names = counts_items(items_list, lang)

    await end_collecting(coll_data['dino_id'], 
                                 coll_data['items'], coll_data['sended'], 
                                 items_names)

    await quest_process(coll_data['sended'], coll_data['collecting_type'], coll_data['now_count'])

async def collecting_process():
    data = await long_activity.find({'activity_type': 'collecting'}, comment='collecting_process_data')

    for coll_data in data:
        coll_type = coll_data["collecting_type"]
        if coll_data['now_count'] >= coll_data['max_count']:
            await stop_collect(coll_data)
        else:
            dino = await Dino().create(coll_data['dino_id'])
            rare_list = [50, 25, 15, 9, 1]

            # Понижение энергии
            if random() <= ENERGY_DOWN:
                if dino: await mutate_dino_stat(dino.__dict__, 'energy', -1)

            # Расчёт шанса
            res = await check_inspiration(coll_data['dino_id'], 'collecting')
            if res: chance = 0.9
            else: chance = 0.45

            if await check_accessory(dino, 'tooling'): chance += 0.25

            # Выдача опыта
            if random() <= LVL_CHANCE:
                if await check_inspiration(dino._id, 'exp_boost'):
                    await experience_enhancement(coll_data['sended'], 
                                             randint(1, 6))
                else:
                    await experience_enhancement(coll_data['sended'], 
                                             randint(1, 3))

            if random() + transform(dino.stats['charisma'], 20, 0.3) >= 90:
                await experience_enhancement(coll_data['sended'], randint(1, 5))

            # Выдача еды
            if random() <= chance:
                await check_accessory(dino, 'tooling', True)

                # Повышение шанса редкости
                if coll_type == 'fishing' and \
                    await check_accessory(dino, 'fishing-rod', True):
                        # Аксессуар удочка задействован
                        rare_list[0] -= 10
                        rare_list[1] -= 7

                        rare_list[2] += 10
                        rare_list[3] += 5
                        rare_list[4] += 2

                elif coll_type == 'hunt' and \
                    await check_accessory(dino, 'net', True):
                        # Аксессуар сеть задействован
                        rare_list[0] -= 10
                        rare_list[1] -= 7

                        rare_list[2] += 10
                        rare_list[3] += 5
                        rare_list[4] += 2

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
                rare_list[0] -= transform(char, 20, 25)
                rare_list[1] -= transform(char, 20, 12)

                rare_list[2] += transform(char, 20, 22)
                rare_list[3] += transform(char, 20, 13)
                rare_list[4] += transform(char, 20, 2)

                items = GAME_SETTINGS['collecting_items'][coll_type]
                event = await get_event(f'add_{coll_type}')
                count = randint(1, 3)

                if coll_data['now_count'] + count > coll_data['max_count']:
                    count = coll_data['max_count'] - coll_data['now_count']

                for _ in range(count):
                    rar = choices(list(items.keys()), rare_list)[0]
                    item = choice(items[rar])

                    if coll_type == 'collecting' and \
                       random() <= 0.7 and \
                            await check_accessory(dino, 'torch', True):
                                # 0.7 выдать редкий предмет
                                item = 'gourmet_herbs'

                    elif event != {} and random() <= 0.2:
                            # 0.2 Шанс выдать предмет из ивента
                            item = choice(event['data']['items'])

                    if item in coll_data['items']:
                        coll_data['items'][item] += 1
                    else: coll_data['items'][item] = 1

                await long_activity.update_one({'_id': coll_data['_id']}, 
                                                 {'$set': {'items': coll_data['items'] },'$inc': {'now_count': count}}, comment='collecting_task_1')

                if coll_data['now_count'] + count == coll_data['max_count']:
                    await stop_collect(coll_data)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(collecting_process, REPEAT_MINUTS * 60.0, 1.0)