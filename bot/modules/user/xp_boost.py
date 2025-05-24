
from bot.modules.managment.events import get_event
from bot.modules.user.premium import premium
from bot.modules.user.rtl_name import check_name

from bot.modules.managment.boost_spy import base_boost_check

async def xpboost_percent(userid: int):
    """
        Возвращает множитель опыта для пользователя.
        1.0 - обычный опыт
        +0.5 - премиум
        +1.0 - Бустер канала
        +0.2 - РТЛ имя
        +0.1 - 0.2 - событие

        Максимум *2.5
    """
    assert isinstance(userid, int), f'userid must be int, not {type(userid)} {userid}'

    xp_boost = 1

    if await base_boost_check(userid):
        xp_boost += 0.5

    premium_st = await premium(userid)
    if premium_st: xp_boost += 0.5

    if event_data := await get_event('xp_boost'):
        xp_boost += event_data['data']['xp_boost']

    if event_data := await get_event('xp_premium_boost'):
        if premium_st:
            xp_boost += event_data['data']['xp_boost']

    if await check_name(userid):
        xp_boost += 0.2

    # Бустер опыта

    return min(xp_boost, 2.5)