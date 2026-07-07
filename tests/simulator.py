import asyncio
import time
from typing import List, Optional, Union
from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, CallbackQuery, Chat, User as TGUser
from aiogram.methods import SendMessage, SendPhoto, EditMessageText, EditMessageMedia, EditMessageCaption

class BotSimulator:
    """
    A simulator helper to mock client-side updates (messages, button clicks)
    and check responses sent by the bot.
    """
    def __init__(self, dp: Dispatcher, bot: Bot, user_id: int = 123456789, username: str = "testuser"):
        self.dp = dp
        self.bot = bot
        self.user_id = user_id
        self.username = username
        self.chat = Chat(id=user_id, type="private")
        self.tg_user = TGUser(
            id=user_id,
            is_bot=False,
            first_name="Test",
            last_name="User",
            username=username,
            language_code="ru"
        )
        self.update_id = 1000

    async def send_message(self, text: str) -> Message:
        """Simulates sending a text message or command from the user to the bot."""
        self.update_id += 1
        message = Message(
            message_id=self.update_id,
            date=int(time.time()),
            chat=self.chat,
            from_user=self.tg_user,
            text=text
        )
        update = Update(update_id=self.update_id, message=message)
        await self.dp.feed_update(self.bot, update)
        return message

    async def click_callback(self, data: str, message_id: int = 999) -> CallbackQuery:
        """Simulates clicking an inline keyboard button (CallbackQuery)."""
        self.update_id += 1
        cb_message = Message(
            message_id=message_id,
            date=int(time.time()),
            chat=self.chat,
            from_user=self.tg_user,
            text="[Inline Menu Message]"
        )
        callback_query = CallbackQuery(
            id=str(self.update_id),
            from_user=self.tg_user,
            chat_instance="1",
            message=cb_message,
            data=data
        )
        update = Update(update_id=self.update_id, callback_query=callback_query)
        await self.dp.feed_update(self.bot, update)
        return callback_query

    def get_sent_requests(self) -> List:
        """Returns all outgoing API requests recorded on the mock bot."""
        return getattr(self.bot, "sent_requests", [])

    def clear_sent_requests(self):
        """Clears the history of outgoing API requests."""
        if hasattr(self.bot, "sent_requests"):
            self.bot.sent_requests.clear()

    def get_last_message_text(self) -> Optional[str]:
        """Helper to get the text or caption of the last sent message or photo."""
        requests = self.get_sent_requests()
        if not requests:
            return None
        last = requests[-1]
        if isinstance(last, SendMessage):
            return last.text
        elif isinstance(last, SendPhoto):
            return last.caption
        elif isinstance(last, EditMessageText):
            return last.text
        elif isinstance(last, EditMessageCaption):
            return last.caption
        elif isinstance(last, EditMessageMedia):
            return last.media.caption
        return None

    def get_last_reply_markup(self):
        """Helper to retrieve the reply markup of the last sent message."""
        requests = self.get_sent_requests()
        if not requests:
            return None
        last = requests[-1]
        return getattr(last, "reply_markup", None)
