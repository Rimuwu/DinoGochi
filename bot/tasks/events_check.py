from bot.config import conf, mongo_client
from bot.taskmanager import add_task
from bot.modules.managment.events import auto_event, create_event, add_event
from time import time
from random import random
from bot.modules.logs import log

from bot.modules.overwriting.DataCalsses import DBconstructor
events = DBconstructor(mongo_client.other.events)

async def old_events():
    """ Удаляет истёкшие события
    """
    events_data = await events.find({}, {'type': 1, 'time_end': 1}, comment='old_events_events_data')

    for i in events_data:
        if i['time_end'] != 0 and int(time()) >= i['time_end']:
            await events.delete_one({'type': i['type']}, comment='old_events_1')

async def random_event():
    events_data = await events.find({}, {'type': 1}, comment='random_event_events_data')
    not_system = []

    for i in events_data:
        if i['type'] not in ['new_year', 'time_year', 'april_1', 'april_5']: not_system.append(i['type'])

    if random() <= 5 and len(not_system) < 3:
        event = await create_event()
        await add_event(event)
        log(f'Создано событие - {event}')

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(auto_event, 3600, 5.0)
        add_task(old_events, 240, 1.0)
        add_task(random_event, 3600, 10.0)