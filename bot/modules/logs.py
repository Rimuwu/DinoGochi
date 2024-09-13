import logging
from logging.handlers import RotatingFileHandler
from time import strftime

from colorama import Fore, Style

from bot.config import conf

logging.basicConfig(
    handlers=[RotatingFileHandler(
        filename=f"{conf.logs_dir}/{strftime('%Y %m-%d %H.%M.%S')}.log", 
        encoding='utf-8', mode='a+', backupCount=10, maxBytes=1024*1024*10)
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
    -1 - Base Log
    0 - debug (активируется в config)\n
    1 - info\n
    2 - warning\n
    3 - error\n
    4 - critical
    """

    if lvl == 0:
        if conf.debug:
            logging.info(f'{prefix}: DEBUG: {message}')
            print(Fore.CYAN + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == -1: # Цвет для логов базы
        if conf.base_logging:
            logging.info(f"{prefix}: {message}")
            print(Fore.LIGHTBLACK_EX + f"{strftime('%Y %m-%d %H.%M.%S')} DB {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 1:
        logging.info(f"{prefix}: {message}")
        print(Fore.GREEN + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 2:
        logging.warning(f"{prefix}: {message}")
        print(Fore.BLUE + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    elif lvl == 3:
        logging.error(f"{prefix}: {message}")
        print(Fore.YELLOW + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
    else:
        logging.critical(f"{prefix}: {message}")
        print(Fore.RED + f"{strftime('%Y %m-%d %H.%M.%S')} {prefix}: {message}" + Style.RESET_ALL)
