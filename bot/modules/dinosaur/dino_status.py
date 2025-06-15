from typing import Union
from bson.objectid import ObjectId
from bot.dbmanager import mongo_client

from bot.modules.data_format import deepcopy, random_code
from bot.modules.items.item import AddItemToUser
from bot.modules.logs import log
from bot.modules.notifications_utils import dino_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
from time import time

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

kindergarten = DBconstructor(mongo_client.dino_activity.kindergarten)
kd_activity = DBconstructor(mongo_client.dino_activity.kd_activity)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
item_craft = DBconstructor(mongo_client.items.item_craft)
users = DBconstructor(mongo_client.user.users)

async def check_status(dino_id: Union[ObjectId, dict]) -> str:

    if isinstance(dino_id, ObjectId):
        dino = await dinosaurs.find_one({'_id': dino_id}, 
                                    {'activity_type': 1}, comment='check_status_dino')
    elif isinstance(dino_id, dict):
        dino = dino_id
        dino_id = dino['_id']
    else: #Dino
        dino = dino_id.__dict__
        dino_id = dino['_id']

    if dino:

        activity = await long_activity.find_one({'dino_id': dino_id}, 
                {'_id': 1, 'activity_type': 1}, comment="check_all_status")
        if activity == None: status = 'pass'
        else:
            status: str = activity['activity_type']

        on_craft = await item_craft.find_one({'dino_id': dino_id}) != None

        in_kindergarten = await kindergarten.find_one({'dinoid': dino_id}, 
                                    comment='check_status_in_kindergarten')

        hysteria = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'breakdown', 'action': 'hysteria'}, comment='check_status_hysteria')
        unrestrained_play = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'breakdown', 'action': 'unrestrained_play'}, comment='check_status_unrestrained_play')

        status_checks = {
            'sleep': status == 'sleep',

            'unrestrained_play': bool(unrestrained_play),
            'game': status == 'game',

            'journey': status == 'journey',
            'collecting': status == 'collecting',
            'dungeon': status == 'dungeon',

            'kindergarten': bool(in_kindergarten),
            'hysteria': bool(hysteria),

            'farm': status == 'farm',
            'mine': status == 'mine',
            'bank': status == 'bank',
            'sawmill': status == 'sawmill',
            
            'gym': status == 'gym',
            'library': status == 'library',
            'park': status == 'park',
            'swimming_pool': status == 'swimming_pool',

            'craft': on_craft,
            'inactive': status == 'inactive'
        }

        for key, value in status_checks.items():
            if value: return key

    return 'pass'


skill_time = {
    "gym": [5400, 10800],
    "library": [1800, 7200],
    "swimming_pool": [5400, 7200],
    "park": [1200, 7200],
}

def get_skill_time(skill: str) -> list[int]: return deepcopy(skill_time[skill]) # type: ignore

async def start_skill_activity(dino_id: ObjectId, activity: str, up: str, down: str, 
                               up_unit: list[float], down_unit: list[float],
                               sended: int):
    """ up_unit | down_unit - list[float, float] минимум и максимум число которое может быть выдано
        - за 10 минут
    """

    assert activity in ['gym', 'library', 'swimming_pool', 'park'], f'{activity} не подходит для старта'

    assert up in ['charisma', 'intelligence', 'dexterity', 'power'], f'{up} не соответствует скилам'

    assert down in ['charisma', 'intelligence', 'dexterity', 'power'], f'{down} не соответствует скилам'

    if not await long_activity.find_one({'dino_id': dino_id,
            'activity_type': activity}, comment=f'start_{activity}_check'):
        skl_time = get_skill_time(activity)
        act = {
            'send': sended, # Id того, кто отправил дино, чтобы воровать из его инвентаря энергетики
            'use_energy': False,

            'dino_id': dino_id,

            'up_skill': up, 'down_skill': down,
            'up_unit': up_unit, 'down_unit': down_unit,

            'last_check': int(time()), 'start_time': int(time()),

            'activity_type': activity,
            'alt_code': random_code(),

            'up': 0.0, # Считаем, сколько было повышено и вычитаем 50% при отмене заранее.
            'min_time': skl_time[0], 'max_time': skl_time[1],
            'ahtung_lvl': 0
            # min_time - если меньше, то штраф к хррактеристикам
            # max_time - Если больше на 20% - повышение кд на 5 часов (ahtung_lvl = 1)
            #          - Если больше на 40% - штраф (ahtung_lvl = 2)
        }
        await long_activity.insert_one(act, comment=f'start_{activity}')
    return act

async def end_skill_activity(dino_id: ObjectId):

    res = await long_activity.find_one({'dino_id': dino_id}, comment=f'end_skill_activity')

    if res and res['activity_type'] in ['gym', 'library', 'swimming_pool', 'park']:
        await long_activity.delete_one({'_id': res['_id']}, comment='end_skill_act_del')

        return 1
    else: return 0


async def start_game(dino_baseid: ObjectId, duration: int=1800, 
               percent: float=1):
    """Запуск активности "игра". 
       + Изменение статуса динозавра 
    """

    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'game'}, comment='start_game'):
        game = {
            'dino_id': dino_baseid,
            'game_start': int(time()),
            'game_end': int(time()) + duration,
            'game_percent': percent,
            'activity_type': 'game'
        }
        result = await long_activity.insert_one(game, comment='game_task_result')

    return result

async def end_game(dino_id: ObjectId, send_notif: bool=True):
    """Заканчивает игру и отсылает уведомление.
    """
    await long_activity.delete_many({'dino_id': dino_id}, comment='end_game') 

    if send_notif: await dino_notification(dino_id, 'game_end')


async def start_sleep(dino_baseid: ObjectId, s_type: str='long', 
                duration: int=1):
    """Запуск активности "сон". 
       + Изменение статуса динозавра 
    """

    assert s_type in ['long', 'short'], f'Неподходящий аргумент {s_type}'

    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'sleep'}, comment='start_sleep_1'):
        sleep = {
            'dino_id': dino_baseid,
            'sleep_start': int(time()),
            'sleep_type': s_type,
            'activity_type': 'sleep'
        }
        if s_type == 'short':
            sleep['sleep_end'] = int(time()) + duration

        result = await long_activity.insert_one(sleep, comment='start_sleep_2')
    return result

async def end_sleep(dino_id: ObjectId,
                    sec_time: int=0, send_notif: bool=True):
    """Заканчивает сон и отсылает уведомление.
       sec_time - время в секундах, сколько спал дино.
    """
    await long_activity.delete_many({'dino_id': dino_id}, comment='end_sleep_1')
    if send_notif:
        await dino_notification(dino_id, 'sleep_end', 
                            add_time_end=True,
                            secs=sec_time)


async def start_journey(dino_baseid: ObjectId, owner_id: int, 
                  duration: int=1800, location: str = 'forest'):
    """Запуск активности "путешествие". 
       + Изменение статуса динозавра 
    """
    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'journey'}, comment='start_journey'):
        game = {
            'sended': owner_id, # Так как у нас может быть несколько владельцев
            'dino_id': dino_baseid,
            'journey_start': int(time()),
            'journey_end': int(time()) + duration,

            'location': location,
            'journey_log': [], 'items': [],
            'coins': 0,

            'activity_type': 'journey'
        }
        result = await long_activity.insert_one(game, comment='start_journey_result')

    return result

async def end_journey(dino_id: ObjectId):
    data = await long_activity.find_one({'dino_id': dino_id,
            'activity_type': 'journey'}, comment='end_journey_data')
    if data:
        for i in data['items']: 
            await AddItemToUser(data['sended'], i)
        await users.update_one({'userid': data['sended']}, {'$inc': {'coins': data['coins']}}, comment='end_journey')
        log(f"Edit coins: user: {data['sended']} col: {data['coins']}", 0, "take_coins")

        await long_activity.delete_many({'dino_id': dino_id}, comment='end_journey')

async def start_collecting(dino_baseid: ObjectId, owner_id: int, coll_type: str, max_count: int):
    """Запуск активности "сбор пищи". 
       + Изменение статуса динозавра 
    """

    assert coll_type in ['collecting', 'hunt', 'fishing', 'all'], f'Неподходящий аргумент {coll_type}'

    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'collecting'}, comment='start_collecting'):
        collecting = {
            'sended': owner_id, # Так как у нас может быть несколько владельцев
            'dino_id': dino_baseid,
            'collecting_type': coll_type,
            'max_count': max_count,
            'now_count': 0,
            'items': {},

            'activity_type': 'collecting'
        }
        result = await long_activity.insert_one(collecting, comment='start_collecting_result')
    return result

async def end_collecting(dino_id: ObjectId, items: dict, recipient: int,
                         items_names: str,
                         send_notif: bool = True):
    """Конец сбора пищи,
       items_name - сгенерированное сообщение для уведолмения
       items - словарь типа {'id': count: int} с предметами для добавления
       recipient - тот кто получит собранные предметы
    """
    await long_activity.delete_many({'dino_id': dino_id}, comment='end_collecting_1')

    for key_id, count in items.items():
        await AddItemToUser(recipient, key_id, count)

    if send_notif:
        await dino_notification(dino_id, 'end_collecting', items_names=items_names)


async def set_status(dino_id: ObjectId, new_status: str, now_status: str = ''):
    """ НЕ вводит в состояние, лишь отменяет старое. Делает это грубо.
    """

    assert new_status in ['sleep', 'game', 'journey', 'collecting', 'dungeon', 'kindergarten', 'hysteria', 'farm', 'mine', 'bank', 'sawmill', 'gym', 'library', 'park', 'swimming_pool', 'craft', 'unrestrained_play', 'pass'], f'Состояние {new_status} не найдено!'
    
    # hysteria farm unrestrained_play

    if not now_status:
        now_status = await check_status(dino_id)

    if now_status == 'sleep':
        sleeper = await long_activity.find_one({'dino_id': dino_id,
            'activity_type': 'sleep'}, comment='set_status_sleeper')
        if sleeper:
            sleep_time = int(time()) - sleeper['sleep_start']
            await end_sleep(dino_id, sleeper['_id'], sleep_time)

    elif now_status == 'game': await end_game(dino_id)

    elif now_status == 'journey': await end_journey(dino_id)

    elif now_status == 'collecting':
        data = await long_activity.find_one({'dino_id': dino_id,
            'activity_type': 'collecting'}, comment='set_status_data')
        if data:
            items_list = []
            for key, count in data['items'].items(): 
                items_list += [key] * count

            await end_collecting(dino_id, data['items'], 
                                        data['sended'], '', False)

    elif now_status == 'kindergarten':
        data = await kindergarten.find_one({'dinoid': dino_id}, comment='set_status_data')
        if data: await kindergarten.delete_one({'_id': data['_id']}, comment='set_status_1')

    elif now_status == 'craft':

        res = await item_craft.find_one({'dino_id': dino_id})
        if res:
            await dino_notification(dino_id, 'craft_end')
            await item_craft.delete_one({'_id': res['_id']})

        await long_activity.delete_one({
            'dino_id': dino_id,
            'activity_type': 'craft'
        })

    elif now_status in ['gym', 'library', 'park', 'swimming_pool']:
        res = await long_activity.find_one(
        {'dino_id': dino_id})

        if res: 
            traning_time = int(time()) - res['start_time']
            way = ''

            if traning_time < res['min_time']:
                unit_percent = res['up_unit'] / 2

                skill =  res['up_skill']
                await dinosaurs.update_one({'_id': dino_id}, 
                                            {'$inc': {f'stats.{skill}': 
                                                round(-unit_percent)}
                                             })
                way = '_negative'

            await dino_notification(dino_id, res['activity_type'] + '_end' + way)
            await end_skill_activity(dino_id)

    elif now_status in ['bank', 'mine', 'sawmill']:
        res = await long_activity.find_one(
            {'activity_type': {'$in': ['bank', 'mine', 'sawmill']}, 
             'dino_id': dino_id}
        )

        if res:
            await long_activity.delete_one({'_id': res['_id']})
            await dino_notification(dino_id, f'{now_status}_end')