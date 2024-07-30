from random import choice, randint
from time import time

from bson.objectid import ObjectId

from bot.config import mongo_client
from bot.modules.dinosaur.dinosaur import set_status, start_game, Dino
from bot.modules.items.accessory import downgrade_accessory
from bot.modules.notifications import dino_notification
from bot.const import GAME_SETTINGS

from bot.modules.overwriting.DataCalsses import DBconstructor
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

max_stack = 5

keys = [
    'good_sleep', 'end_game', 'multi_games', 'multi_heal', 
    'multi_eat', 'multi_energy', 'dream', 'good_eat', 'playing_together', 'sunshine', 'breeze', 'meeting_friend', 'magic_animal', 'magic_light', 'pet', 'talk_good', 'simple_work'
    # Положительное 

    'bad_sleep', 'stop_game', 'little_game', 'little_heal',
    'little_eat', 'little_energy', 'bad_dream', 'bad_eat', 'repeat_eat', 'rain', 'cold_wind', 'snowfall', 'drought',
    'break', 'bad_talk', 'hard_work', 'repeat_activity'
    # Отрицательное

    'journey_event' 
    # Любое
]


breakdowns = {
    'seclusion': {
        'cancel_mood': 35,
        'duration_time': (1800, 7200),
    },

    'hysteria': {
        'cancel_mood': 30,
        'duration_time': (1800, 4500)
    },

    'unrestrained_play': {
        'cancel_mood': 30,
        'duration_time': (4150, 5400)
    }, 

    'downgrade': {
        'duration_time': 0
    }
}

inspiration = {
    'game': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
        },
    'collecting': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
        },
    'journey': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
        },
    'sleep': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
    }
}

EVENT_POINT = GAME_SETTINGS['event_points']
BONUS = GAME_SETTINGS['inspiration_bonus']

async def add_mood(dino: ObjectId, key: str, unit: int, duration: int, 
             stacked: bool = False):
    """ Добавляет в лог dino событие по key, которое влияет на настроение в размере unit в течении time секунд
    """
    res = await dino_mood.find({'dino_id': dino, 
                              'action': key, 
                              'type': 'mood_edit'}, comment='add_mood_res'
                             )

    if not stacked and res: 
        await dino_mood.update_one({'_id': res[0]['_id']}, 
                                   {'$set': {'end_time': int(time()) + duration}}, comment='add_mood_1')
        return False
    else:
        if len(list(res)) >= max_stack: return False

    if key in keys:
        data = {
            'dino_id': dino,
            'action': key,
            'unit': unit,
            'end_time': int(time()) + duration,
            'start_time': int(time()),
            'type': 'mood_edit'
        }

        await dino_mood.insert_one(data, comment='add_mood_2')
        return True
    return False

async def mood_while_if(dino: ObjectId, key: str, characteristic: str, 
                  min_unit: int, max_unit: int, unit: int):
    """ Добавляет в лог dino событие по key, которое влияет на настроение в пока его characteristic не меньше min_unit и не выше max_unit
    
        Такая запись может быть одна на ключ
    """

    res = await dino_mood.find_one({'dino_id': dino, 'action': key, 'type': 'mood_while'}, 
                                   comment='mood_while_if_res')

    if not res:
        if key in keys:
            data = {
                'dino_id': dino,
                'action': key,
                'unit': unit,

                'while': {
                    'min_unit': min_unit,
                    'max_unit': max_unit,
                    'characteristic': characteristic
                },

                'start_time': int(time()),
                'type': 'mood_while'
            }

            # print('mood_while_if', dino, key, characteristic, min_unit, max_unit)
            await dino_mood.insert_one(data, comment='mood_while_if_1')

async def dino_breakdown(dino: ObjectId):
    """ Вызывает нервный срыв у динозавра на duration секунд. Чтобы отменить нервный срыв, требуется повысить настроение до cancel_mood или он закончится после определённого времени.

    >> seclusion - динозавр не присылает уведомления
    >> hysteria - динозавр отказывается что либо делать
    >> unrestrained_play - динозавр начнёт играть на протяжении 3-ёх часов
    >> downgrade - немного ломает случайный активный предмет
    """

    action = choice(list(breakdowns.keys()))
    duration_s = breakdowns[action]['duration_time']

    if duration_s:
        duration = randint(*duration_s)
        cancel_mood = breakdowns[action]['cancel_mood']

        data = {
            'dino_id': dino,
            'cancel_mood': cancel_mood,
            'end_time': int(time()) + duration,
            'start_time': int(time()),
            'type': 'breakdown',
            'action': action
        }
        await dino_mood.insert_one(data, comment='dino_breakdown')

    if action == 'hysteria': await set_status(dino, 'hysteria')
    elif action == 'unrestrained_play': await start_game(dino, 10800, 0.4)
    elif action == 'downgrade':
        dino_cl = await Dino().create(dino)

        allowed = []
        for i in ['game', 'collecting', 'journey', 'sleep', 'armor', 'weapon', 'backpack']:
            if dino_cl.activ_items[i]: allowed.append(i)

        if allowed:
            await downgrade_accessory(dino_cl, choice(allowed))

    # print('dino_nervous_breakdown', action, duration_s)
    return action

async def dino_inspiration(dino: ObjectId): 
    """ Вызывает вдохновение у динозавра на duration секунд. Чтобы отменить вдохновение, требуется повысить настроение до cancel_mood или оно закончится после определённого времени.
    
    Все вдохновения ускоряют действие в 2 раза.
    """
    action = choice(list(inspiration.keys()))

    duration_s = inspiration[action]['duration_time']
    duration = randint(*duration_s)
    cancel_mood = inspiration[action]['cancel_mood']

    data = {
        'dino_id': dino,
        'cancel_mood': cancel_mood,
        'end_time': int(time()) + duration,
        'start_time': int(time()),
        'type': 'inspiration',
        'action': action
    }

    # print('dino_inspiration', duration, cancel_mood, action)
    await dino_mood.insert_one(data, comment='dino_inspiration')
    return action

async def calculation_points(dino: dict, point_type: str):
    """ Высчитывает очки вдохновение / срыва и запускает его + отправляет уведомление\n
        'breakdown', 'inspiration'
    """

    assert point_type in ['breakdown', 'inspiration'], f'Неподходящий аргумент {point_type}'
    alter = 'breakdown'

    res_break = await dino_mood.find_one({'dino_id': dino['_id'], 'type': 'breakdown'}, 
                                         comment='calculation_points_res_break')
    res_insp = await dino_mood.find_one({'dino_id': dino['_id'], 'type': 'inspiration'}, 
                                        comment='calculation_points_res_insp')

    if not (res_break and res_insp):

        mood_points = dino['mood']
        if point_type == 'breakdown': alter = 'inspiration'

        if mood_points[alter] != 0:
            await dinosaurs.update_one({'_id': dino['_id']}, 
                                {'$inc': {f'mood.{alter}': -1}}, comment='calculation_points_12')

        else:
            if mood_points[point_type] + 1 >= EVENT_POINT:
                if point_type == 'breakdown':
                    action = await dino_breakdown(dino['_id'])
                else:
                    action = await dino_inspiration(dino['_id'])

                await dinosaurs.update_one({'_id': dino['_id']}, 
                                    {'$set': {f'mood.{point_type}': 0}}, comment='calculation_points_13')

                add_message = f'{point_type}.{action}' # После получения языка, добавит текст с этого пути
                await dino_notification(dino['_id'], point_type, add_message=add_message, bonus=BONUS)

            else:
                res = await dino_mood.find_one({'dino_id': dino['_id'], 
                                        'type': point_type}, comment='calculation_points_res')
                if not res:
                    await dinosaurs.update_one({'_id': dino['_id']}, 
                                    {'$inc': {f'mood.{point_type}': 1}}, comment='calculation_points_14')

async def check_inspiration(dino_id: ObjectId, action_type: str) -> bool:
    """ Проверяет есть ли у динозавра вдохновение данного типа
    """
    assert action_type in list(inspiration.keys()), f'Тип {action_type} не существует!'

    res = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'inspiration', 'action': action_type}, comment='check_inspiration_res')
    return bool(res)

async def check_breakdown(dino_id: ObjectId, action_type: str = '') -> bool:
    """ Проверяет есть ли у динозавра нервный срыв данного типа (если не указано, то есть ли в общем)
    """
    assert action_type in list(breakdowns.keys()), f'Тип {action_type} не существует!'

    if action_type:
        res = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'breakdown', 'action': action_type}, comment='check_breakdown_res')
    else:
        res = await dino_mood.find_one({'dino_id': dino_id, 
                            'type': 'breakdown'}, comment='check_breakdown_res1')

    return bool(res)

async def repeat_activity(dino_id: ObjectId, percent: float):
    if percent != 0:
        if randint(0, 100) <= percent:
            await add_mood(dino_id, 'repeat_activity', -1, 3600, True)