
import aiohttp
from bot.config import conf
from bot.modules.user import premium
from bot.modules.logs import log

async def show_advert(user_id: int):
    print(user_id, "ads")
    if not await premium(user_id):
        async with aiohttp.ClientSession() as session:

            async with session.post(
                'https://api.gramads.net/ad/SendPost',
                headers={
                    'Authorization': conf.advert_token,
                    'Content-Type': 'application/json',
                },
                json={'SendToChatId': user_id},
            ) as response:

                if not response.ok:
                    log('Gramads: %s' % str(await response.json()), 2)

