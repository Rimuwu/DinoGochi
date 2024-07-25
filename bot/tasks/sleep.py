from time import time
from random import uniform, randint

from bot.config import conf, mongo_client
from bot.modules.dinosaur.dinosaur  import end_sleep, mutate_dino_stat, get_owner
from bot.taskmanager import add_task
from bot.modules.dinosaur.mood import add_mood, check_inspiration
from bot.modules.user.user import experience_enhancement

from bot.modules.overwriting.DataCalsses import DBconstructor
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

LONG_SLEEP_COLDOWN_MIN = 7
DREAM_CHANCE = 0.01

async def one_time(sleeper, one_time_unit):
    add_energy, sec_time = 0, 0
    dino = await dinosaurs.find_one({'_id': sleeper['dino_id']}, comment='one_time_dino')

    if await check_inspiration(sleeper['dino_id'], 'sleep'): 
        one_time_unit *= 2

    if sleeper['sleep_type'] == 'long':
        sec_time = int(time()) - sleeper['sleep_start']
    elif sleeper['sleep_type'] == 'short':
        sec_time = sleeper['sleep_end'] - sleeper['sleep_start']

    if randint(0, 1):
        owner = await get_owner(dino['_id'])
        await experience_enhancement(owner['owner_id'], randint(1, 2))

    if dino:
        energy = dino['stats']['energy']
        if energy >= 100:
            await end_sleep(sleeper['dino_id'], sec_time)
        else:
            if energy + one_time_unit >= 100:
                add_energy = 100 - energy
                await end_sleep(sleeper['dino_id'], sec_time)
            else: add_energy = one_time_unit

            if uniform(0, 1) <= DREAM_CHANCE:
                if randint(1, 3) == 2:
                    await add_mood(dino['_id'], 'bad_dream', -1, 2700, True)
                else:
                    await add_mood(dino['_id'], 'dream', 1, 2700, True)

            await mutate_dino_stat(dino, 'energy', add_energy)
    else:
        await long_activity.delete_one({"_id": sleeper['_id']}, comment='one_time_1')

async def check_notification():
    """Уведомления и окончание сна
    """
    data = await long_activity.find(
                    {'sleep_end': {'$lte': int(time())}, 
                     'activity_type': 'sleep'}, comment='check_notification_data')

    for sleeper in data:
        dino = await dinosaurs.find_one({'_id': sleeper['dino_id']}, comment='check_notification_dino')
        if dino:
            await end_sleep(sleeper['dino_id'],
                            sleeper['sleep_end'] - sleeper['sleep_start'])
            if sleeper['sleep_type'] == 'short':
                mood_time = (int(time()) - sleeper['sleep_start']) // 2
            else: mood_time = 2700

            await add_mood(dino['_id'], 'good_sleep', 1, mood_time)

async def short_check():
    data = await long_activity.find({'sleep_type': 'short', 'activity_type': 'sleep'}, comment='short_check_data')
    for sleeper in data: await one_time(sleeper, 2)

async def long_check():
    data = await long_activity.find({'sleep_type': 'long', 'activity_type': 'sleep'}, comment='long_check_data')
    for sleeper in data: await one_time(sleeper, 1)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(long_check, LONG_SLEEP_COLDOWN_MIN * 60.0, 1.0)
        add_task(short_check, (LONG_SLEEP_COLDOWN_MIN // 2) * 60.0, 1.0)
        add_task(check_notification, 30.0, 1.0)