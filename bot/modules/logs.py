import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from multiprocessing import Queue
from time import strftime

from colorama import Fore, Style

from bot.config import conf
# Logger
logger = logging.getLogger()
# File logger
log_filehandler = RotatingFileHandler(
        filename=f"{conf.logs_dir}/{strftime('%Y %m-%d %H.%M.%S')}.log", 
        encoding='utf-8', mode='a+', backupCount=10, maxBytes=1024*1024*10)
log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%F %T")
log_filehandler.setFormatter(log_formatter)
# Async queue logging
log_queue = Queue()
queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)
# Log listen
queue_listener = QueueListener(log_queue, log_filehandler)

logger.setLevel(logging.INFO)
queue_listener.start()

# if conf.debug:
#     logger = telebot.logger
#     telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.

def log(message: str, lvl: int = 1, prefix: str = 'Бот') -> None:
    """
    LVL: \n
    -1 - Base Log
    0 - debug (активируется в config)\n
    1 - info\n
    2 - warning\n
    3 - error\n
    4 - critical
    """

    if lvl == 0:
        if conf.debug:
            logger.info(f'{prefix}: DEBUG: {message}')
            print(Fore.CYAN + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == -1: # Цвет для логов базы
        if conf.base_logging:
            logger.info(f"{prefix}: {message}")
            print(Fore.LIGHTBLACK_EX + f"{strftime('%Y %m-%d %H.%M.%S')} DB {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 1:
        logger.info(f"{prefix}: {message}")
        print(Fore.GREEN + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 2:
        logger.warning(f"{prefix}: {message}")
        print(Fore.BLUE + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 3:
        logger.error(f"{prefix}: {message}")
        print(Fore.YELLOW + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    else:
        logger.critical(f"{prefix}: {message}")
        print(Fore.RED + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
