



import time
from bot.modules.logs import log

_time_dict = {}

def time_counter(key: str, message: str):
    global _time_dict

    """
    Функция для измерения времени между двумя вызовами с одним и тем же ключом.
    Первый вызов — сохраняет время и выводит message.
    Второй вызов — вычисляет разницу, выводит сообщение о завершении и удаляет ключ.
    """
    if key not in _time_dict:
        _time_dict[key] = time.time()
        log(f"Задача \"{message}\" начата", lvl=1)
    else:
        elapsed = time.time() - _time_dict.pop(key)
        log(f"Задача \"{message}\" завершена за {elapsed:.2f} секунд", lvl=1)

def tc(key: str, message: str):
    """
    Сокращенная версия time_counter для удобства использования.
    """
    time_counter(key, message)