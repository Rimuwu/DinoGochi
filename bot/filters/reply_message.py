from aiogram.filters import BaseFilter
from aiogram.types import Message

class IsReply(BaseFilter):
    def __init__(self, status: bool = True) -> None:
        self.reply_status: bool = status

    async def __call__(self, message: Message) -> bool:
        reply_status = bool(message.reply_to_message)

        if self.reply_status: result = reply_status
        else: result = not reply_status
        return result

