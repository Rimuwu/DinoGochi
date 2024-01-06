# Система антифлуда

from telebot.asyncio_handler_backends import BaseMiddleware, SkipHandler
from telebot.types import Message
from bot.exec import bot
from bot.config import mongo_client, conf
from time import time as time_now
from bot.modules.advert import show_advert
from datetime import datetime, timezone
from bot.modules.user import premium

DEFAULT_RATE_LIMIT = 0.2
users = mongo_client.user.users

class AntifloodMiddleware(BaseMiddleware):

    def __init__(self, limit=DEFAULT_RATE_LIMIT):
        self.last_time = {}
        self.last_ads = {}
        self.limit = limit
        self.update_types = ['message']

    async def pre_process(self, message: Message, data: dict):

        if not message.from_user.id in self.last_time:
            self.last_time[message.from_user.id] = time_now()
            return
        if time_now() - self.last_time[message.from_user.id] < self.limit:
            return SkipHandler()
        self.last_time[message.from_user.id] = time_now()

    async def post_process(self, message: Message, data, exception):
        if message.chat.type == "private":
            user = await users.find_one({'userid': message.from_user.id}, {"_id": 1})
            if user:
                await users.update_one({'userid': message.from_user.id}, 
                                    {'$set': {'last_message_time': message.date}})
                if conf.show_advert:

                    create = user['_id'].generation_time
                    now = datetime.now(timezone.utc)
                    delta = now - create

                    if delta.days >= 14:

                        if message.from_user.id in self.last_ads.keys():
                            if int(time_now()) - self.last_ads[message.from_user.id] >= 7_200:
                                self.last_ads[message.from_user.id] = int(time_now())
                            else: return
                        else:
                            self.last_ads[message.from_user.id] = int(time_now())

                        if not await premium(message.from_user.id):
                            await show_advert(message.from_user.id)


bot.setup_middleware(AntifloodMiddleware())  