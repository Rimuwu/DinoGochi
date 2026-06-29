from typing import Dict, Any, Optional
from beanie import Document

class Group(Document):
    group_id: int
    title: str
    username: Optional[str] = None
    settings: Dict[str, Any]

    class Settings:
        name = "groups"

class GroupMessage(Document):
    group_id: int
    message_id: int
    userid: int
    timestamp: int

    class Settings:
        name = "messages"

class GroupUser(Document):
    user_id: int
    group_id: int
    role: str = "member"

    class Settings:
        name = "group_users"
