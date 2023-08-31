import random
from random import randint

from bot.config import conf, mongo_client
from bot.taskmanager import add_task
from bot.modules.user import take_coins
from time import time
from bot.modules.market import delete_product

products = mongo_client.market.products
sellers = mongo_client.market.sellers
users = mongo_client.user.users
preferential = mongo_client.market.preferential

async def market_delete():
    # Удаляет старые продукты
    data = list(products.find({'add_time': {'$lte': int(time()) - 86_400 * 31}})
                ).copy()
    for i in data: await delete_product(i['_id'])

async def auction_end():
    # Завершение аукциона
    data = list(products.find({'end': {'$lte': int(time())}})
                ).copy()

    for i in data:
        for user in i['users']:
            status = users.find_one({'user_id': user['userid']})
            if status:
                products.update_one({'_id': i['_id']}, {'$set': {
                    f'users.{i["users"].index(user)}.status': 'win'
                }})
                take_coins(i['owner_id'], i['coins'], True)
                break

        await delete_product(i['_id'])

async def preferential_delete():
    # Удаляет продвижение
    data = list(products.find({'end': {'$lte': int(time())}})
                ).copy()
    for i in data: preferential.delete_one({'_id': i['_id']})

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(market_delete, 43200, 20.0)
        add_task(auction_end, 7200, 15.0)
        add_task(preferential_delete, 7200, 20.0)