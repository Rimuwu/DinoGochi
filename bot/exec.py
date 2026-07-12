# Исполнитель бота

print('exec')

from bot.dbmanager import check, mongo_client
from aiogram import Bot, Dispatcher, Router 
from aiogram.types import ErrorEvent
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as aioredis

from bot.config import conf
from bot.modules.logs import log, report_devs_start
from bot.taskmanager import add_task
from bot.taskmanager import run as run_taskmanager
import asyncio

import json

def _fsm_json_default(obj):
    """Fallback encoder for types RedisStorage can't serialize by default."""
    try:
        from bson import ObjectId
        if isinstance(obj, ObjectId):
            return str(obj)
    except ImportError:
        pass
    return str(obj)

def _fsm_json_dumps(data: dict) -> str:
    return json.dumps(data, default=_fsm_json_default)

async def ensure_background_tasks():
    from bot.models.activity import CollectingActivity, GameActivity, JourneyActivity
    from bot.models.dinosaur import Egg
    from bot.models.other import Lottery
    from bot.models.items import ItemCraft
    from bot.models.market import Product, Preferential

    log("Запуск синхронизации фоновых задач в Redis...", lvl=1)
    
    try:
        await CollectingActivity.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации CollectingActivity: {e}", lvl=3)

    try:
        await GameActivity.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации GameActivity: {e}", lvl=3)

    try:
        await Egg.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Egg: {e}", lvl=3)

    try:
        await JourneyActivity.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации JourneyActivity: {e}", lvl=3)

    try:
        await Lottery.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Lottery: {e}", lvl=3)

    try:
        await ItemCraft.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации ItemCraft: {e}", lvl=3)

    try:
        await Product.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Product: {e}", lvl=3)

    try:
        await Preferential.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Preferential: {e}", lvl=3)

    # Перестройка Redis-кеша шардов динозавров
    try:
        from bot.modules.shard_cache import rebuild_shards
        await rebuild_shards()
    except Exception as e:
        log(f"Ошибка перестройки шардов: {e}", lvl=3)

    log("Синхронизация фоновых задач завершена.", lvl=1)

from typing import Any, Optional
from aiogram.methods.base import TelegramMethod

class CustomBot(Bot):
    async def __call__(
        self,
        method: TelegramMethod,
        request_timeout: Optional[int] = None,
    ) -> Any:
        # Intercept and convert markdown to html
        from bot.modules.data_format import convert_markdown_to_html
        
        # Helper check to see if text/caption has custom emoji syntax
        def has_custom_emoji(val: Any) -> bool:
            return isinstance(val, str) and "![" in val and "tg://emoji?id=" in val

        # 1. Check if method has parse_mode and either text or caption
        parse_mode = getattr(method, "parse_mode", None)
        if parse_mode != "HTML":
            should_convert = parse_mode in ("Markdown", "MarkdownV2")
            # If SendMessage or EditMessageText or similar
            if hasattr(method, "text"):
                text = getattr(method, "text", None)
                if should_convert or has_custom_emoji(text):
                    if isinstance(text, str):
                        method.text = convert_markdown_to_html(text)
                        method.parse_mode = "HTML"
            # If SendPhoto, SendVideo, EditMessageCaption or similar
            elif hasattr(method, "caption"):
                caption = getattr(method, "caption", None)
                if should_convert or has_custom_emoji(caption):
                    if isinstance(caption, str):
                        method.caption = convert_markdown_to_html(caption)
                        method.parse_mode = "HTML"

        # 2. Check if method is EditMessageMedia
        if hasattr(method, "media"):
            media = getattr(method, "media", None)
            if media:
                media_parse_mode = getattr(media, "parse_mode", None)
                if media_parse_mode != "HTML":
                    media_caption = getattr(media, "caption", None)
                    if media_parse_mode in ("Markdown", "MarkdownV2") or has_custom_emoji(media_caption):
                        if isinstance(media_caption, str):
                            new_caption = convert_markdown_to_html(media_caption)
                            if hasattr(media, "model_copy"):
                                method.media = media.model_copy(update={"caption": new_caption, "parse_mode": "HTML"})
                            else:
                                method.media = media.copy(update={"caption": new_caption, "parse_mode": "HTML"})

        return await super().__call__(method, request_timeout)

bot = CustomBot(conf.bot_token)
_fsm_redis = aioredis.from_url(
    conf.redis_url,
    decode_responses=False,  # RedisStorage требует bytes, не str
    socket_timeout=5.0
)
STORAGE = RedisStorage(redis=_fsm_redis, json_dumps=_fsm_json_dumps)
dp = Dispatcher(storage=STORAGE)

main_router = Router(name='MainRouter')
dp.include_router(main_router)

# @dp.errors() 
# async def on_error(error_event: ErrorEvent):
#     text = f'error: {error_event.exception.args} <{error_event.exception}>'
#     if error_event.update.message:
#         text = f'message_text: {error_event.update.message.text} - {text}'

#         if error_event.update.message.from_user:
#             user = error_event.update.message.from_user
#             text = f'userid: {user.id} - {text}'

#     log(text, prefix='AiogramError', lvl=4)

def run():
    log('# ====== Inicialization Start ====== #', 2)
    log('Привет! Я вижу ты так и не починил тот самый баг на 46-ой строчке...')
    log('Это не баг, а фича!')
    log('Ваша фича наминирована на оскар!')
    log('Спасибо, но я все равно перепишу все с нуля...')
    log('У вас логи не логятся :/')
    log('Не вижу ошибок == нет ошибок!')
    log('Кстати, в создании бота поучаствовал ChatGPT')
    log('Ой, да что там ваш ChatGPT?! *Stable Diffusion подключился*')

    try:
        # Автоматический запуск команды, если задан флаг use_command
        if getattr(conf, 'use_command', False) and getattr(conf, 'command', ''):
            import os
            import subprocess
            command_str = conf.command.strip()
            
            # Проверяем, запускалась ли уже эта команда успешно
            state_file_path = os.path.join('.state-save', 'executed_command.json')
            already_run = False
            if os.path.exists(state_file_path):
                try:
                    with open(state_file_path, 'r', encoding='utf-8') as sf:
                        state_data = json.load(sf)
                        if state_data.get('command') == command_str and state_data.get('success') is True:
                            already_run = True
                except Exception:
                    pass

            if not already_run:
                log(f"Обнаружен флаг use_command=True. Запуск команды: {command_str}")
                try:
                    res = subprocess.run(command_str, shell=True)
                    if res.returncode == 0:
                        log(f"[OK] Команда '{command_str}' выполнена успешно.")
                        
                        # Пытаемся сбросить флаг в config.json
                        try:
                            with open('config.json', 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                            config_data['use_command'] = False
                            with open('config.json', 'w', encoding='utf-8') as f:
                                json.dump(config_data, f, ensure_ascii=False, indent=4)
                            log("Флаг use_command успешно сброшен на False в config.json.")
                        except OSError as config_err:
                            log(f"Предупреждение: Не удалось перезаписать config.json ({config_err}). Используем сохранение состояния в volume.")
                        
                        # Сохраняем состояние выполнения (только при успехе) в доступный для записи volume
                        try:
                            os.makedirs('.state-save', exist_ok=True)
                            with open(state_file_path, 'w', encoding='utf-8') as sf:
                                json.dump({'command': command_str, 'success': True}, sf, ensure_ascii=False, indent=4)
                            log("Состояние выполнения сохранено в .state-save/executed_command.json")
                        except Exception as sf_err:
                            log(f"Не удалось записать файл состояния: {sf_err}", prefix='Error', lvl=4)
                    else:
                        log(f"[Error] Команда '{command_str}' завершилась с кодом {res.returncode}.", prefix='Error', lvl=4)
                        
                except Exception as err:
                    log(f"Ошибка при автоматическом выполнении команды: {err}", prefix='Error', lvl=4)
            else:
                log(f"Команда '{command_str}' уже была выполнена ранее (пропуск).")

        # Прегенерация изображений предметов и автогенерация конфига эмодзи
        try:
            from bot.modules.items.image_generator import pregenerate_item_images, auto_generate_items_emojis_json
            if getattr(conf, 'pregenerate_images', True):
                pregenerate_item_images()
            if getattr(conf, 'sync_custom_emojis', False):
                auto_generate_items_emojis_json()
            from bot.const import reload_const
            reload_const()
        except Exception as e:
            log(f"Ошибка при инициализации изображений/эмодзи предметов: {e}", lvl=3)

        # Проверка готовности
        check()

        # Shard verification and task queue synchronization on startup
        if conf.active_tasks:
            add_task(ensure_background_tasks)

            # Run task queue ticks periodically (every 1 second)
            from bot.modules.task_queue import task_queue_tick
            add_task(task_queue_tick, repeat_time=1.0, delay=1.0)

        # Запуск тасков и бота
        add_task(report_devs_start, bot=bot) # Уведомление запуска для разрабов
        add_task(dp.start_polling, bots=[bot], 
                 allowed_updates=dp.resolve_used_update_types())

        log('Все готово! Взлетаем!', prefix='Start')
        run_taskmanager()
    except Exception as e:
        log(f'Ошибка в работе бота: {e}', prefix='Error', lvl=4)
        asyncio.run(bot.send_message(conf.bot_report_id, f'❌ Бот упал с ошибкой: {e}'))
        raise
