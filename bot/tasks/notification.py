from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.logs import log
from bot.modules.notifications import notification_manager
from bot.taskmanager import add_task
from bot.modules.dinosaur.dinosaur  import Dino
import asyncio
import math

from bot.modules.overwriting.DataCalsses import DBconstructor
import time
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

async def dino_notifications_task(dinos):
    """Уведомления для отдельного чанка динозавров"""
    start_time = time.time()

    for dino in dinos:
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
                res = await notification_manager(dino_id, stat, unit)
                if res: await asyncio.sleep(0.2)

        except Exception as e:
            log(f'dino_notifications dino_id: {dino_id} - {e}', 3)

    end_time = time.time()
    log(f'dino_notifications_task completed in {end_time - start_time:.2f} seconds', 1)

async def dino_notifications():
    """Главная функция уведомлений динозавров"""
    dinos = await dinosaurs.find({}, comment='dino_notifications_dinos')
    num_tasks = 16  # Количество тасков
    chunk_size = math.ceil(len(dinos) / num_tasks)

    tasks = [dino_notifications_task(dinos[i * chunk_size:(i + 1) * chunk_size]) for i in range(num_tasks)]
    await asyncio.gather(*tasks)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(dino_notifications, 30, 10.0)