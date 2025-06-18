# Основной файл запуска, инициирует бота

import time
print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Первичный запуск")

from bot.exec import run
if __name__ == '__main__': run()