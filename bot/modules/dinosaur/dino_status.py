
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

        dungeon = False
        in_kindergarten = await kindergarten.find_one({'dinoid': dino_id}, 
                                    comment='check_status_in_kindergarten')
        hysteria = await dino_mood.find_one({'dino_id': dino_id, 
                              'type': 'breakdown', 'action': 'hysteria'}, comment='check_status_hysteria')

        data = ['sleep', 'game', 'journey', 'collecting', 'dungeon', 'kindergarten', 'hysteria', 'farm', 'mine', 'bank', 'sawmill', 'gym', 'library', 'park', 'swimming_pool']
        checks = [bool(in_sleep), bool(in_game), bool(in_journey), bool(in_collecting), bool(dungeon), bool(in_kindergarten), bool(hysteria),  bool(on_farm), bool(in_mine), bool(in_bank), bool(in_sawmill), bool(in_gym), bool(in_library), bool(in_park), bool(in_swimming_pool)]

        if True in checks: status = data[checks.index(True)]
        return status
    return 'pass'

async def start_skill_activity(dino_id: ObjectId, activity: str, up: str, down: str, up_unit: float, down_unit: float, time_end: int, sended: int):
    """ up_unit | down_unit - float число сколько сколько понижается / повышается 
        за 10 минут
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

            'end_time': time_end + int(time()), 'last_check': int(time()),

            'activity_type': activity,
            'alt_code': random_code(),

            'up_unit': 0.0 # Считаем, сколько было повышено и вычитаем 50% при отмене заранее.
        }
        result = await long_activity.insert_one(act, comment=f'start_{activity}')
    return act

async def end_skill_activity(dino_id: ObjectId):

    res = await long_activity.find_one({'dino_id': dino_id}, comment=f'end_skill_activity')

    if res and res['activity_type'] in ['gym', 'library', 'swimming_pool', 'park']:
        await long_activity.delete_one({'_id': res['_id']}, comment='end_skill_act_del')

        return 1
    else: return 0