from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.exec import bot



class IsReply(BaseFilter):
    def __init__(self, status: bool = True) -> None:
        self.status: bool = status

    async def __call__(self, message: Message) -> bool:
        me = await bot.get_me()

        reply_status = bool(message.reply_to_message)
        if reply_status:
            to_me = me.id == message.reply_to_message.from_user.id
        else: to_me = False

        status = all(
            [reply_status, to_me]
        )

        if self.status: result = status
        else: result = not status
        return result

