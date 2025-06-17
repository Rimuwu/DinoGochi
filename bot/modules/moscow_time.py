import os
import time
from datetime import timezone, timedelta

# Установка московской временной зоны как глобальной
MOSCOW_TZ = timezone(timedelta(hours=3))

def set_moscow_timezone():
    """
    Устанавливает московскую временную зону как системную по умолчанию
    """
    # Устанавливаем переменную окружения TZ
    os.environ['TZ'] = 'Europe/Moscow'
    
    # Перезагружаем временную зону (только на Unix-системах)
    try:
        if hasattr(time, 'tzset'):
            time.tzset()  # type: ignore
    except (OSError, AttributeError):
        # На Windows tzset может отсутствовать или не работать
        pass