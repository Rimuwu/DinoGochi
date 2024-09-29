# Фильтр текста на выбранном языке

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.exec import bot
from bot.modules.localization import t, get_lang

class IsEqual(BaseFilter):
    def __init__(self, key: str) -> None:
        self.key: str = key

    async def __call__(self, message: Message):
        if message.from_user:
            if isinstance(message.from_user.language_code, str):
                lang_n = message.from_user.language_code
            else: lang_n = 'en'

            lang = await get_lang(message.from_user.id, lang_n)
            text = t(self.key, lang)

            if text == message.text: return True
        return False

class StartWith(BaseFilter):
    def __init__(self, key: str) -> None:
        self.key: str = key

    async def __call__(self, message: Message):
        if message.from_user:
            if isinstance(message.from_user.language_code, str):
                lang_n = message.from_user.language_code
            else: lang_n = 'en'

            lang = await get_lang(message.from_user.id, lang_n)
            text = t(self.key, lang, False)

            if isinstance(message.text, str):
                if message.text.startswith(text): return True
        return False
