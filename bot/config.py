# Основной модуль настроек

# Прямой запуск используется для создания файла настроек

# Как модуль предоставляет лишь чтение настроек и доступ к ним
import json
import sys
import os
import re

CONFIG_PATH = 'config.json'

# Load .env file manually if it exists (for local runs)
if os.path.exists('.env'):
    try:
        with open('.env', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip()
    except Exception as e:
        print(f"Error loading .env file: {e}")

class Config:
    def __init__(self) -> None:
        """Класс настроек бота. Все основные переменные хранятся здесь
        """
        self.bot_token = 'NOTOKEN' # Токен бота
        self.bot_devs = [] # Доступ к админ командам
        self.logs_dir = 'logs' # Директория логов
        self.active_tasks = True # Активация тасков
        self.bot_group_id = 0 # Уведомления событий
        self.bot_report_id = 0 # Отчеты
        self.mongo_url = 'mongodb://root:example@mongo:27017'
        self.redis_url = 'redis://:redis_dino_secret@redis:6379'

        self.debug = False # Больше логов
        self.show_advert = False # Отображения рекламы
        self.advert_token = '' # Рекламный токен

        self.check_translate = False # Синхронизация перевода
        self.base_logging = False # Логирование БД
        self.handlers_logging = False # Логирование обработчиков

        self.only_dev = False # Принимает сообщения только от разработчиков
        self.use_command = False # Использовать автозапуск команды при старте
        self.command = "" # Команда для автозапуска

    def from_json(self, js: str) -> None:
        """Десереализует строку в данные

        Args:
            js (str): Строка формата json с парвильной разметкой
        """
        def repl(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        js_substituted = re.sub(r'\$\{([^}]+)\}', repl, js)
        self.__dict__ = json.loads(js_substituted)

    def to_json(self) -> str:
        """Сереализует объект настроек в json строку

        Returns:
            str: сереализованная json строка
        """
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)
 
conf = Config()

if __name__ == '__main__':
    with open(CONFIG_PATH, 'w') as f:
        f.write(conf.to_json())
        sys.exit(f"{CONFIG_PATH} created! Please don't forget to set it up!")
else:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f: conf.from_json(f.read()) # Загрузка настроек
    else:
        sys.exit(f"{CONFIG_PATH} missed! Please, run {__name__}")