import time
from bot.modules.data_format import random_dict
from bot.const import GAME_SETTINGS as GS
from random import choice, randint
from bot.config import mongo_client

events = mongo_client.other.events

async def get_event(event_type: str=''):
    res = await events.find_one({'type': event_type})
    if res: return res
    return {}

async def create_event(event_type: str = ''):

    if not event_type:
        event_type = choice(['add_hunting', 'add_fishing', 'add_collecting', 'add_all'])

    event = {
        'type': event_type,
        'data': {},
        'time_start': int(time.time()),
        'time_end': 0
    }

    if event_type == 'time_year':
        month_n = int(time.strftime("%m"))
        
        if month_n < 3 or month_n > 11:
            event['data']['season'] = 'winter'
        elif 6 > month_n > 2:
            event['data']['season'] = 'spring'
        elif 9 > month_n > 5:
            event['data']['season'] = 'summer'
        else: event['data']['season'] = 'autumn'

    elif event_type == 'new_year':
        day_n = int(time.strftime("%j"))

        event['data']['send'] = []
        event['time_end'] = (86400 * (366 - day_n) + 5) + int(time.time())

    elif event_type in ['add_hunting', 'add_fishing', 'add_collecting', 'add_all']:
        max_col = random_dict(GS['events']['random_data']['random_col'])
        items = []

        while len(items) < max_col:
            for key, value in GS['events']['random_data'][event_type].items():
                if randint(1, value[1]) <= value[0]:
                    items.append(key)

        event['data']['items'] = items
        event['time_end'] = int(time.time()) + choice(GS['events']['random_data']['random_time'])
    return event

async def add_event(event: dict):
    res = await events.find_one({'type': event['type']})
    if not res:
        await events.insert_one(event)
        return True
    else: return False

async def auto_event():
    """ Проверка системных событий
    """
    # Проверка на время года
    time_year = await get_event('time_year')
    ty_event = await create_event('time_year')
    if time_year:
        if time_year['data']['season'] != ty_event['data']['season']:
            await events.update_one({'type': 'time_year'}, {"$set": {'data': ty_event['data']}})
    else: await add_event(ty_event)
    
    # Проверка на новогоднее событие
    new_year = get_event('time_year')
    if not new_year:
        day_n = int(time.strftime("%j"))
        if day_n >= 358:
            new_year_event = await create_event('new_year')
            await add_event(new_year_event)