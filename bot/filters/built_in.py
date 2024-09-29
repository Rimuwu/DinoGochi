#Активация встроенных фильтров
from aiogram import Router
from aiogram.filters import StateFilter, BaseFilter
from aiogram.types import Message   
from bot.exec import bot


class IsDigitFilter(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        return message.text.isdigit() # type: ignore


router = Router()
router.message.filter(IsDigitFilter())
router.message.filter(StateFilter())