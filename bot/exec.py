# Исполнитель бота
from pydoc import cli
from bot.dbmanager import check, mongo_client
from aiogram import Bot, Dispatcher, Router 
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.mongo import MongoStorage

from bot.config import conf
from bot.modules.logs import log, report_devs_start
from bot.taskmanager import add_task
from bot.taskmanager import run as run_taskmanager
import asyncio

bot = Bot(conf.bot_token)
STORAGE = MongoStorage(client=mongo_client, 
                       db_name='other',
                       collection_name='states')
dp = Dispatcher(storage=STORAGE)

main_router = Router(name='MainRouter')
dp.include_router(main_router)

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
        # Проверка готовности
        check()

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
