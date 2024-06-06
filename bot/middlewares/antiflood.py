# Система антифлуда

from telebot.asyncio_handler_backends import BaseMiddleware, SkipHandler
from telebot.types import Message
from bot.exec import bot
from bot.config import mongo_client
from time import time as time_now
from bot.modules.notifications import user_notification
from bot.modules.logs import log
import requests

DEFAULT_RATE_LIMIT = 0.5
users = mongo_client.user.users
daily_data = mongo_client.tavern.daily_award


async def ping():
    st = time_now()
    r = requests.post('https://api.telegram.org')
    dt = round(time_now() - st, 3)
    return dt

class AntifloodMiddleware(BaseMiddleware):

    def __init__(self, limit=DEFAULT_RATE_LIMIT):
        self.last_time = {}
        self.limit = limit
        self.update_types = ['message']

    async def pre_process(self, message: Message, data: dict):
        if message.date < int(time_now()):
            log(f'message timeout: {message.text} from {message.from_user.id} ping1 {int(time_now() - message.date)} ping2 {await ping()}ms', 4, 'middleware')

        if not message.from_user.id in self.last_time:
            self.last_time[message.from_user.id] = time_now()
            return 
        if time_now() - self.last_time[message.from_user.id] < self.limit:
            return SkipHandler()
        self.last_time[message.from_user.id] = time_now()
        return

    async def post_process(self, message: Message, data, exception):
        user_id = message.from_user.id
        if message.chat.type == "private":
            user = await users.find_one({'userid': user_id}, {"_id": 1, 
                                                    "settings": 1, 'notifications': 1})
            if user:
                await users.update_one({'userid': user_id}, 
                                    {'$set': {'last_message_time': message.date}})

                if await daily_data.find_one({'owner_id': user_id}) == None:
                    if user['settings']['notifications']:
                        for key, value in user['notifications'].items():

                            if key == 'daily_award' and \
                                value + 8 * 3600 > int(time_now()):
                                break
                        else:
                            res = await user_notification(user_id, 'daily_award')

                            if res:
                                await users.update_one({'userid': user_id}, 
                                    {'$set': {'notifications.daily_award': int(time_now())}})


bot.setup_middleware(AntifloodMiddleware())