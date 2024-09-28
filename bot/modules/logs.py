import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from multiprocessing import Queue
from time import strftime

from bot.config import conf

last_errors = []
MAX_ERRORS = 5
errors_counter = 0
last_errors_counter = 0

# Logger
logger = logging.getLogger()

# File logger
log_filehandler = RotatingFileHandler(
        filename=f"{conf.logs_dir}/{strftime('%Y-%m-%d_%H.%M.%S')}.log", 
        encoding='utf-8', mode='a+', backupCount=10, maxBytes=1024*1024*10)
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

logger.setLevel(logging.INFO)
queue_listener.start()

# if conf.debug:
#     telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.

def log(message: str, lvl: int = 1, prefix: str = 'Бот') -> None:
    """
    LVL: \n
    -1 - Base Log\n
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
        report_last_error(f"{prefix}: {message}")
    else:
        logger.critical(f"{prefix}: {message}")
        report_last_error(f"{prefix}: {message}")

# Храним последние ошибки
def report_last_error(message: str):
    global errors_counter
    errors_counter += 1
    if len(last_errors) >= MAX_ERRORS:
        last_errors.pop(0)

    last_errors.append(message)

def get_errors_last_count() -> int:
    global last_errors_counter
    errors_dif = errors_counter - last_errors_counter
    last_errors_counter = errors_counter
    return errors_dif

def get_errors_count() -> int:
    return errors_counter


# Получить последние ошибки
def get_last_errors() -> list[str]:
    last_errors_copy = last_errors.copy()
    last_errors.clear()
    return last_errors_copy