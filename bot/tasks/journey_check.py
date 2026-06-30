from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.activity import Activity, JourneyActivity
from bot.models.dinosaur import DinoMood, Dino
from random import randint, random
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.handlers.actions_live.journey import send_logs
from bot.modules.data_format import transform
from bot.models.items import Item
from bot.models.dinosaur import Dino
from bot.models.activity import JourneyActivity
from bot.modules.quests import quest_process
from bot.modules.user.user import experience_enhancement
from bot.taskmanager import add_task
from bot.models.items import Item

long_activity = LazyCollection(Activity)
dinosaurs = LazyCollection(Dino)

REPEAT_MINUTS = 6
EVENT_CHANCE = 0.6

async def end_journey_time():
    data = await long_activity.find(
        {'journey_end': {'$lte': int(time())}, 'activity_type': 'journey'}, comment='end_journey_time_data')
    for i in data:
        dino = await dinosaurs.find_one({'_id': i['dino_id']}, comment='end_journey_time_dino')
        if dino:
            await JourneyActivity.end(i['dino_id'])
            await quest_process(i['sended'], 'journey', (int(time()) - i['journey_start']) // 60)

            lang = await Dino.get_language(i['dino_id'])
            await send_logs(i['sended'], lang, i, dino['name'])

async def events():
    data = await long_activity.find(
        {'journey_end': {'$gte': int(time())}, 'activity_type': 'journey'}, comment='events_data')

    for i in data:
        event_random = round(random(), 3)

        chance = EVENT_CHANCE
        dino = await Dino().create(i['dino_id'])
        if not dino: continue

        res = await DinoMood.check_inspiration(i['dino_id'], 'journey')
        if res: chance *= 2

        hik_flag = False
        if event_random >= chance:
            if await Item.check_accessory(dino, 'hiking_bag'):
                chance += 0.3
                hik_flag = True

        if event_random <= chance:
            await JourneyActivity.random_event(i['dino_id'], i['location'])
            if hik_flag:
                await Item.check_accessory(dino, 'hiking_bag', True)

            if randint(0, 1):
                if await DinoMood.check_inspiration(dino._id, 'exp_boost'):
                    await experience_enhancement(i['sended'], randint(1, 4))
                else:
                    await experience_enhancement(i['sended'], randint(1, 2))

            if randint(1, 100) + transform(dino.stats['charisma'], 20, 30) >= 80:
                await experience_enhancement(i['sended'], randint(1, 2))

if __name__ != '__main__':
    if conf.active_tasks: 
        add_task(end_journey_time, 30.0, 5.0)
        add_task(events, REPEAT_MINUTS * 60.0, 20.0)