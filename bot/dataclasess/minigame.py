from dataclasses import dataclass, field
from email import message


@dataclass
class SMessage:
    message_id: int
    chat_id: int
    data: dict

@dataclass
class PlayerData:
    user_id: int
    chat_id: int
    user_name: str
    data: dict

@dataclass
class Button:
    function: str
    filters: list[str]
    active: bool

@dataclass
class Waiter:
    function: str
    active: bool
    data: dict

@dataclass
class Thread:
    repeat: int
    col_repeat: int | str
    function: str
    last_start: int
    active: bool

@dataclass
class Stage:
    threads_active: list[dict]
    buttons_active: list[dict]
    waiter_active: list[dict]
    stage_generator: str
    to_function: str
    data: dict