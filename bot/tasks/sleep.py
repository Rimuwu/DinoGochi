from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.activity import Activity
from bot.models.dinosaur import State, DinoMood, Dino
from bot.models.user import User
from time import time
from random import randint, random

from bot.config import conf
from bot.modules.data_format import transform
from bot.models.dinosaur import Dino
from bot.models.activity import SleepActivity
from bot.models.items import Item
from bot.taskmanager import add_task


long_activity = LazyCollection(Activity)
dinosaurs = LazyCollection(Dino)

DREAM_CHANCE = 0.01

async def pre_end(dino_id, sec_time, notif=True):

    await SleepActivity.end(dino_id, sec_time, notif)
    dino = await Dino().create(dino_id)
    
    if dino:
        pillow = await Item.check_accessory(
                dino.id, 'pillow', True
            )
        if pillow:
                bonus = 2 + pillow.get_level()
                await State.add(dino_id, 'energy', bonus, 3600)

        else:
            blanket = await Item.check_accessory(
                    dino.id, 'blanket', True
                )
            if blanket:
                    bonus = 2 + blanket.get_level()
                    await State.add(dino_id, 'heal', bonus, 3600)

async def one_time(sleeper, one_time_unit):
    add_energy, sec_time = 0, 0
    dino = await dinosaurs.find_one({'_id': sleeper['dino_id']}, comment='one_time_dino')

    if await DinoMood.check_inspiration(sleeper['dino_id'], 'sleep'): 
        one_time_unit *= 2

    if sleeper['sleep_type'] == 'long':
        sec_time = int(time()) - sleeper['start_time']
    elif sleeper['sleep_type'] == 'short':
        sec_time = sleeper['end_time'] - sleeper['start_time']

    if dino:
        if randint(0, 1):
            owner_conn = await Dino.get_owner_by_id(dino['_id'])
            if owner_conn and owner_conn.owner_id:
                user_obj = await User.find_one(User.userid == owner_conn.owner_id)
                if user_obj:
                    if await DinoMood.check_inspiration(dino['_id'], 'exp_boost'):
                        await user_obj.add_xp_lvl(randint(1, 4))
                    else:
                        await user_obj.add_xp_lvl(randint(1, 2))

                    if randint(1, 100) + transform(dino['stats']['charisma'], 20, 30) >= 80:
                        await user_obj.add_xp_lvl(randint(1, 2))

        energy = dino['stats']['energy']
        if energy >= 100:
            await pre_end(sleeper['dino_id'], sec_time)
        else:
            if energy + one_time_unit >= 100:
                add_energy = 100 - energy
                await pre_end(sleeper['dino_id'], sec_time)
            else: add_energy = one_time_unit

            if random() <= DREAM_CHANCE:
                if randint(1, 3) == 2:
                    await DinoMood.add(dino['_id'], 'bad_dream', -1, 2700, True)
                else:
                    await DinoMood.add(dino['_id'], 'dream', 1, 2700, True)

            if dino['mood']['breakdown'] != 0 and randint(1, 3) == 3:
                dino_class = await Dino().create(dino['_id'])
                if dino_class:
                    toy = await Item.check_accessory(
                        dino_class.id, 'toy_solider', True
                        )
                    if toy:
                        reduction = -1 - toy.get_level()
                        await dinosaurs.update_one(
                            {'_id': dino['_id']}, 
                            {'$inc': {'mood.breakdown': reduction}}
                        )

            await Dino.mutate_stat(dino, 'energy', add_energy)
    else:
        await long_activity.delete_one({"_id": sleeper['_id']}, comment='one_time_1')

async def check_notification():
    """Уведомления и окончание сна
    """
    data = await long_activity.find(
                    {'end_time': {'$lte': int(time())}, 
                     'activity_type': 'sleep'}, comment='check_notification_data')

    for sleeper in data:
        dino = await dinosaurs.find_one({'_id': sleeper['dino_id']}, comment='check_notification_dino')
        if dino:
            sec_time = int(time()) - sleeper['start_time']
            await pre_end(sleeper['dino_id'], sec_time)
            mood_time = sec_time // 2

            await DinoMood.add(dino['_id'], 'good_sleep', 1, mood_time)

async def short_check():
    data = await long_activity.find({'sleep_type': 'short', 'activity_type': 'sleep'}, comment='short_check_data')
    for sleeper in data: await one_time(sleeper, 1)

async def long_check():
    data = await long_activity.find({'sleep_type': 'long', 'activity_type': 'sleep'}, comment='long_check_data')
    for sleeper in data: await one_time(sleeper, 1)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(long_check, 360.0, 1.0)
        add_task(short_check, 144.0, 1.0)
        add_task(check_notification, 30.0, 1.0)