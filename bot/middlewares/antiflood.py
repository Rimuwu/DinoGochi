# Система антифлуда


from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate
from telebot.types import Message
from bot.exec import bot
from bot.dbmanager import mongo_client, conf
from time import time as time_now
from bot.modules.localization import get_lang, t
from bot.modules.logs import log

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
            # log(f'message: {message.text} from {message.from_user.id} ping1 {int(time_now() - message.date)}', 3, 'middlewareCancel')
            return CancelUpdate()

        if not message.from_user.id in self.last_time:
            self.last_time[message.from_user.id] = time_now()
            return 
        if time_now() - self.last_time[message.from_user.id] < self.limit:
            return CancelUpdate()
        self.last_time[message.from_user.id] = time_now()
        return

    async def post_process(self, message: Message, data: dict, exception: BaseException):
        pass

bot.setup_middleware(AntifloodMiddleware())