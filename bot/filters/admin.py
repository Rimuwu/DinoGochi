from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.config import conf

class IsAdminUser(BaseFilter):
    def __await__(self, status: bool):
        self.status: bool = status

    async def __call__(self, message: Message):
        is_authorized = message.from_user.id in conf.bot_devs

        if self.status: result = is_authorized
        else: result = not is_authorized
        return result
