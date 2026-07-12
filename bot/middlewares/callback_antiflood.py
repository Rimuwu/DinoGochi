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

        token = None
        if message.from_user:
            try:
                from bot.modules.localization import get_rare_emoji, current_rare_emoji
                rare_emoji_val = await get_rare_emoji(message.from_user.id)
                token = current_rare_emoji.set(rare_emoji_val)
            except Exception:
                pass

            if conf.bot_devs and message.from_user.id == conf.bot_devs[0]:
                from bot.modules.localization import owner_premium_cache
                owner_premium_cache["is_premium"] = bool(message.from_user.is_premium)
                owner_premium_cache["last_check"] = time.time()

        if conf.only_dev and message.from_user.id not in conf.bot_devs:
            lang = await get_lang(message.from_user.id)
            await message.answer(t('only_dev_mode', lang), True)
            return 

        try:
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
        finally:
            if token:
                try:
                    from bot.modules.localization import current_rare_emoji
                    current_rare_emoji.reset(token)
                except Exception:
                    pass

main_router.callback_query.middleware(CallbackQueryAntiFloodMiddleware())