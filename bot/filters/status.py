from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.modules.inline import inline_menu
from bot.modules.localization import t
from bot.modules.user.user import User

class DinoPassStatus(BaseFilter):
    key = 'dino_pass'
    
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message):
        if message.from_user:
            user = await User().create(message.from_user.id)
            last_dino = await user.get_last_dino()
            lang = await user.lang

            if last_dino:
                if await last_dino.status == 'pass': return True
                else:
                    await message.answer(t('alredy_busy', lang), reply_markup=inline_menu('dino_profile', lang, 
                            dino_alt_id_markup=last_dino.alt_id))
        return False