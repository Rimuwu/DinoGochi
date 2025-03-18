import time
from typing import Awaitable, Callable, Any

from aiogram.types import CallbackQuery
from aiogram import BaseMiddleware
from bot.exec import main_router, bot
from bot.modules.localization import get_lang, t
from bot.config import conf

DEFAULT_RATE_LIMIT = 0.5

class CallbackQueryAntiFloodMiddleware(BaseMiddleware):
    def __init__(self, timeout: float=DEFAULT_RATE_LIMIT):
        super().__init__()
        self.timeout = timeout
        self.last_query = {}

    async def __call__(self, 
                handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
                message: CallbackQuery,
                data: dict[str, Any]):
        if conf.only_dev and message.from_user.id not in conf.bot_devs:
            lang = await get_lang(message.from_user.id)
            await message.answer(t('only_dev_mode', lang), True)
            return 

        now = time.time()
        if message.from_user.id not in self.last_query:
            self.last_query[message.from_user.id] = now
            # await message.answer()  # always answer callback query
            return await handler(message, data)

        if now - self.last_query[message.from_user.id] < self.timeout:
            self.last_query[message.from_user.id] = now

            lang = await get_lang(message.from_user.id)
            await message.answer(t('timeout_message', lang), True)
            return 

        self.last_query[message.from_user.id] = now
        # await message.answer()  # always answer callback query
        return await handler(message, data)

main_router.callback_query.middleware(CallbackQueryAntiFloodMiddleware())