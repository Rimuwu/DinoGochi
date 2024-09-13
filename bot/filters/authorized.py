from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import Message

from bot.dbmanager import mongo_client
from bot.exec import bot

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)

class IsAuthorizedUser(AdvancedCustomFilter):
    key = 'is_authorized'

    async def check(self, message: Message, status: bool):
        is_authorized = await users.find_one(
                { 'userid': message.from_user.id
                }, {'_id': 1}, comment='authorized_check'
                ) is not None

        if status: result = is_authorized
        else: result = not is_authorized
        return result

bot.add_custom_filter(IsAuthorizedUser())