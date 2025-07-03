# Этап выбора яйца

from bot.filters.private import IsPrivateChat
from bot.filters.translated_text import Text
from bot.modules.decorators import HDMessage
from bot.exec import bot, main_router
from aiogram.types import Message

# @HDMessage
# @main_router.message(IsPrivateChat(), 
#                      Text('commands_name.backgrounds.custom_profile')
#                      )
# async def custom_profile(message: Message):
#     userid = message.from_user.id
