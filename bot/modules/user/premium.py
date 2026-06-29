from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import Subscription


from bot.dbmanager import mongo_client

subscriptions = LazyCollection(Subscription)

async def premium(userid: int):
    res = await subscriptions.find_one({'userid': userid}, comment='premium_res')
    return bool(res)