from time import time

from bot.config import conf
from bot.exec import bot, STORAGE
from bot.modules.get_state import get_state, clear_multi_inventory_state
from bot.modules.localization import get_lang
from bot.modules.markup import markups_menu as m
from bot.taskmanager import add_task
from bot.modules.logs import log


async def storage_clear():
    """Scan Redis FSM keys and expire states older than 1 hour.
    For ChooseMultiInventory states also deletes the inline keyboard message."""
    from aiogram.fsm.storage.redis import RedisStorage
    if not isinstance(STORAGE, RedisStorage):
        return

    try:
        import json
        redis = STORAGE.redis
        # FSM data keys pattern: fsm:{bot_id}:{chat_id}:{user_id}:data
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=b'fsm:*:data', count=200)
            for key in keys:
                try:
                    raw = await redis.get(key)
                    if not raw:
                        continue
                    data = json.loads(raw)
                    time_start = data.get('time_start')
                    if not time_start or time_start + 3600 > time():
                        continue

                    # Parse ids from key: fsm:{bot}:{chat}:{user}:data
                    parts = key.decode().split(':')
                    if len(parts) < 5:
                        continue
                    chat_id = int(parts[2])
                    user_id = int(parts[3])

                    # Check state name for ChooseMultiInventory
                    state_key_str = key.decode().replace(':data', ':state')
                    state_raw = await redis.get(state_key_str)
                    state_name = state_raw.decode() if state_raw else ''

                    if 'ChooseMultiInventory' in state_name:
                        await clear_multi_inventory_state(user_id, chat_id)
                    else:
                        state = await get_state(user_id, chat_id)
                        if state:
                            await state.clear()

                    lang = await get_lang(user_id)
                    try:
                        await bot.send_message(chat_id, '❌',
                            reply_markup=await m(user_id, 'last_menu', lang))
                    except Exception:
                        pass

                except Exception as e:
                    log(f'storage_clear key error: {e}', lvl=3)

            if cursor == 0:
                break

        # Clean up old temporary inline images
        try:
            import os
            temp_dir = 'bot/temp'
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    if filename.startswith('img-'):
                        filepath = os.path.join(temp_dir, filename)
                        if os.path.isfile(filepath):
                            # check if file is older than 24 hours (86400 seconds)
                            if os.path.getmtime(filepath) + 86400 < time():
                                try:
                                    os.remove(filepath)
                                    log(f"Removed expired temp inline image file: {filepath}", lvl=1)
                                except Exception as rm_err:
                                    log(f"Failed to remove temp file {filepath}: {rm_err}", lvl=2)
        except Exception as cleanup_err:
            log(f"Error during temp file cleanup: {cleanup_err}", lvl=3)

    except Exception as e:
        log(f'storage_clear error: {e}', lvl=3)
    finally:
        import gc
        gc.collect()


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(storage_clear, 1800, 15)