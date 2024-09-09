import asyncio
import os
import pprint
import sys
from typing import Dict

import motor.motor_asyncio
from config import CONFIG_PATH, conf
from motor.core import AgnosticClient

from bot.const import GAME_SETTINGS

# Проверка mongodb 
async def check_db(client: AgnosticClient):
    if not client.server_info():
        raise ConnectionError("Failed to connect to MongoDB server")
    
    print(f"{client.HOST}, mongo connected")

    await create_collections(client)
    await create_necessary_documents(client)
    
    print('The databases are checked and prepared for use.')

# Создание необходимых коллекций
async def create_collections(client: AgnosticClient):
    for base, collections in GAME_SETTINGS['collections'].items():
        database = client[base]
        existing_collections = set(await database.list_collection_names())
        for col in collections:
            if col not in existing_collections:
                await database.create_collection(col)

# Создание необходимых документов
async def create_necessary_documents(client: AgnosticClient):
    for base, collections in GAME_SETTINGS['please_create_this'].items():
        database = client[base]
        for col, documents in collections.items():
            collection = database[col]
            for doc in documents:
                await create_document_if_not_exists(collection, doc)

# Создание отстуствующих документов
async def create_document_if_not_exists(collection, doc: Dict):
    if not await collection.find_one({"_id": doc['_id']}, {'_id': 1}):
        await collection.insert_one(doc)


def check():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f: conf.from_json(f.read()) # Загрузка настроек
    else:
        sys.exit(f"{CONFIG_PATH} missed! Please, run {__name__}")

    for way in [conf.logs_dir]: # Проверка путей
        if not os.path.exists(way):
            os.mkdir(way) #Создаёт папку в директории  
            print(f"I didn't find the {way} directory, so I created it.")

    if conf.check_translate:
        from tools.translate.translate import main as check_locs

        print("Запуск автоматической проверки файлов локализации.")
        res = check_locs()
        print("Обновлённые данные:")
        pprint.pprint(res)
        print()

    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(conf.mongo_url)

    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(check_db(mongo_client)) # Проверка базы данных на наличие коллекций