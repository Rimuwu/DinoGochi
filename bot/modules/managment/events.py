import time
from bot.modules.data_format import random_dict
from bot.const import GAME_SETTINGS as GS
from random import choice, randint
from bot.dbmanager import mongo_client, conf
from bot.exec import bot
from bot.modules.localization import t
import datetime

from bot.modules.overwriting.DataCalsses import DBconstructor
from random import choices
events = DBconstructor(mongo_client.other.events)

async def get_event(event_type: str=''):
    res = await events.find_one({'type': event_type}, comment='get_event_res')
    if res: return res
    return {}

async def check_event(event_type: str='') -> bool:
    res = await events.find_one({'type': event_type}, {"_id": 1}, comment='check_event_res')
    if res: return True
    return False

async def create_event(event_type: str = '', time_end: int = 0):

    if not event_type:
        event_types = {
            'add_hunting': 20,
            'add_fishing': 20,
            'add_collecting': 20,
            'add_all': 10,
            'xp_boost': 5,
            'xp_premium_boost': 5
        }
        event_type = choices(
            list(event_types.keys()),
            list(event_types.values())
        )[0]

    event = {
        'type': event_type,
        'data': {},
        'time_start': int(time.time()),
        'time_end': time_end
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
        event['time_end'] = (86400 * (366 - day_n + 7)) + int(time.time())

    elif event_type in ['add_hunting', 'add_fishing', 'add_collecting', 'add_all']:
        max_col = random_dict(GS['events']['random_data']['random_col'])
        items = []

        while len(items) < max_col:
            for key, value in GS['events']['random_data'][event_type].items():
                if randint(1, value[1]) <= value[0]:
                    items.append(key)

        event['data']['items'] = items
        event['data']['special_chance'] = {}

        if time_end == 0:
            event['time_end'] = int(time.time()) + choice(GS['events']['random_data']['random_time'])

    elif event_type in ['xp_premium_boost', 'xp_boost']:
        event['data']['xp_boost'] = round(randint(1, 2) / 10, 1)

        if time_end == 0:
            event['time_end'] = int(time.time()) + choice([14_400, 28_800, 7200, 3600])

    return event

async def add_event(event: dict, delete_old: bool = False) -> bool:
    res = await events.find_one({'type': event['type']}, comment='add_event_res')
    if not res:
        await events.insert_one(event, comment='add_event')
        return True
    else: 
        if delete_old:
            await events.delete_one({'type': event['type']}, comment='add_event')
            await events.insert_one(event, comment='add_event')
            return True
        return False

async def auto_event():
    """ Проверка системных событий
    """

    # Проверка на время года
    time_year = await get_event('time_year')
    ty_event = await create_event('time_year')
    if time_year:
        if time_year['data']['season'] != ty_event['data']['season']:
            await events.update_one({'type': 'time_year'}, {"$set": {'data': ty_event['data']}}, 
                                    comment='auto_event')
    else:
        await add_event(ty_event)

    # Проверка на новогоднее событие
    if not await check_event('new_year'):
        day_n = int(time.strftime("%j"))
        if day_n >= 363:
            new_year_event = await create_event('new_year')
            await add_event(new_year_event)
            await bot.send_message(conf.bot_group_id, t("events.new_year"))

    # Проверка на 1-ое апреля
    if not await check_event('april_1'):
        today = datetime.date.today()
        day_n = int(time.strftime("%j"))

        if today.strftime("%m-%d") == "04-01":
            time_end = (86400 * 3) + int(time.time())
            april_event = await create_event('april_1', time_end)

            events_lst = []
            for i in ['add_hunting', 'add_fishing', 'add_collecting', 'add_all']:
                ev = await create_event(i, time_end)
                ev['data']['items'] = ['fried_egg']
                events_lst.append(ev)

            await add_event(april_event)

            for i in events_lst: await add_event(i, True)
            await bot.send_message(conf.bot_group_id, t("events.april_1"))

    # День рождения бота
    if not await check_event('april_5'):
        today = datetime.date.today()
        day_n = int(time.strftime("%j"))

        if today.strftime("%m-%d") == "04-05":
            time_end = (86400 * 3) + int(time.time())
            april_event = await create_event('april_5', time_end)

            events_lst = []
            add_hunting = await create_event('add_hunting', time_end)
            add_hunting['data']['items'] += ['meat_pie', 'ale', 'cake']
            events_lst.append(add_hunting)

            add_fishing = await create_event('add_fishing', time_end)
            add_fishing['data']['items'] += ['fish_cake', 'ale', 'cake']
            events_lst.append(add_fishing)

            add_collecting = await create_event('add_collecting', time_end)
            add_collecting['data']['items'] += ['berry_pie', 'ale', 'cake']
            events_lst.append(add_collecting)

            add_all = await create_event('add_all', time_end)
            add_all['data']['items'] += ['berry_pie', 'fish_cake', 'meat_pie', 'ale', 'cake']
            events_lst.append(add_all)
            
            xp_boost = await create_event('xp_boost', time_end)
            xp_boost['data']['xp_boost'] = 1
            events_lst.append(xp_boost)

            await add_event(april_event)
            for i in events_lst: await add_event(i, True)

            await bot.send_message(conf.bot_group_id, t("events.april_5"))
