# Исполнитель бота
import traceback

from telebot.async_telebot import AsyncTeleBot, ExceptionHandler

from bot.config import conf
from bot.modules.logs import log
from bot.taskmanager import add_task, run as run_taskmanager
class TracebackHandler(ExceptionHandler):
    def handle(self, exception):
        log(f'{traceback.format_exc()} {exception}', 3)

bot = AsyncTeleBot(conf.bot_token, 
                   exception_handler=TracebackHandler()
                   )
bot.enable_saving_states()

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

    # Запуск тасков и бота
    add_task(bot.infinity_polling, skip_pending=True, timeout=5, request_timeout=20)
    log('Все готово! Взлетаем!', prefix='Start')
    run_taskmanager()
