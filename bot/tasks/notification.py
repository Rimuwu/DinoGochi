from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import Dino
from bot.config import conf
from bot.modules.logs import log
from bot.modules.notifications import notification_manager
from bot.taskmanager import add_task
from bot.models.dinosaur import Dino
import asyncio

import time
dinosaurs = LazyCollection(Dino)

# Ограничение параллельности для предотвращения пика RAM
_NOTIF_SEMAPHORE = asyncio.Semaphore(50)

async def dino_notifications_task(dinos):
    """Уведомления для отдельного чанка динозавров"""
    start_time = time.time()

    async def process_single_dino(dino):
        async with _NOTIF_SEMAPHORE:
            try:
                dino_id = dino['_id']
                for stat in dino['stats']:
                    if stat not in ['heal', 'eat', 'mood', 'energy', 'game']:
                        continue

                    if dino['stats']['heal'] <= 0:
                        dino_cl = await Dino().create(dino['_id'])
                        if dino_cl: await dino_cl.dead()
                        continue

                    unit = dino['stats'][stat]
                    res = await notification_manager(dino_id, stat, unit, dino_doc=dino)
                    if res: await asyncio.sleep(0.2)

            except Exception as e:
                log(f'dino_notifications dino_id: {dino.get("_id")} - {e}', 3)

    tasks = [process_single_dino(d) for d in dinos]
    await asyncio.gather(*tasks)


async def dino_notifications_shard(shard_num: int):
    """Отправка уведомлений для конкретного шарда (ID берутся из Redis)."""
    from bot.modules.shard_cache import get_shard_dino_ids
    shard_dino_ids = await get_shard_dino_ids(shard_num)
    if not shard_dino_ids:
        return
    # Загружаем только необходимые поля для снижения RAM
    dinos = await dinosaurs.find(
        {'_id': {'$in': shard_dino_ids}},
        projection={'stats': 1, 'notifications': 1, 'name': 1, 'alt_id': 1},
        comment=f'dino_notifications_shard_{shard_num}')
    await dino_notifications_task(dinos)

if __name__ != '__main__':
    if conf.active_tasks:
        shard_count = getattr(conf, 'shard_count', 16)
        interval = 30.0 / shard_count

        def make_notification_task(s_idx: int):
            async def dino_notifications_shard_idx():
                await dino_notifications_shard(s_idx)
            dino_notifications_shard_idx.__name__ = f"dino_notifications_shard_{s_idx}"
            return dino_notifications_shard_idx

        for shard_idx in range(shard_count):
            delay = 10.0 + shard_idx * interval
            add_task(make_notification_task(shard_idx), repeat_time=30.0, delay=delay)