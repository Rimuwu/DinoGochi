from bot.exec import bot
from bot.exec import STORAGE
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext

from bot.modules.logs import log

BOT_ID = None

async def get_state(user_id: int, chat_id: int):
    global BOT_ID
    if BOT_ID is None:
        self_bot = await bot.get_me()
        BOT_ID = self_bot.id

    # Создаем уникальный ключ состояния на основе user_id и chat_id
    key = StorageKey(bot_id=BOT_ID, user_id=user_id, chat_id=chat_id)
    # Создаем контекст FSM с хранилищем и ключом
    fsm_context = FSMContext(storage=STORAGE, key=key)
    return fsm_context


async def clear_multi_inventory_state(user_id: int, chat_id: int, state=None):
    """Clear ChooseMultiInventory FSM state and delete its inline message."""
    if state is None:
        state = await get_state(user_id, chat_id)
    state_data = await state.get_data()
    log(f'clear_multi_inventory_state: state_data keys={list(state_data.keys()) if state_data else None}', prefix='FSM')
    await state.clear()
    main_message = state_data.get('main_message', 0) if state_data else 0
    log(f'clear_multi_inventory_state: main_message={main_message} chat_id={chat_id}', prefix='FSM')
    if main_message:
        try:
            await bot.delete_message(chat_id, main_message)
            log(f'clear_multi_inventory_state: deleted message {main_message}', prefix='FSM')
        except Exception as e:
            log(f'clear_multi_inventory_state: delete failed: {e}', prefix='FSM', lvl=3)