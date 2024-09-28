# Основной модуль настроек

# Прямой запуск используется для создания файла настроек

# Как модуль предоставляет лишь чтение настроек и доступ к ним
import json
import sys
import os

CONFIG_PATH = 'config.json'

class Config:
    def __init__(self) -> None:
        """Класс настроек бота. Все основные переменные хранятся здесь
        """
        self.bot_token = 'NOTOKEN' # Токен бота
        self.bot_devs = [] # Доступ к админ командам
        self.logs_dir = 'logs' # Директория логов
        self.active_tasks = True # Активация тасков
        self.bot_group_id = 0 # Уведомления событий
        self.mongo_url = 'mongodb://root:example@mongo:27017'

        self.debug = False # Больше логов
        self.show_advert = False # Отображения рекламы
        self.advert_token = '' # Рекламный токен

        self.check_translate = False # Синхронизация перевода
        self.base_logging = False # Логирование БД
        self.handlers_logging = False # Логирование обработчиков

        self.only_dev = False # Принимает сообщения только от разработчиков

    def from_json(self, js: str) -> None:
        """Десереализует строку в данные

        Args:
            js (str): Строка формата json с парвильной разметкой
        """
        self.__dict__ = json.loads(js)

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