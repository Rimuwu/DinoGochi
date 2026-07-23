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
    
    if state_data:
        msg_ids = []
        if state_data.get('main_message'):
            msg_ids.append(state_data['main_message'])
        if state_data.get('edit_message_id'):
            msg_ids.append(state_data['edit_message_id'])
        
        t_data = state_data.get('transmitted_data', {})
        steps = t_data.get('steps', [])
        for s in steps:
            if isinstance(s, dict) and s.get('bmessageid'):
                msg_ids.append(s['bmessageid'])

        for mid in set(msg_ids):
            if mid:
                try:
                    await bot.delete_message(chat_id, mid)
                    log(f'clear_multi_inventory_state: deleted message {mid}', prefix='FSM')
                except Exception as e:
                    log(f'clear_multi_inventory_state: delete failed: {e}', prefix='FSM', lvl=3)