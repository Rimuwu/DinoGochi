
from random import choice, randint
import time

from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.modules.items.items_groups import get_group
from bot.modules.items.item import AddItemToUser, get_item_dict
from bot.modules.items.item import get_data as get_item_data

from bot.const import GAME_SETTINGS
from bot.modules.items.item import get_data as get_item_data


from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import take_coins
inside_shop = DBconstructor(mongo_client.tavern.inside_shop)


ignore_items = GAME_SETTINGS['ignore_items_inside_shop']

async def create_shop(onwer_id):

    data = {
        "owner_id": onwer_id,
        "day_number": 0,
        "items": {}
    }

    res = await inside_shop.insert_one(data)
    items = await update_shop(res.inserted_id)
    return items


async def update_shop(ins_id: ObjectId) -> dict:

    shop = await inside_shop.find_one({'_id': ins_id})
    if shop:
        day_n = int(time.strftime("%j"))
        if day_n != shop['day_number']:
            items = {}

            items_group = get_group('recipe').copy()
            for i in ignore_items:
                if i in items_group: items_group.remove(i)

            for _ in range(5):
                count = randint(1, 3)

                item = choice(items_group)
                item_data = get_item_data(item)
                items_group.remove(item)

                price = GAME_SETTINGS['buyer'][item_data['rank']]['price']

                new_price = int(int(price * 3) + randint(int(price * 0.1), price))

                items[item] = {
                    'items_data': get_item_dict(item),
                    'count': count,
                    'price': new_price
                }

            await inside_shop.update_one({'_id': ins_id}, 
                                         {'$set': {'items': items, 
                                                   'day_number': day_n
                                                   }
                                          })
            return items
    return {}

async def get_content(owner_id: int): 
    shop = await inside_shop.find_one({'owner_id': owner_id})

    if shop:
        res = await update_shop(shop['_id'])
        if res != {}: return res
        else: return shop['items']

    else:
        return await create_shop(owner_id)

async def item_buyed(owner_id: int, item_key: str, col: int):
    shop = await inside_shop.find_one({'owner_id': owner_id})
    if shop:
        if item_key in shop['items']:
            item = shop['items'][item_key]
            if col <= item['count']:
                if await take_coins(owner_id, -col * item['price']):
                    await AddItemToUser(owner_id, item_key, col)

                    await inside_shop.update_one({'_id': shop['_id']}, {
                        '$inc': {f'items.{item_key}.count': -col}
                    })

                    return True

    return False