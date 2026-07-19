from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import Ad
from bot.models.user import User
from bot.models.tavern import DailyAward
# Система антифлуда


from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.dbmanager import mongo_client, conf
from time import time as time_now
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.exec import main_router, bot

DEFAULT_RATE_LIMIT = 0.2

async def check_ads(user_id):
    ads = LazyCollection(Ad)
    ads_cabinet = await ads.find_one({'userid': user_id}, comment='check_ads_midl')

    if ads_cabinet is None:
        return 1000

    last_ads = ads_cabinet['last_ads'] if isinstance(ads_cabinet, dict) else ads_cabinet.last_ads
    return int(time_now() - last_ads)

class AntifloodMiddleware(BaseMiddleware):

    def __init__(self, limit=DEFAULT_RATE_LIMIT):
        self.last_time = {}
        self.limit = limit
        self.update_types = ['message']

    async def __call__(self, 
                handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
                message: Message,
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
                owner_premium_cache["last_check"] = time_now()

            if conf.only_dev and message.from_user.id not in conf.bot_devs:
                if message.from_user.is_bot or message.pinned_message:
                    return await handler(message, data)
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

        try:
            if message.from_user:
                if not message.from_user.id in self.last_time:
                    self.last_time[message.from_user.id] = time_now()
                    return await handler(message, data)
                if time_now() - self.last_time[message.from_user.id] < self.limit:
                    return 
                self.last_time[message.from_user.id] = time_now()
            return await handler(message, data)
        finally:
            if token:
                try:
                    from bot.modules.localization import current_rare_emoji
                    current_rare_emoji.reset(token)
                except Exception:
                    pass

main_router.message.middleware(AntifloodMiddleware())
