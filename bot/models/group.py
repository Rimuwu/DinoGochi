from typing import Optional
from beanie import Document, Link
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User

class Group(PrivateModelMixin, Document):
    group_id: Optional[int] = None
    topic_link: int = 0
    topic_incorrect_message: bool = True
    delete_message: int = 0

    class Settings:
        name = "groups"

    async def set_delete_message(self, seconds: int) -> None:
        self.delete_message = seconds
        await self.save()

    async def set_topic_link(self, topic_id: int) -> None:
        self.topic_link = topic_id
        await self.save()

    async def set_topic_incorrect_message(self, status: bool) -> None:
        self.topic_incorrect_message = status
        await self.save()


class GroupMessage(PrivateModelMixin, Document):
    group_id: Optional[int] = None
    message_id: Optional[int] = None
    user: Optional[Link[User]] = None
    timestamp: int = 0
    time_sended: int = 0

    class Settings:
        name = "messages"

    async def set_time_sended(self, timestamp: int) -> None:
        self.time_sended = timestamp
        await self.save()


class GroupUser(PrivateModelMixin, Document):
    user: Optional[Link[User]] = None
    group_id: Optional[int] = None
    games_count: int = 0

    class Settings:
        name = "group_users"

    async def increment_games(self, count: int = 1) -> None:
        self.games_count += count
        await self.save()
