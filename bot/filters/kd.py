from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import CallbackQuery

from bot.exec import bot
from bot.modules.data_format import seconds_to_str
from bot.modules.dinosaur.kd_activity import check_activity
from bot.modules.localization import t
from bot.modules.user.user import User
from bot.modules.markup import markups_menu as m

class KDCheck(AdvancedCustomFilter):
    key = 'kd_check'

    async def check(self, var, activity: str):
        chatid = var.chat.id
        user = await User().create(var.from_user.id)
        lang = await user.lang
        last_dino = await user.get_last_dino()

        sec_col = await check_activity(last_dino._id, activity)
        if sec_col:
            text = t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))

            await bot.send_message(chatid, text, reply_markup=await m(user.userid, 'speed_actions_menu', lang, True))
            return False
        return True

bot.add_custom_filter(KDCheck())