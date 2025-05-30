
from bot.exec import bot
from aiogram.types import User
from bot.const import GAME_SETTINGS
from bot.modules.logs import log

async def check_name(user: User | int):
    """ Проверяет есть ли в нике надпись DinoGochi
    """
    if isinstance(user, (int, float)): 
        chat_member = await bot.get_chat_member(user, user)
        if chat_member and hasattr(chat_member, 'user'):
            user = chat_member.user
        else:
            return False
    
    if isinstance(user, User):
        text = user.full_name.lower()
        for word in GAME_SETTINGS['rtl_name']:
            if word in text:
                return True
    else:
        log(f"В check_name передано {user} {type(user)}", 4)
    return False