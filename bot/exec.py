# Исполнитель бота
from bot.dbmanager import check, mongo_client
from aiogram import Bot, Dispatcher 
from aiogram.fsm.storage.mongo import MongoStorage

from bot.config import conf
from bot.modules.logs import log
from bot.taskmanager import add_task
from bot.taskmanager import run as run_taskmanager
import asyncio

bot = Dispatcher(storage=MongoStorage(mongo_client))
botworker = Bot(conf.bot_token)

async def notify_devs_start():
    # id рассылки
    report_ids = conf.get_report_ids()

    tasks = []
    for id in report_ids:
        if isinstance(id, str):
            channel_id, topic_id = id.split('_', 2)
            tasks.append(botworker.send_message(channel_id, '✅ Бот запущен!', message_thread_id=int(topic_id)))
        else: 
            tasks.append(botworker.send_message(id, '✅ Бот запущен!'))
    await asyncio.gather(*tasks)

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
    # Проверка готовности
    check()

    # Запуск тасков и бота
    add_task(notify_devs_start) # Уведомление запуска для разрабов
    add_task(bot.start_polling, bots=[botworker])

    log('Все готово! Взлетаем!', prefix='Start')
    run_taskmanager()
