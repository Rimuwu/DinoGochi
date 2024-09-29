from typing import Union
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class IsPrivateChat(BaseFilter):
    key = 'private'

    def __init__(self, var: Union[CallbackQuery, Message], 
                 status: str) -> None:
        self.var: Union[CallbackQuery, Message] = var
        self.status: str = status

    async def __call__(self, message: Message) -> bool:
        is_private = False

        if type(self.var) == CallbackQuery:
            if self.var.message:
                is_private = self.var.message.chat.type == 'private'

        elif type(self.var) == Message:
            if self.var:
                is_private = self.var.chat.type == 'private'

        if self.status: result = is_private
        else: result = not is_private
        return result
