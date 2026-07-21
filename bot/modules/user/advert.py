from bot.models.user import Ad
from bot.models.user import User

from calendar import c
import aiohttp
from bot.config import conf
from bot.modules.companies import generate_message, nextinqueue, priority_and_timeout
from bot.modules.logs import log
from bot.dbmanager import mongo_client
import json
from bot.exec import bot
from bot.modules.localization import t, get_lang
from time import time as time_now
from datetime import datetime, timezone

from bot.modules.get_state import get_state

async def show_advert_gramads(user_id: int):
    """ Показ рекламы через площадку gramads.net

    Undefined = 0
    Success = 1
    RevokedTokenError = 2
    UserForbiddenError = 3
    ToManyRequestsError = 4
    OtherBotApiError = 5
    OtherError = 6

    AdLimited = 7
    NoAds = 8
    BotIsNotEnabled = 9
    Banned = 10
    InReview = 11
    """

    res = 6
    if conf.advert_token:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:

            async with session.post(
                'https://api.gramads.net/ad/SendPost',
                headers={
                    'Authorization': conf.advert_token,
                    'Content-Type': 'application/json',
                },
                json={'SendToChatId': user_id},
            ) as response:
                data = json.loads(await response.read())
                res = data['SendPostResult']

                if not response.ok:
                    log('Gramads: %s' % str(await response.json()), 2)

        if res == 1: await save_last_ads(user_id)
        else: 
            if res not in [8, 7]:
                log(f'gramads status - {res}', 4)
    return res

async def create_ads_data(user_id:int, limit: int = 7200): 
    ads_cabinet = await Ad.find_one(Ad.userid == user_id)
    if not ads_cabinet:
        ads_cabinet = Ad(
            userid=user_id,
            limit=limit,
            last_ads=0
        )
        await ads_cabinet.insert()
    return ads_cabinet

async def check_limit(user_id:int):
    """ Отвечает на впорос: Можно ли отправить рекламу снова, учитывая лимит игрока
    """
    ads_cabinet = await create_ads_data(user_id)

    last = ads_cabinet.last_ads
    limit = ads_cabinet.limit

    if limit != "inf":
        if int(time_now()) >= last + limit: return True
    return False 

async def save_last_ads(user_id:int):
    ads_cabinet = await create_ads_data(user_id)

    await ads_cabinet.set_last_ads(int(time_now()))

    user = await User.find_one(User.userid == user_id)
    if user:
        await user.add_super_coins(1)
    log(f"Edit super_coins: user: {user_id} col: 1", 1, "save_last_ads")

    lang = await get_lang(user_id)

    try:
        await bot.send_message(user_id, t('super_coins.plus_one', lang))
    except:
        await bot.send_message(user_id, t('super_coins.plus_one', lang))


async def auto_ads(message, only_parthner: bool = False):
    user_id = message.from_user.id
    if message.chat.type == "private":
        user = await User.find_one(User.userid == user_id)
        if user:
            if only_parthner:
                lang = await get_lang(user_id)
                comp_id = await nextinqueue(user_id, lang)
                lim = await check_limit(user_id)

                create = user.id.generation_time
                now = datetime.now(timezone.utc)
                delta = now - create

                if comp_id and delta.days >= 1:
                    priory, ign_timeout = await priority_and_timeout(comp_id)

                    if ign_timeout or lim:
                        state = await get_state(user_id, message.chat.id)
                        if not await state.get_state():
                            await generate_message(user_id, comp_id, lang)

            elif conf.show_advert:
                grm = False
                sen_c = False

                create = user.id.generation_time
                now = datetime.now(timezone.utc)
                delta = now - create

                lim = await check_limit(user_id)
                comp_id = await nextinqueue(user_id)
                if comp_id:
                    priory, ign_timeout = await priority_and_timeout(comp_id)

                    # Проверяем приоритет компании
                    if comp_id and priory:
                        if ign_timeout or lim:
                            await generate_message(user_id, comp_id)
                            sen_c = True

                # Если не в приоритете пытаемся отослать рекламу
                if delta.days >= 4 and not sen_c:
                    if lim:
                        r = await show_advert_gramads(user_id)
                        if r == 1: grm = True

                # Если реклама не сработала
                if not grm and comp_id and not sen_c:
                    if ign_timeout or lim:
                        await generate_message(user_id, comp_id)
                        sen_c = True