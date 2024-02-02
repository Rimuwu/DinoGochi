# Основной модуль настроек

# Прямой запуск используется для создания файла настроек

# Как модуль предоставляет лишь чтение настроек и доступ к ним
from tools.new_translate.translate import main as check_locs
import json
import os
import sys
import motor.motor_asyncio
from motor.core import AgnosticClient
import pprint

import asyncio

CONFIG_PATH = 'config.json'

class Config:
    def __init__(self) -> None:
        """Класс настроек бота. Все основные переменные хранятся здесь
        """
        self.bot_token = 'NOTOKEN'
        self.bot_devs = []
        self.logs_dir = 'logs'
        self.active_tasks = True
        self.bot_group_id = 0
        self.mongo_url = 'mongodb://localhost:27017'

        self.debug = False
        self.show_advert = False

        self.donation_token = ''
        self.advert_token = ''

        self.check_translate = False

    def fromJSON(self, js: str) -> None:
        """Десереализует строку в данные

        Args:
            js (str): Строка формата json с парвильной разметкой
        """
        self.__dict__ = json.loads(js)

    def toJSON(self) -> str:
        """Сереализует объект настроек в json строку

        Returns:
            str: сереализованная json строка
        """
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)
 
async def check_base(client: AgnosticClient):
    from bot.const import GAME_SETTINGS
    if client.server_info(): print(f"{client.HOST}, mongo connected")

    #Создаёт документы и базы, необходимы для работы бота
    collections = GAME_SETTINGS['collections']
    for base in collections.keys():
        database = client[base]
        for col in collections[base]:
            if col not in await database.list_collection_names():
                await database.create_collection(col)

    #Создаёт документы, необходимые для работы бота
    necessary_create = GAME_SETTINGS['please_create_this']
    for base in necessary_create.keys(): 
        database = client[base]
        for col in necessary_create[base]:
            collection = database[col]
            for doc in necessary_create[base][col]:
                fnd_doc = await collection.find_one({"_id": doc['_id']}, {'_id': 1})
                if not fnd_doc:
                    await collection.insert_one(doc)

    print('The databases are checked and prepared for use.')

conf = Config()

def load():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f: conf.fromJSON(f.read()) # Загрузка настроек
    else:
        sys.exit(f"{CONFIG_PATH} missed! Please, run {__name__}")

    for way in [conf.logs_dir]: # Проверка путей
        if not os.path.exists(way):
            os.mkdir(way) #Создаёт папку в директории  
            print(f"I didn't find the {way} directory, so I created it.")


if __name__ == '__main__':
    with open(CONFIG_PATH, 'w') as f:
        f.write(conf.toJSON())
        sys.exit(f"{CONFIG_PATH} created! Please don't forget to set it up!")
else:
    load()
    if conf.check_translate:
        print("Запуск автоматической проверки файлов локализации.")
        res = check_locs()
        print("Обновлённые данные:")
        pprint.pprint(res)
        print()

    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(conf.mongo_url)

    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(check_base(mongo_client)) # Проверка базы данных на наличие коллекций