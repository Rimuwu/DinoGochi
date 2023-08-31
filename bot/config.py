# Основной модуль настроек

# Прямой запуск используется для создания файла настроек

# Как модуль предоставляет лишь чтение настроек и доступ к ним

import pymongo
import json
import os
import sys

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
        self.ssh = False

        # self.ssh = False
        self.mongo_url = 'mongodb://localhost:27017'

        # self.ssh = True
        self.ssh_host = 'db.example.com'
        self.ssh_port = 21
        self.ssh_user = 'user'
        self.ssh_password = 'password'

        self.debug = False
        self.donation_token = ''

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
 
def check_base(client: pymongo.MongoClient):
    from bot.const import GAME_SETTINGS
    if client.server_info(): print(f"{client.address}, mongo connected")

    #Создаёт документы и базы, необходимы для работы бота
    collections = GAME_SETTINGS['collections']
    for base in collections.keys():
        database = client[base]
        for col in collections[base]:
            if col not in database.list_collection_names():
                database.create_collection(col)

    #Создаёт документы, необходимые для работы бота
    necessary_create = GAME_SETTINGS['please_create_this']
    for base in necessary_create.keys(): 
        database = client[base]
        for col in necessary_create[base]:
            collection = database[col]
            for doc in necessary_create[base][col]:
                fnd_doc = collection.find_one({"_id": doc['_id']}, {'_id': 1})
                if not fnd_doc:
                    collection.insert_one(doc)
    
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
    if conf.ssh:
        from ssh_pymongo import MongoSession

        session = MongoSession(
            host=conf.ssh_host,
            port=conf.ssh_port,
            user=conf.ssh_user,
            password=conf.ssh_password,
        )
        mongo_client = session.connection
    else:
        mongo_client = pymongo.MongoClient(conf.mongo_url)

    check_base(mongo_client) # Проверка базы данных на наличие коллекций