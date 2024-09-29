from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.config import conf

class IsAdminUser(BaseFilter):
    key = 'is_admin'

    async def __call__(self, message: Message, status: bool):
        is_authorized = message.from_user.id in conf.bot_devs

        if status: result = is_authorized
        else: result = not is_authorized
        return result

# bot.add_custom_filter(IsAdminUser())
router = Router()
router.message.filter(IsAdminUser())