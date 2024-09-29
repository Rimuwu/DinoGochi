# Фильтр текста на выбранном языке

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.exec import bot
from bot.modules.localization import t, get_lang

class IsEqual(BaseFilter):
    key = 'text'

    def __init__(self, key: str) -> None:
        self.key: str = key

    async def __call__(self, message: Message):
        lang = await get_lang(message.from_user.id, 
                              message.from_user.language_code)
        text = t(self.key, lang)

        if text == message.text:
            return True
        else:
            return False

class StartWith(BaseFilter):
    key = 'textstart'

    def __init__(self, key: str) -> None:
        self.key: str = key

    async def __call__(self, message: Message):
        lang = await get_lang(message.from_user.id, 
                              message.from_user.language_code)
        text = t(self.key, lang, False)

        if message.text.startswith(text):
            return True
        else:
            return False
