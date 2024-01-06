
import aiohttp
from bot.config import conf
from bot.modules.logs import log
from bot.config import mongo_client
import json
from bot.exec import bot
from bot.modules.localization import t, get_lang

users = mongo_client.user.users

async def show_advert(user_id: int):
    """ Показ рекламы через площадку gramads.net

    Undefined = 0,
    Success = 1,
    RevokedTokenError = 2,
    UserForbiddenError = 3,
    ToManyRequestsError = 4,
    OtherBotApiError = 5,
    OtherError = 6,

    AdLimited = 7,
    NoAds = 8,
    BotIsNotEnabled=9,
    Banned=10,
    InReview=11
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

    if res == 1:
        await users.update_one({"userid": user_id}, {'$inc': {"super_coins": 1}})

        lang = await get_lang(user_id)
        await bot.send_message(user_id, t('super_coins.plus_one', lang), parse_mode="Markdown")

    return res

