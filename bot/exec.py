# Исполнитель бота
import traceback

from bot.dbmanager import check
from telebot.async_telebot import AsyncTeleBot, ExceptionHandler

from bot.config import conf
from bot.modules.logs import log
from bot.taskmanager import add_task
from bot.taskmanager import run as run_taskmanager
import asyncio


class TracebackHandler(ExceptionHandler):
    def handle(self, exception):
        log(f'{traceback.format_exc()} {exception}', 3)

bot = AsyncTeleBot(conf.bot_token, 
                   exception_handler=TracebackHandler()
                   )
bot.enable_saving_states()

async def report_devs_start():
    tasks = []
    report_id = conf.bot_report_id
    if isinstance(report_id, str):
        channel_id, topic_id = report_id.split('_', 1)
        tasks.append(bot.send_message(channel_id, '✅ Бот запущен!', message_thread_id=int(topic_id)))
    else: 
        tasks.append(bot.send_message(report_id, '✅ Бот запущен!'))
        
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
    add_task(report_devs_start) # Уведомление запуска для разрабов
    add_task(bot.infinity_polling, skip_pending=True)
    log('Все готово! Взлетаем!', prefix='Start')
    run_taskmanager()
