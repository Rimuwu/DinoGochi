from bot.exec import bot
from bot.exec import STORAGE
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext

BOT_ID = 0

async def get_state(user_id: int, chat_id: int):
    global BOT_ID
    if not BOT_ID:
        self_bot = await bot.get_me()
        BOT_ID = self_bot.id

    # Создаем ключ состояния на основе user_id и chat_id
    key = StorageKey(BOT_ID, user_id=user_id, chat_id=chat_id)
    # Создаем контекст FSM с хранилищем и ключом
    fsm_context = FSMContext(storage=STORAGE, key=key)
    return fsm_context