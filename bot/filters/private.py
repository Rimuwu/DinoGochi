from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class IsPrivateChat(BaseFilter):
    key = 'private'

    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message, var, status: bool) -> bool:
        if type(var) == CallbackQuery:
            is_private = var.message.chat.type == 'private'
        else: # Message
            is_private = var.chat.type == 'private'

        if status: result = is_private
        else: result = not is_private
        return result

router = Router()
router.message.filter(IsPrivateChat())