from functools import wraps
from time import time
from bot.modules.logs import log
from telebot.types import Message, CallbackQuery


class HendlerDecorator(object):

    def MessageCommand(self, func):

        @wraps(func)
        async def wrapper(*args):
            message: Message = args[0]
            user_id = message.from_user.id
            time_save = time()

            log(f"command: {func.__name__} userid: {user_id}", 0, 'HandlerStart')

            result = await func(*args)

            log(f"command: {func.__name__} userid: {user_id} work.time: {round(time() - time_save, 4)} result: {result}", 0, 'HandlerStart')

        return wrapper

    def CallbackCommand(self, func):

        @wraps(func)
        async def wrapper(*args):
            callback: CallbackQuery = args[0]
            user_id = callback.from_user.id
            time_save = time()

            log(f"buttonclick: {func.__name__} userid: {user_id}", 0, 'HandlerStart')

            result = await func(*args)

            log(f"buttonclick: {func.__name__} userid: {user_id} work.time: {round(time() - time_save, 4)} result: {result}", 0, 'HandlerStart')

        return wrapper

HDMessage = HendlerDecorator().MessageCommand
HDCallback = HendlerDecorator().CallbackCommand