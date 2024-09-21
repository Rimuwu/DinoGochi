# Система антифлуда

from random import randint, random
from telebot.asyncio_handler_backends import BaseMiddleware
from telebot.types import Message
from bot.exec import bot
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

    def __init__(self):
        self.update_types = ['message']

    async def pre_process(self, message: Message, data: dict):
        pass

    async def post_process(self, message: Message, data, exception):
        user_id = message.from_user.id
        if message.chat.type == "private":
            user = await users.find_one({'userid': user_id}, {"_id": 1, 
                                         "settings": 1, 'notifications': 1}, 
                                        comment='post_process_user')
            if user:
                await users.update_one({'userid': user_id}, 
                                    {'$set': {'last_message_time': message.date}}, 
                                    comment='post_process_1')

                daily = await daily_data.find_one({'owner_id': user_id}, comment='post_process_check')
                last_ads_time = await check_ads(user_id)
                send = False

                if daily == None and last_ads_time >= 10:
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

                if last_ads_time >= 10 and not send:
                    # Рекламные сообщения
                    if random() <= 0.5:
                        await auto_ads(message, True)


bot.setup_middleware(PassWorker())