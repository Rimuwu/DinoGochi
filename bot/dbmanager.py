import asyncio
import os
import pprint
from typing import Dict

import motor.motor_asyncio
from bot.config import conf
from motor.core import AgnosticClient

from bot.const import GAME_SETTINGS


mongo_client = motor.motor_asyncio.AsyncIOMotorClient(conf.mongo_url)


# Проверка mongodb 
async def check_db(client: AgnosticClient):
    if not client.server_info():
        raise ConnectionError("Failed to connect to MongoDB server")

    print(f"{client.HOST}, mongo connected")

    print('Checking the database...')
    await create_collections(client)
    print('Collections checked.')

    print('Creating necessary documents...')
    await create_necessary_documents(client)
    print('Necessary documents created.')

    print('Creating indexes...')
    await check_and_create_indexes(client)
    print('Indexes created.')

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
                    'expireAfterSeconds': index.get('ttl'),
                }

                # Убираем None значения из опций
                index_options = {k: v for k, v in index_options.items() if v is not None}

                # Исключаем wildcardProjection, если тип индекса не wildcard
                if index['type'] == 'wildcard':
                    index_options['wildcardProjection'] = index.get('wildcardProjection')

                # Исключаем collation, если он пуст
                collation = index.get('collation')
                if collation:
                    index_options['collation'] = collation

                # Исключаем partialFilterExpression, если он пуст
                partial_filter_expression = index.get('partialFilterExpression')
                if partial_filter_expression:
                    # Удаляем $ne: null, оставляем только $exists: true
                    if '$ne' in partial_filter_expression.get('userid', {}):
                        partial_filter_expression = {"userid": {"$exists": True}}
                    index_options['partialFilterExpression'] = partial_filter_expression

                try:
                    if index['type'] in ['1', '-1', 1, -1]:
                        await collection.create_index([(index['field'], int(index['type']))], **index_options)
                    elif index['type'] == '2dsphere':
                        await collection.create_index([(index['field'], '2dsphere')], **index_options)
                    elif index['type'] == 'text':
                        # Проверяем, есть ли уже текстовый индекс
                        if any(idx.get('key', {}).get(index['field']) == 'text' for idx in existing_indexes.values()):
                            print(f"Text index for field {index['field']} already exists, skipping creation.")
                            continue
                        await collection.create_index([(index['field'], 'text')], **index_options)
                    elif index['type'] == 'wildcard':
                        await collection.create_index([(index['field'], 'wildcard')], **index_options)
                except Exception as e:
                    if 'IndexOptionsConflict' in str(e):
                        print(f"Index conflict detected for {index_config['database']}.{index_config['collection']}.{index_name}, skip.")
                    else:
                        print(f"Failed to create index {index_name}: {e}")
                    


def check():
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

    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(check_db(mongo_client)) # Проверка базы данных на наличие коллекций