from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import Message

from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.inline import inline_menu
from bot.modules.localization import t
from bot.modules.user.user import User

class DinoPassStatus(AdvancedCustomFilter):
    key = 'dino_pass'

    async def check(self, message: Message, status: bool):
        user = await User().create(message.from_user.id)
        last_dino = await user.get_last_dino()

        chatid = message.chat.id
        lang = await user.lang

        if last_dino:
            if await last_dino.status == 'pass': return True
            else:
                await bot.send_message(chatid, t('alredy_busy', lang),
                        reply_markup=inline_menu('dino_profile', lang, 
                        dino_alt_id_markup=last_dino.alt_id))
        return False

bot.add_custom_filter(DinoPassStatus())