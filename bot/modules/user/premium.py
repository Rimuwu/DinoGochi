

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.dbmanager import mongo_client

subscriptions = DBconstructor(mongo_client.user.subscriptions)

async def premium(userid: int):
    res = await subscriptions.find_one({'userid': userid}, comment='premium_res')
    return bool(res)