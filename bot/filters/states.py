from typing import Union
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class NothingState(BaseFilter):
    def __init__(self, status: bool = True) -> None:
        self.status: bool = status

    async def __call__(self, var: Union[CallbackQuery, Message]):
        if type(var) == CallbackQuery:
            state = var.from_user.__getstate__

        if type(var) == Message:
            if var.from_user:
                state = var.from_user.__getstate__
            else: return False

        if not state and self.status: return True
        elif not state and not self.status: return False

        elif state and self.status: return False
        elif state and not self.status: return True

