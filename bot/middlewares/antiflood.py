# Система антифлуда

from random import randint
from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate
from telebot.types import Message
from bot.exec import bot
from bot.config import mongo_client, conf
from time import time as time_now
from bot.modules.localization import get_lang, t
from bot.modules.notifications import user_notification
from bot.modules.logs import log

from bot.modules.user.advert import auto_ads

DEFAULT_RATE_LIMIT = 0.5

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
daily_data = DBconstructor(mongo_client.tavern.daily_award)
ads = DBconstructor(mongo_client.user.ads)

async def check_ads(user_id):
    ads_cabinet = await ads.find_one({'userid': user_id}, comment='check_ads_midl')

    if ads_cabinet is None: return 1000
    else: return int(time_now() - ads_cabinet['last_ads'])


class AntifloodMiddleware(BaseMiddleware):

    def __init__(self, limit=DEFAULT_RATE_LIMIT):
        self.last_time = {}
        self.limit = limit
        self.update_types = ['message']

    async def pre_process(self, message: Message, data: dict):
        if conf.only_dev and message.from_user.id not in conf.bot_devs:
            if message.chat.type == "private":
                lang = await get_lang(message.from_user.id)
                await bot.send_message(message.chat.id, t('only_dev_mode', lang))
            return CancelUpdate()

        if message.date + 10 < int(time_now()):
            log(f'message timeout: {message.text} from {message.from_user.id} ping1 {int(time_now() - message.date)}', 4, 'middleware')

        # Отмена команды с задержкой в 60+ секунд
        if int(time_now() - message.date) >= 60:
            log(f'message: {message.text} from {message.from_user.id} ping1 {int(time_now() - message.date)}', 3, 'middlewareCancel')
            return CancelUpdate()

        if not message.from_user.id in self.last_time:
            self.last_time[message.from_user.id] = time_now()
            return 
        if time_now() - self.last_time[message.from_user.id] < self.limit:
            return CancelUpdate()
        self.last_time[message.from_user.id] = time_now()
        return

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
                    if randint(1, 4) == 4:
                        await auto_ads(message, True)


bot.setup_middleware(AntifloodMiddleware())