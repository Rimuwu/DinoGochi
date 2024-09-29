from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.modules.data_format import seconds_to_str
from bot.modules.dinosaur.kd_activity import check_activity
from bot.modules.localization import t
from bot.modules.user.user import User
from bot.modules.markup import markups_menu as m

class KDCheck(BaseFilter):
    def __init__(self, activity: str) -> None:
        self.activity: str = activity

    async def __call__(self, var: Message) -> bool:
        user = await User().create(var.from_user.id)
        lang = await user.lang
        last_dino = await user.get_last_dino()

        sec_col = await check_activity(last_dino._id, self.activity)
        if sec_col:
            text = t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))
            await var.answer(text, reply_markup=await m(user.userid, 'last_menu', lang))
            return False
        return True
