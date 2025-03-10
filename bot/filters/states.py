from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

class NothingState(BaseFilter):
    def __init__(self, status: bool = True, state: FSMContext | None = None) -> None:
        self.status: bool = status
        self.state: FSMContext | None = state

    async def __call__(self, var: Union[CallbackQuery, Message]):
        if self.state is None: return True

        if not self.state and self.status: return True
        elif not self.state and not self.status: return False

        elif self.state and self.status: return False
        elif self.state and not self.status: return True

