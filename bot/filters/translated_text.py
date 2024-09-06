# Фильтр текста на выбранном языке

from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import Message
from bot.exec import bot
from bot.modules.localization import t, get_lang

class IsEqual(AdvancedCustomFilter):
    key = 'text'

    async def check(self, message: Message, key: str):
        lang = await get_lang(message.from_user.id, message.from_user.language_code)
        text = t(key, lang)

        if text == message.text:
            return True
        else:
            return False

class StartWith(AdvancedCustomFilter):
    key = 'textstart'

    async def check(self, message: Message, key: str):
        lang = await get_lang(message.from_user.id, message.from_user.language_code)
        text = t(key, lang, False)

        if text == message.text.startswith(text):
            return True
        else:
            return False

bot.add_custom_filter(IsEqual())
bot.add_custom_filter(StartWith())