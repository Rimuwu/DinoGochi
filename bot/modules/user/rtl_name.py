
from bot.exec import bot
from aiogram.types import User as teleUser
from bot.const import GAME_SETTINGS

async def check_name(user: teleUser | int):
    """ Проверяет есть ли в нике надпись DinoGochi
    """
    if isinstance(user, int): 
        chat_member = await bot.get_chat_member(user, user)
        if chat_member and hasattr(chat_member, 'user'):
            user = chat_member.user
        else:
            return False

    text = user.full_name.lower()
    for word in GAME_SETTINGS['rtl_name']:
        if word in text:
            return True
    return False