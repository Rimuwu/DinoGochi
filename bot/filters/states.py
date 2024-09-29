from typing import Union
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class NothingState(BaseFilter):
    def __init__(self, var: Union[CallbackQuery, Message], 
                 status: bool) -> None:
        self.var: Union[CallbackQuery, Message] = var
        self.status: bool = status

    async def __call__(self):
        if type(self.var) == CallbackQuery:
            state = self.var.from_user.__getstate__
        else: # Message
            state = self.var.from_user.__getstate__

        if not state and self.status: return True
        elif not state and not self.status: return False

        elif state and self.status: return False
        elif state and not self.status: return True

