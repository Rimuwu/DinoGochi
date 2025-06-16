# Система антифлуда


from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.dbmanager import mongo_client, conf
from time import time as time_now
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.exec import main_router

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

    async def __call__(self, 
                handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
                message: Message,
                data: dict[str, Any]):

        if message.from_user:
            if conf.only_dev and message.from_user.id not in conf.bot_devs:
                if message.chat.type == "private":
                    lang = await get_lang(message.from_user.id)
                    await message.answer(t('only_dev_mode', lang))
                return 

            if message.date.timestamp() + 10 < int(time_now()):
                log(f'message timeout: {message.text} from {message.from_user.id} ping1 {int(time_now() - message.date.timestamp())}', 4, 'middleware')

            # Отмена команды с задержкой в 60+ секунд
            if int(time_now() - message.date.timestamp()) >= 60:
                # log(f'message: {message.text} from {message.from_user.id} ping1 {int(time_now() - message.date)}', 3, 'middlewareCancel')
                return 

            if not message.from_user.id in self.last_time:
                self.last_time[message.from_user.id] = time_now()
                return await handler(message, data)
            if time_now() - self.last_time[message.from_user.id] < self.limit:
                return 
            self.last_time[message.from_user.id] = time_now()
            return await handler(message, data)

main_router.message.middleware(AntifloodMiddleware())