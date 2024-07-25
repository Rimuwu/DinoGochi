import random
from random import randint
from time import time

from bot.config import conf, mongo_client
from bot.handlers.actions_live.journey import send_logs
from bot.modules.items.accessory import check_accessory
from bot.modules.dinosaur.dinosaur  import (Dino, end_collecting, end_journey,
                                  get_dino_language, mutate_dino_stat)
from bot.modules.dinosaur.journey import random_event
from bot.modules.quests import quest_process
from bot.modules.user.user import experience_enhancement
from bot.taskmanager import add_task
from bot.modules.items.accessory import check_accessory
from bot.modules.dinosaur.mood import check_inspiration

from bot.modules.overwriting.DataCalsses import DBconstructor
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

REPEAT_MINUTS = 6
EVENT_CHANCE = 0.17 * REPEAT_MINUTS

async def end_journey_time():
    data = await long_activity.find(
        {'journey_end': {'$lte': int(time())}, 'activity_type': 'journey'}, comment='end_journey_time_data')
    for i in data:
        dino = await dinosaurs.find_one({'_id': i['dino_id']}, comment='end_journey_time_dino')
        if dino:
            await end_journey(i['dino_id'])
            await quest_process(i['sended'], 'journey', (int(time()) - i['journey_start']) // 60)

            lang = await get_dino_language(i['dino_id'])
            await send_logs(i['sended'], lang, i, dino['name'])

async def events():
    data = await long_activity.find(
        {'journey_end': {'$gte': int(time())}, 'activity_type': 'journey'}, comment='events_data')

    for i in data:
        chance = EVENT_CHANCE
        dino = await Dino().create(i['dino_id'])

        res = await check_inspiration(i['dino_id'], 'journey')
        if res: chance *= 2

        if await check_accessory(dino, 'hiking_bag'):
            chance += 0.6 * REPEAT_MINUTS

        if random.uniform(0, 1) <= chance:
            await random_event(i['dino_id'], i['location'])
            await check_accessory(dino, 'hiking_bag', True)

            if randint(0, 1): 
                await experience_enhancement(i['sended'], randint(1, 2))

if __name__ != '__main__':
    if conf.active_tasks: 
        add_task(end_journey_time, 30.0, 5.0)
        add_task(events, REPEAT_MINUTS * 60.0, 20.0)