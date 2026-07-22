from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.modules.user.user import User

class MultiDinoFilter(BaseFilter):
    def __init__(self, is_multi: bool = True) -> None:
        self.is_multi = is_multi

    async def __call__(self, message: Message) -> bool:
        if not message or not message.from_user:
            return False
        user = await User().create(message.from_user.id)
        dinos = await user.get_last_dinos()
        has_multi = len(dinos) > 1
        return has_multi == self.is_multi
