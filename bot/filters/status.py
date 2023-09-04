from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import Message

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.inline import inline_menu
from bot.modules.localization import t
from bot.modules.user import User

users = mongo_client.user.users

class DinoPassStatus(AdvancedCustomFilter):
    key = 'dino_pass'

    async def check(self, message: Message, status: bool):
        user = User(message.from_user.id)
        last_dino = user.get_last_dino()

        chatid = message.chat.id
        lang = user.lang

        if last_dino:
            if last_dino.status == 'pass': return True
            else:
                await send_message(chatid, t('alredy_busy', lang),
                        reply_markup=inline_menu('dino_profile', lang, 
                        dino_alt_id_markup=last_dino.alt_id))
        return False

bot.add_custom_filter(DinoPassStatus())