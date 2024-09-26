import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from multiprocessing import Queue
from time import strftime
import telebot

from bot.config import conf

# Logger
logger = logging.getLogger()

# File logger
log_filehandler = RotatingFileHandler(
        filename=f"{conf.logs_dir}/{strftime('%Y-%m-%d_%H.%M.%S')}.log", 
        encoding='utf-8', mode='a+', backupCount=100, maxBytes=1024*1024*10)
log_streamhandler = logging.StreamHandler()
log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%F %T")
log_filehandler.setFormatter(log_formatter)
log_streamhandler.setFormatter(log_formatter)

# Async queue logging
log_queue = Queue()
queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)
logger.addHandler(log_streamhandler)

# Log listen
queue_listener = QueueListener(log_queue, log_filehandler)

logger.setLevel(logging.DEBUG)
queue_listener.start()

# if conf.debug:
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
            logger.info(f'{prefix} DEBUG: {message}')
    elif lvl == -1: # Цвет для логов базы
        if conf.base_logging:
            logger.info(f"{prefix}: {message}")
    elif lvl == 1:
        logger.info(f"{prefix}: {message}")
    elif lvl == 2:
        logger.warning(f"{prefix}: {message}")
    elif lvl == 3:
        logger.error(f"{prefix}: {message}")
    else:
        logger.critical(f"{prefix}: {message}")
