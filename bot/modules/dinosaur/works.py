
from bson.objectid import ObjectId
from bot.config import mongo_client

from bot.modules.items.item import AddItemToUser, get_item_dict
from bot.modules.overwriting.DataCalsses import DBconstructor
from time import time

from bot.modules.user.user import take_coins

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

kindergarten = DBconstructor(mongo_client.dino_activity.kindergarten)
kd_activity = DBconstructor(mongo_client.dino_activity.kd_activity)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

works_data = {

    "bank": {
        "time": 3600 * 4,
        "max_coins": 15000,
        "max_items": 6
    },

    "mine": {
        "time": 3600 * 2,
        "max_coins": 7000,
        "max_items": 7
    },

    "sawmill": {
        "time": 3600 * 2,
        "max_coins": 7000,
        "max_items": 15
    }

}

async def start_mine(dino_baseid: ObjectId, owner_id: int, action_type: str):

    data = {
        'activity_type': 'mine',

        'sended': owner_id,
        'dino_id': dino_baseid,

        'start_time': int(time()),
        'end_time': int(time()) + works_data['mine']['time'],

        'last_check': int(time()), 
        'last_view': 0,
        'checks': 3
    }

    if action_type == 'coins':
        data['coins'] = 0
        data['max_coins'] = works_data['mine']['max_coins']

    elif action_type == 'ore':
        data['items'] = {}
        data['max_items'] = works_data['mine']['max_items']
        data['item_per_hour'] = 3

    await long_activity.insert_one(data)

async def start_bank(dino_baseid: ObjectId, owner_id: int, action_type: str):

    data = {
        'activity_type': 'bank',

        'sended': owner_id,
        'dino_id': dino_baseid,

        'start_time': int(time()),
        'end_time': int(time()) + works_data['bank']['time'],

        'last_check': int(time()), 
        'last_view': 0,
        'checks': 3
    }

    if action_type == 'coins':
        data['coins'] = 0
        data['max_coins'] = works_data['bank']['max_coins']

    elif action_type == 'recipes':
        data['items'] = {}
        data['max_items'] = works_data['bank']['max_items']
        data['item_per_hour'] = 1

    await long_activity.insert_one(data)

async def start_sawmill(dino_baseid: ObjectId, owner_id: int, action_type: str):

    data = {
        'activity_type': 'sawmill',

        'sended': owner_id,
        'dino_id': dino_baseid,

        'start_time': int(time()),
        'end_time': int(time()) + works_data['sawmill']['time'],

        'last_check': int(time()), 
        'last_view': 0,
        'checks': 3,
    }

    if action_type == 'coins':
        data['coins'] = 0
        data['max_coins'] = works_data['sawmill']['max_coins']

    elif action_type == 'wood':
        data['items'] = {}
        data['max_items'] = works_data['sawmill']['max_items']
        data['item_per_hour'] = 5

    await long_activity.insert_one(data)

async def end_work(dino_baseid: ObjectId):

    res = await long_activity.find_one(
        {'activity_type': {'$in': ['bank', 'mine', 'sawmill']}, 'dino_id':dino_baseid}
    )
    if res:
        sended = res['sended']
        if 'coins' in res:
            await take_coins(sended, res['coins'], True)

        elif 'items' in res:
            """
            item: {
                'item_data': {},
                'count': int
            }
            """

            for key, item in res['items'].items():
                data = get_item_dict(key)

                item_id = data['item_id']
                abilities = data.get('abilities', {})
                await AddItemToUser(sended, item_id, item['count'], abilities)

        await long_activity.delete_one({'_id': res['_id']})