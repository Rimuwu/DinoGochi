
import aiohttp
from bot.config import conf
from bot.modules.companies import generate_message, nextinqueue, save_message
from bot.modules.logs import log
from bot.config import mongo_client
import json
from bot.exec import bot
from bot.modules.localization import t, get_lang
from time import time as time_now
from datetime import datetime, timezone

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
ads = DBconstructor(mongo_client.user.ads)

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
    async with aiohttp.ClientSession() as session:

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
    else: log(f'gramads status - {res}', 4)
    return res

async def create_ads_data(user_id:int, limit: int = 7200): 
    ads_cabinet = await ads.find_one({'userid': user_id}, comment='create_ads_data_ads_cabinet')
    if not ads_cabinet:
        data = {
            'userid': user_id,
            'limit': limit,
            'last_ads': 0
        }
        await ads.insert_one(data, comment='create_ads_data')
        return data

    return ads_cabinet

async def check_limit(user_id:int):
    """ Отвечает на впорос: Можно ли отправить рекламу снова, учитывая лимит игрока
    """
    ads_cabinet = await create_ads_data(user_id)

    last = ads_cabinet['last_ads']
    limit = ads_cabinet['limit']
    
    if limit != "inf":
        if int(time_now()) >= last + limit: return True
    return False 

async def save_last_ads(user_id:int):
    ads_cabinet = await create_ads_data(user_id)

    await ads.update_one({'_id': ads_cabinet['_id']}, 
                         {"$set": {'last_ads': int(time_now())}}, comment='save_last_ads')
    await users.update_one({"userid": user_id}, {'$inc': {"super_coins": 1}},
                           comment='save_last_ads')

    lang = await get_lang(user_id)

    try:
        await bot.send_message(user_id, t('super_coins.plus_one', lang), parse_mode="Markdown")
    except:
        await bot.send_message(user_id, t('super_coins.plus_one', lang))


async def auto_ads(message, only_parthner: bool = False):
    user_id = message.from_user.id
    if message.chat.type == "private":
        user = await users.find_one({'userid': user_id}, {"_id": 1}, comment='auto_ads_user')
        print(user)
        if user:
            if conf.show_advert:

                create = user['_id'].generation_time
                now = datetime.now(timezone.utc)
                delta = now - create

                if delta.days >= 4:
                    if await check_limit(user_id):
                        await show_advert_gramads(user_id)

            if only_parthner:
                lang = await get_lang(user_id)
                comp_id = await nextinqueue(user_id, lang)
                print(comp_id)

                if comp_id:
                    m_id = await generate_message(user_id, comp_id, lang)
                    if m_id:
                        await save_message(comp_id, user_id, m_id)