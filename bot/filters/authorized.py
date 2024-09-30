from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.dbmanager import mongo_client

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)

class IsAuthorizedUser(BaseFilter):
    def __init__(self, status: bool = True):
        self.status: bool = status

    async def __call__(self, message: Message) -> bool:
        if message.from_user:
            is_authorized = await users.find_one(
                    { 'userid': message.from_user.id
                    }, {'_id': 1}, comment='authorized_check'
                    ) is not None

            if self.status: result = is_authorized
            else: result = not is_authorized
            return result
        return False