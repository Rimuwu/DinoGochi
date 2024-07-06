from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import CallbackQuery

from bot.exec import bot

class NothingState(AdvancedCustomFilter):
    key = 'nothing_state'

    async def check(self, var, status: bool):
        if type(var) == CallbackQuery:
            state = await bot.get_state(var.from_user.id, var.message.chat.id)
        else: # Message
            state = await bot.get_state(var.from_user.id, var.chat.id)

        if not state and status: return True
        elif not state and not status: return False

        elif state and status: return False
        elif state and not status: return True

bot.add_custom_filter(NothingState())