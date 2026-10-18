"""
Скрипт миграции возраста динозавров на отдельное поле created_at.
Для всех динозавров без поля created_at вычисляет timestamp из ObjectId generation_time.
"""
import asyncio
import sys
import os
import time

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def migrate():
    from bot.dbmanager import mongo_client, init_beanie_odm

    print('Инициализация MongoDB и Beanie...')
    await init_beanie_odm(mongo_client._real_client)

    db = mongo_client._real_client["dinogochi"]

    print('Поиск живых динозавров для миграции created_at...')
    col_dinos = db["dinosaurs"]
    migrated_count = 0
    total_dinos = await col_dinos.count_documents({})

    cursor = col_dinos.find({"$or": [{"created_at": {"$exists": False}}, {"created_at": 0}]})
    async for doc in cursor:
        try:
            gen_ts = int(doc["_id"].generation_time.timestamp())
        except Exception:
            gen_ts = int(time.time())
        await col_dinos.update_one({"_id": doc["_id"]}, {"$set": {"created_at": gen_ts}})
        migrated_count += 1

    print('Поиск мёртвых динозавров для миграции created_at...')
    col_dead = db["dead_dinos"]
    dead_migrated = 0
    total_dead = await col_dead.count_documents({})

    dead_cursor = col_dead.find({"$or": [{"created_at": {"$exists": False}}, {"created_at": 0}]})
    async for dead in dead_cursor:
        try:
            gen_ts = int(dead["_id"].generation_time.timestamp())
        except Exception:
            gen_ts = int(time.time())
        await col_dead.update_one({"_id": dead["_id"]}, {"$set": {"created_at": gen_ts}})
        dead_migrated += 1

    print(f'✅ Миграция завершена!\nЖивых динозавров: {total_dinos} (обновлено {migrated_count})\nМёртвых динозавров: {total_dead} (обновлено {dead_migrated}).')


if __name__ == '__main__':
    asyncio.run(migrate())
