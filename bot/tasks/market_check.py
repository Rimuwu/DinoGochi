from bot.config import conf, mongo_client
from bot.taskmanager import add_task
from time import time
from bot.modules.market.market import delete_product


from bot.modules.overwriting.DataCalsses import DBconstructor
products = DBconstructor(mongo_client.market.products)
users = DBconstructor(mongo_client.user.users)
preferential = DBconstructor(mongo_client.market.preferential)


async def market_delete():
    # Удаляет старые продукты
    data = await products.find({'add_time': {'$lte': int(time()) - 86_400 * 31}}, comment='market_delete_data'
                                    )
    for i in data: await delete_product(i['_id'])

async def auction_end():
    # Завершение аукциона
    data = await products.find({'end': {'$lte': int(time())}}, comment='auction_end_data'
                              )

    for i in data:
        users_data = list(i['users'])

        max_coins = 0
        winner = None
        for user in users_data:
            status = await users.find_one({'userid': user['userid']}, comment='auction_end_status')
            if status and user['coins'] >= max_coins:

                max_coins = user['coins']
                winner = i["users"].index(user)

        if winner != None:
            s = await products.update_one({'_id': i['_id']}, 
                    {'$set': {f'users.{winner}.status': 'win'}}, comment='auction_end_s')
            s.raw_result

        await delete_product(i['_id'])

async def preferential_delete():
    # Удаляет продвижение
    await preferential.delete_many({'end': {'$lte': int(time())}}, comment='preferential_delete')

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(market_delete, 43200, 20.0)
        add_task(auction_end, 600, 15.0)
        add_task(preferential_delete, 7200, 20.0)