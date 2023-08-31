#Активация встроенных фильтров
from telebot.asyncio_filters import StateFilter, IsDigitFilter

from bot.exec import bot

bot.add_custom_filter(StateFilter(bot))
bot.add_custom_filter(IsDigitFilter())