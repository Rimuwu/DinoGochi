# Система антифлуда

from telebot.asyncio_handler_backends import BaseMiddleware, SkipHandler
from telebot.types import Message
from bot.exec import bot
from bot.config import mongo_client, conf
from time import time as time_now
from bot.modules.advert import show_advert

DEFAULT_RATE_LIMIT = 0.2
users = mongo_client.user.users

class AntifloodMiddleware(BaseMiddleware):
    throttle_dict = {}

    def __init__(self, limit=DEFAULT_RATE_LIMIT):
        self.last_time = {}
        self.limit = limit
        self.update_types = ['message', 'callback_query']

    async def pre_process(self, message: Message, data: dict):

        if not message.from_user.id in self.last_time:
            self.last_time[message.from_user.id] = time_now()
            return
        if time_now() - self.last_time[message.from_user.id] < self.limit:
            return SkipHandler()
        self.last_time[message.from_user.id] = time_now()

    async def post_process(self, message, data, exception):
        await users.update_one({'userid': message.from_user.id}, {'$set': {'last_message_time': message.date}})
        if conf.show_advert: await show_advert(message.from_user.id)


bot.setup_middleware(AntifloodMiddleware())