from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import Message

from bot.config import conf
from bot.exec import bot

class IsAdminUser(AdvancedCustomFilter):
    key = 'is_admin'

    async def check(self, message: Message, status: bool):
        is_authorized = message.from_user.id in conf.bot_devs
        
        if status: result = is_authorized
        else: result = not is_authorized
        return result

bot.add_custom_filter(IsAdminUser())