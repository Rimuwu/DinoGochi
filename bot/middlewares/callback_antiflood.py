import time

from telebot.types import CallbackQuery
from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate
from bot.exec import bot
from bot.modules.localization import get_lang, t
from bot.config import conf

DEFAULT_RATE_LIMIT = 1

class CallbackQueryAntiFloodMiddleware(BaseMiddleware):
    def __init__(self, timeout: float=DEFAULT_RATE_LIMIT):
        super().__init__()
        self.timeout = timeout
        self.update_types = ['callback_query']
        self.last_query = {}

    async def pre_process(self, message: CallbackQuery, data: dict):
        if conf.only_dev and message.from_user.id not in conf.bot_devs:
            lang = await get_lang(message.from_user.id)
            await bot.answer_callback_query(message.id, t('only_dev_mode', lang), 
                                            show_alert=True)
            return CancelUpdate()

        now = time.time()
        if message.from_user.id not in self.last_query:
            self.last_query[message.from_user.id] = now
            await bot.answer_callback_query(message.id)  # always answer callback query
            return
        if now - self.last_query[message.from_user.id] < self.timeout:
            self.last_query[message.from_user.id] = now

            lang = await get_lang(message.from_user.id)
            await bot.answer_callback_query(message.id, 
                            t('timeout_message', lang), show_alert=True)

            return CancelUpdate()
        self.last_query[message.from_user.id] = now
        await bot.answer_callback_query(message.id)  # always answer callback query

    async def post_process(self, message: CallbackQuery, data: dict, exception: BaseException):
        pass

bot.setup_middleware(CallbackQueryAntiFloodMiddleware())