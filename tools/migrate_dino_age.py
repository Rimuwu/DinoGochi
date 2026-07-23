"""
Скрипт миграции возраста динозавров на отдельное поле created_at.
Для всех динозавров без поля created_at вычисляет timestamp из ObjectId generation_time.
"""
import asyncio
import sys
import os

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def migrate():
    from bot.dbmanager import mongo_client, init_beanie_odm
    from bot.models.dinosaur import Dino, DeadDino

    print('Инициализация MongoDB и Beanie...')
    await init_beanie_odm(mongo_client._real_client)

    print('Поиск живых динозавров для миграции created_at...')
    all_dinos = await Dino.find().to_list()
    migrated_count = 0

    for dino in all_dinos:
        if not getattr(dino, 'created_at', 0):
            try:
                gen_ts = int(dino.id.generation_time.timestamp())
            except Exception:
                import time
                gen_ts = int(time.time())
            await dino.set_created_at(gen_ts)
            migrated_count += 1

    print('Поиск мёртвых динозавров для миграции created_at...')
    dead_dinos = await DeadDino.find().to_list()
    dead_migrated = 0
    for dead in dead_dinos:
        if not getattr(dead, 'created_at', 0):
            try:
                gen_ts = int(dead.id.generation_time.timestamp())
            except Exception:
                import time
                gen_ts = int(time.time())
            dead.created_at = gen_ts
            await dead.save()
            dead_migrated += 1

    print(f'✅ Миграция завершена!\nЖивых динозавров: {len(all_dinos)} (обновлено {migrated_count})\nМёртвых динозавров: {len(dead_dinos)} (обновлено {dead_migrated}).')



if __name__ == '__main__':
    asyncio.run(migrate())
