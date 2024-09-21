from functools import wraps
from time import time
from bot.modules.logs import log
from telebot.types import Message, CallbackQuery

send_logs = True

class HendlerDecorator(object):

    def MessageCommand(self, func):

        @wraps(func)
        async def wrapper(*args):
            message: Message = args[0]
            user_id = message.from_user.id
            time_save = time()

            if send_logs:
                log(f"command: {func.__name__} userid: {user_id}", 0, 'HandlerStart')

            result = await func(*args)

            work_time = round(time() - time_save, 4)
            add_message = ''
            if work_time >= 60:
                add_message = 'AHTUNG 60'
            elif work_time >= 10:
                add_message = 'AHTUNG 10'

            if send_logs:
                log(f"command: {func.__name__} userid: {user_id} work.time: {work_time} result: {result} {add_message}", 0, 'HandlerEnd')

        return wrapper

    def CallbackCommand(self, func):

        @wraps(func)
        async def wrapper(*args):
            callback: CallbackQuery = args[0]
            user_id = callback.from_user.id
            time_save = time()

            if send_logs:
                log(f"ButtonClickStart: {func.__name__} userid: {user_id}", 0, 'HandlerStart')

            result = await func(*args)

            work_time = round(time() - time_save, 4)
            add_message = ''
            if work_time >= 60:
                add_message = 'AHTUNG 60'
            elif work_time >= 10:
                add_message = 'AHTUNG 10'
            
            if send_logs:
                log(f"ButtonClickEnd: {func.__name__} userid: {user_id} work.time: {work_time} result: {result} {add_message}", 0, 'HandlerStart')

        return wrapper

HDMessage = HendlerDecorator().MessageCommand
HDCallback = HendlerDecorator().CallbackCommand