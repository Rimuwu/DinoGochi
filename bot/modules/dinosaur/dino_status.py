
from bson.objectid import ObjectId
from bot.config import mongo_client

from bot.modules.data_format import random_code
from bot.modules.overwriting.DataCalsses import DBconstructor
from time import time

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

kindergarten = DBconstructor(mongo_client.dino_activity.kindergarten)
kd_activity = DBconstructor(mongo_client.dino_activity.kd_activity)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

async def check_status(dino_id):

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

        on_craft = status == 'craft'
        on_farm = status == 'farm'

        in_mine = status == 'mine'
        in_bank = status == 'bank'
        in_sawmill = status == 'sawmill'

        in_gym = status == 'gym'
        in_library = status == 'library'
        in_park = status == 'park'
        in_swimming_pool = status == 'swimming_pool'

        in_sleep = status == 'sleep'
        in_game = status == 'game'
        in_journey = status == 'journey'
        in_collecting = status == 'collecting'

        inactive = status == 'inactive'

        dungeon = False
        in_kindergarten = await kindergarten.find_one({'dinoid': dino_id}, 
                                    comment='check_status_in_kindergarten')

        hysteria = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'breakdown', 'action': 'hysteria'}, comment='check_status_hysteria')
        unrestrained_play = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'breakdown', 'action': 'unrestrained_play'}, comment='check_status_unrestrained_play')

        data = ['sleep', 'unrestrained_play', 'game', 'journey', 'collecting', 'dungeon', 'kindergarten', 'hysteria', 'farm', 'mine', 'bank', 'sawmill', 'gym', 'library', 'park', 'swimming_pool', 'craft', 'inactive']
        checks = [bool(in_sleep), bool(unrestrained_play), bool(in_game), bool(in_journey), bool(in_collecting), bool(dungeon), bool(in_kindergarten), bool(hysteria),  bool(on_farm), bool(in_mine), bool(in_bank), bool(in_sawmill), bool(in_gym), bool(in_library), bool(in_park), bool(in_swimming_pool), bool(on_craft), bool(inactive)]

        if True in checks: status = data[checks.index(True)]
        return status
    return 'pass'


skill_time = {
    "gym": [5400, 10800],
    "library": [1800, 7200],
    "swimming_pool": [5400, 7200],
    "park": [1200, 7200],
}

def get_skill_time(skill: str): return skill_time[skill]

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
            'min_time': skill_time[activity][0], 'max_time': skill_time[activity][1],
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