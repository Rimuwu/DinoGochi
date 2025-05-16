
from bot.const import GAME_SETTINGS
from bot.modules.managment.events import get_event
from bot.modules.user.premium import premium
from bot.modules.user.rtl_name import check_name
from bot.dbmanager import mongo_client
from bot.exec import bot

from bot.modules.managment.boost_spy import user_boost_channel_status

async def xpboost_percent(userid: int):
    xp_boost = 1

    if await user_boost_channel_status(userid):
        xp_boost += 0.5

    if await premium(userid):
        xp_boost += 0.8

    if event_data := await get_event('xp_boost'):
        xp_boost += event_data['data']['xp_boost']

    if event_data := await get_event('xp_premium_boost'):
        xp_boost += event_data['data']['xp_boost']

    if await check_name(userid):
        xp_boost += 0.2

    # Бустер опыта

    return xp_boost