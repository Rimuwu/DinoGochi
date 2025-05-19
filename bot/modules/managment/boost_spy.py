from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.dbmanager import mongo_client
import time
from bot.exec import bot
from bot.const import GAME_SETTINGS

boosters = DBconstructor(mongo_client.other.boosters)

async def user_boost_channel_status(userid: int):
    try:
        res = await bot.get_user_chat_boosts(GAME_SETTINGS['channel_id'], userid)
        if res and len(res.boosts) > 0:
            return True
        return False
    except: return False

async def create_boost(userid: int, end_time: int = 0) -> dict:
    """ Создание бустера
    """

    check = await boosters.find_one({'user_id': userid}, comment='create_boost')
    if check:
        # message
        return check

    boost = {
        'user_id': userid,
        'end_time': end_time,
        'time': int(time.time())
    }

    # message
    await boosters.insert_one(boost, comment='create_boost')
    return boost

async def delete_boost(userid: int):
    """ Удаление бустера
    """

    res = await user_boost_channel_status(userid)
    if not res:
        await boosters.delete_one({'user_id': userid}, comment='delete_boost')
        # message