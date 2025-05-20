from random import random
from typing import Awaitable, Callable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.exec import main_router, bot
from bot.dbmanager import mongo_client
from time import time as time_now
from bot.middlewares.antiflood import check_ads
from bot.modules.notifications import user_notification

from bot.modules.user.advert import auto_ads

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
daily_data = DBconstructor(mongo_client.tavern.daily_award)
ads = DBconstructor(mongo_client.user.ads)

class PassWorker(BaseMiddleware):

    async def __call__(self, 
                handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
                message: Message,
                data: dict[str, Any]):

        result = await handler(message, data)
        await self.post_process(message, data)
        return result

    async def post_process(self, message: Message, data):
        user_id = message.from_user.id
        if message.chat.type == "private":
            user = await users.find_one({'userid': user_id}, {"_id": 1, 
                                         "settings": 1, 'notifications': 1}, 
                                        comment = 'post_process_user')
            if user:
                await users.update_one({'userid': user_id}, 
                                    {'$set': {'last_message_time': 
                                        int(message.date.timestamp())}}, 
                                    comment = 'post_process_1')

                daily = await daily_data.find_one({'owner_id': user_id}, 
                                                  comment = 'post_process_check')
                last_ads_time = await check_ads(user_id)
                send = False

                if user['_id'].generation_time.days <= 1:
                    pass

                elif daily == None and last_ads_time >= 10:
                    if user['settings']['notifications']:
                        for key, value in user['notifications'].items():

                            if key == 'daily_award' and \
                                value + 8 * 3600 > int(time_now()):
                                break
                        else:
                            res = await user_notification(user_id, 'daily_award')
                            send = True

                            if res:
                                await users.update_one({'userid': user_id}, 
                                    {'$set': {'notifications.daily_award': int(time_now())}}, 
                                    comment='post_process_2')

                elif last_ads_time >= 10 and not send:
                    # Рекламные сообщения
                    await auto_ads(message, True)

main_router.message.middleware(PassWorker())