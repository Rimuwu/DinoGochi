from bot.modules.overwriting.DataCalsses import LazyCollection
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.models.user import User


class IsAuthorizedUser(BaseFilter):
    def __init__(self, status: bool = True):
        self.status: bool = status

    async def __call__(self, message: Message) -> bool:
        if message.from_user:
            is_authorized = await User.have_account(message.from_user.id)

            if self.status: result = is_authorized
            else: result = not is_authorized
            return result
        return False