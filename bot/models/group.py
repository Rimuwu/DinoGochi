from typing import Dict, Any, Optional
from beanie import Document
from pydantic import Field

class Group(Document):
    group_id: Optional[int] = None
    title: str = ""
    username: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "groups"

class GroupMessage(Document):
    group_id: Optional[int] = None
    message_id: Optional[int] = None
    userid: Optional[int] = None
    timestamp: int = 0

    class Settings:
        name = "messages"

class GroupUser(Document):
    user_id: Optional[int] = None
    group_id: Optional[int] = None
    role: str = "member"

    class Settings:
        name = "group_users"
