import asyncio
import os
import pprint
from typing import Dict
import time

import motor.motor_asyncio
from bot.config import conf
from motor.core import AgnosticClient

from bot.const import GAME_SETTINGS
from bot.modules.time_counter import time_counter


mongo_client = motor.motor_asyncio.AsyncIOMotorClient(conf.mongo_url)


async def wait_for_mongo_ready(client: AgnosticClient, timeout=30):
    """Ждем готовности MongoDB"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            await client.admin.command('ping')
            print("MongoDB is ready!")
            return True
        except Exception as e:
            print(f"Waiting for MongoDB... ({e})")
            await asyncio.sleep(1)
    raise TimeoutError("MongoDB not ready within timeout")


# Проверка mongodb 
async def check_db(client: AgnosticClient):
    # Сначала ждем готовности MongoDB
    await wait_for_mongo_ready(client)
    
    if not client.server_info():
        raise ConnectionError("Failed to connect to MongoDB server")

    print(f"{client.HOST}, mongo connected")

    print('Checking the database...')
    await create_collections(client)
    print('Collections checked.')

    print('Creating necessary documents...')
    await create_necessary_documents(client)
    print('Necessary documents created.')

    # Создание индексов в фоне для ускорения запуска
    asyncio.create_task(create_indexes_background(client))
    print('Index creation started in background.')

    print('The databases are checked and prepared for use.')


async def create_indexes_background(client: AgnosticClient):
    """Создание индексов в фоновом режиме"""
    try:
        print('Creating indexes in background...')
        await check_and_create_indexes(client)
        print('Background index creation completed.')
    except Exception as e:
        print(f'Error creating indexes in background: {e}')


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

# Проверка и создание индексов для коллекций
async def check_and_create_indexes(client: AgnosticClient):
    for index_config in GAME_SETTINGS['indexes']:
        database = client[index_config['database']]
        collection = database[index_config['collection']]
        existing_indexes = await collection.index_information()

        for index in index_config['indexes']:
            index_name = index.get('name') or index['field']
            if index_name not in existing_indexes:
                index_options = {
                    'name': index_name,
                    'unique': index.get('unique', False),
                    'sparse': index.get('sparse', False),
                }

                # Добавляем TTL только если он указан
                if 'ttl' in index and index['ttl'] is not None:
                    index_options['expireAfterSeconds'] = index['ttl']

                # Исключаем wildcardProjection, если тип индекса не wildcard
                if index.get('type') == 'wildcard' and 'wildcardProjection' in index:
                    index_options['wildcardProjection'] = index['wildcardProjection']

                # Исключаем collation, если он пуст
                collation = index.get('collation')
                if collation:
                    index_options['collation'] = collation

                # Исключаем partialFilterExpression, если он пуст
                partial_filter_expression = index.get('partialFilterExpression')
                if partial_filter_expression:
                    # Удаляем $ne: null, оставляем только $exists: true
                    if isinstance(partial_filter_expression.get('userid', {}), dict) and '$ne' in partial_filter_expression.get('userid', {}):
                        partial_filter_expression = {"userid": {"$exists": True}}
                    index_options['partialFilterExpression'] = partial_filter_expression

                try:
                    index_type = index.get('type')
                    
                    if index_type in ['1', '-1', 1, -1]:
                        # Числовой индекс (восходящий или нисходящий)
                        await collection.create_index([(index['field'], int(index_type))], **index_options)
                    elif index_type == '2dsphere':
                        # Геопространственный индекс
                        await collection.create_index([(index['field'], '2dsphere')], **index_options)
                    elif index_type == 'text':
                        # Проверяем, есть ли уже текстовый индекс в коллекции
                        has_text_index = False
                        for idx_info in existing_indexes.values():
 
                            if isinstance(idx_info.get('key'), list):
                                for key_field, key_type in idx_info['key']:
                                    if key_field == index['field'] and key_type == 'text':
                                        has_text_index = True
                                        break

                            else:
                                for key_field, key_type in idx_info.get('key', {}).items():
                                    if key_field == index['field'] and key_type == 'text':
                                        has_text_index = True
                                        break

                        if not has_text_index:
                            await collection.create_index([(index['field'], 'text')], **index_options)
                        else:
                            print(f"Text index for field {index['field']} already exists, skipping creation.")
                    elif index_type == 'wildcard':
                        # Индекс с подстановочным знаком
                        await collection.create_index([(index['field'], 'wildcard')], **index_options)
                    else:
                        # Если тип не указан, создаем индекс по умолчанию - восходящий
                        await collection.create_index([(index['field'], 1)], **index_options)
                except Exception as e:
                    if 'IndexOptionsConflict' in str(e):
                        print(f"Index conflict detected for {index_config['database']}.{index_config['collection']}.{index_name}, skip.")
                    else:
                        print(f"Failed to create index {index_name}: {e}")
                    


def check():
    print("Starting initialization checks...")
    time_counter('mongo_prepare', 'Подготовка MongoDB')

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

    print("Starting database check...")
    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(check_db(mongo_client)) # Проверка базы данных на наличие коллекций
    print("Database check completed.")

    time_counter('mongo_prepare', 'Подготовка MongoDB')