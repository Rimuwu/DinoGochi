import logging
from time import strftime

from colorama import Fore, Style
# import psutil
from functools import wraps
import telebot

from bot.config import conf

logging.basicConfig(
    handlers=[logging.FileHandler(
        filename=f"{conf.logs_dir}/{strftime('%Y %m-%d %H.%M.%S')}.log", 
        encoding='utf-8', mode='a+')
              ],
        format="%(asctime)s %(levelname)s %(message)s", 
        datefmt="%F %T", 
        level=logging.INFO
        )

# if conf.debug:
#     logger = telebot.logger
#     telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.

def log(message: str, lvl: int = 1, prefix: str = 'Бот') -> None:
    """
    LVL: \n
    0 - debug (активируется в config)\n
    1 - info\n
    2 - warning\n
    3 - error\n
    4 - critical
    """

    if lvl == 0:
        if conf.debug:
            logging.info(f'DEBUG: {message}')
            print(Fore.CYAN + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == -1: # Цвет для логов базы
        logging.error(message)
        print(Fore.LIGHTBLACK_EX + f"{strftime('%Y %m-%d %H.%M.%S')} DB {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 1:
        logging.info(message)
        print(Fore.GREEN + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 2:
        logging.warning(message)
        print(Fore.BLUE + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 3:
        logging.error(message)
        print(Fore.YELLOW + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    else:
        logging.critical(message)
        print(Fore.RED + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)

# def cpu_dec(func):
#     def wrapper(*args):
#         start_cpu = psutil.cpu_percent()
#         start_time = time.time()

#         func(*args)

#         log(f"Функция завершила работу за {round(time.time() - start_time, 4)}, затрачено цпу {round(psutil.cpu_percent() - start_cpu, 4)}, до запуска было затрачено {round(start_cpu, 4)}", 0, func.__name__)

#     return wrapper

# class asinc_decor(object):
#     def cpu(self, func):
#         @wraps(func)
#         async def wrapper(*args):
#             start_cpu = psutil.cpu_percent()
#             start_time = time.time()

#             await func(*args)

#             ccp = round(psutil.cpu_percent() - start_cpu, 4)
#             if ccp > 80 or start_cpu > 80: lvl = 4
#             else: lvl = 0

#             log(f"Функция завершила работу за {round(time.time() - start_time, 4)}, затрачено цпу {ccp}, до запуска было затрачено {round(start_cpu, 4)}", lvl, func.__name__)

#         return wrapper