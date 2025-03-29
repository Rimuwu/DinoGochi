
from bot.exec import main_router, bot
from bot.modules.decorators import HDMessage
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from aiogram.types import Message

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.map-bt'), IsAuthorizedUser())
async def map(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    
    await bot.send_message(message.chat.id, t('map.text', lang), reply_markup=await m(userid, 'map_menu', lang))