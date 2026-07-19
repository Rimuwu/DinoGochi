# Исполнитель бота

print('exec')

# Re-export key components to maintain backward compatibility
from bot.bot_instance import bot, STORAGE, dp, main_router, _fsm_redis

from bot.dbmanager import check, mongo_client
from bot.config import conf
from bot.modules.logs import log, report_devs_start
from bot.taskmanager import add_task
from bot.taskmanager import run as run_taskmanager
import asyncio

# Semantic module imports
from bot.modules.verify_tasks import ensure_background_tasks
from bot.modules.webhook_server import run_webhook_server
from bot.modules.startup_commands import run_startup_commands
from bot.modules.boot_actions import log_startup_banners, initialize_assets

def run():
    log_startup_banners()

    try:
        run_startup_commands()
        initialize_assets()

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
        if getattr(conf, 'webhook_mode', False):
            if not getattr(conf, 'webhook_domain', ''):
                raise ValueError("webhook_domain must be set when webhook_mode is True")
            add_task(run_webhook_server, bot=bot, dp=dp)
        else:
            add_task(dp.start_polling, bots=[bot], 
                     allowed_updates=dp.resolve_used_update_types())

        log('Все готово! Взлетаем!', prefix='Start')
        run_taskmanager()
    except Exception as e:
        log(f'Ошибка в работе бота: {e}', prefix='Error', lvl=4)
        asyncio.run(bot.send_message(conf.bot_report_id, f'❌ Бот упал с ошибкой: {e}'))
        raise
