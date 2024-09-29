from typing import Union
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class IsPrivateChat(BaseFilter):
    def __init__(self, status: bool) -> None:
        self.status: bool = status

    async def __call__(self, var: Union[CallbackQuery, Message]) -> bool:
        is_private = False

        if type(var) == CallbackQuery:
            if var.message:
                is_private = var.message.chat.type == 'private'

        elif type(var) == Message:
            if var:
                is_private = var.chat.type == 'private'

        if self.status: result = is_private
        else: result = not is_private
        return result
