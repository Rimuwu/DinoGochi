from dataclasses import dataclass, field
from email import message
from email.mime import image
from typing import Optional


@dataclass
class SMessage:
    message_id: int
    chat_id: int
    data: dict
    parse_mode: Optional[str]
    image: Optional[str] = field(default=None)
    last_update: Optional[float] = field(default=0.0)

@dataclass
class PlayerData:
    user_id: int
    chat_id: int
    user_name: str
    data: dict
    stage: str

@dataclass
class Button:
    filters: list[str]
    active: bool
    function: str = field(default='')
    stage: str = field(default='')

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
    last_start: float
    active: bool

@dataclass
class stageThread:
    thread: str
    data: dict = field(default_factory=dict) # Изменения в потоке

@dataclass
class stageButton:
    button: str
    data: dict = field(default_factory=dict) # Изменения в кнопке

@dataclass
class stageWaiter:
    waiter: str
    data: dict = field(default_factory=dict) # Изменения в ожидании

@dataclass
class Stage:
    threads_active: list[stageThread]
    buttons_active: list[stageButton]
    waiter_active: list[stageWaiter]
    stage_generator: str
    to_function: str
    data: dict
