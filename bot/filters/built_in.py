#Активация встроенных фильтров

from aiogram.filters import BaseFilter
from aiogram.types import Message   

class IsDigitFilter(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        return message.text.isdigit() # type: ignore
