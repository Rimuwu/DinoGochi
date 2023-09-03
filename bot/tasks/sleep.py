from time import time
from random import uniform, randint

from bot.config import conf, mongo_client
from bot.modules.dinosaur import end_sleep
from bot.taskmanager import add_task
from bot.modules.mood import add_mood, check_inspiration

sleepers = mongo_client.dino_activity.sleep
dinosaurs = mongo_client.dinosaur.dinosaurs

LONG_SLEEP_COLDOWN_MIN = 6
LONG_SLEEP_TIME_MIN = 600
LONG_MAX_UNIT_AFTER = LONG_SLEEP_TIME_MIN // LONG_SLEEP_COLDOWN_MIN
LONG_ONE_TIME = LONG_MAX_UNIT_AFTER // 100

SHORT_SLEEP_COLDOWN_MIN = LONG_SLEEP_COLDOWN_MIN // 2
SHORT_SLEEP_TIME_MIN = LONG_SLEEP_TIME_MIN // 2
SHORT_MAX_UNIT_AFTER = SHORT_SLEEP_TIME_MIN // SHORT_SLEEP_COLDOWN_MIN
SHORT_ONE_TIME = SHORT_MAX_UNIT_AFTER // 100

DREAM_CHANCE = 0.01

async def one_time(data, one_time_unit):
    for sleeper in data:
        add_energy, sec_time = 0, 0
        dino = dinosaurs.find_one({'_id': sleeper['dino_id']})

        if check_inspiration(sleeper['dino_id'], 'sleep'): 
            one_time_unit *= 2

        if sleeper['sleep_type'] == 'long':
            sec_time = int(time()) - sleeper['sleep_start']
        elif sleeper['sleep_type'] == 'short':
            sec_time = sleeper['sleep_end'] - sleeper['sleep_start']

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
                        add_mood(dino['_id'], 'bad_dream', -1, 2700, True)
                    else:
                        add_mood(dino['_id'], 'dream', 1, 2700, True)

                dinosaurs.update_one({'_id': dino['_id']}, {'$inc': {'stats.energy': add_energy}})
        else:
            sleepers.delete_one({"_id": sleeper['_id']})

async def check_notification():
    """Уведомления и окончание сна
    """
    data = list(sleepers.find({'sleep_end': {'$lte': int(time())}})
                ).copy()

    for sleeper in data:
        dino = dinosaurs.find_one({'_id': sleeper['dino_id']})
        if dino:
            await end_sleep(sleeper['dino_id'],
                            sleeper['sleep_end'] - sleeper['sleep_start'])
            if sleeper['sleep_type'] == 'short':
                mood_time = (int(time()) - sleeper['sleep_start']) // 2
            else: mood_time = 2700

            add_mood(dino['_id'], 'good_sleep', 1, mood_time)

async def short_check():
    data = list(sleepers.find({'sleep_type': 'short'})).copy()
    await one_time(data, 1)

async def long_check():
    data = list(sleepers.find({'sleep_type': 'long'})).copy()
    await one_time(data, 1)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(long_check, 12 * 60.0, 1.0)
        add_task(short_check, 6 * 60.0, 1.0)
        add_task(check_notification, 30.0, 1.0)
