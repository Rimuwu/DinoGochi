
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from bot.config import conf
from bot.modules.user.user import user_in_chat

class IsGroupAdmin(BaseFilter):
    def __init__(self, status: bool = True):
        self.status: bool = status

    async def __call__(self, var: Message | CallbackQuery):

        if isinstance(var, CallbackQuery): 
            message = var.message
            from_user = var.from_user
        else:
            message = var
            from_user = message.from_user

        if from_user:
            user_status = await user_in_chat(from_user.id, message.chat.id)
            is_group_admin = user_status in ['admin', 'creator']

            if self.status: result = is_group_admin
            else: result = not is_group_admin
            return result
        return False
