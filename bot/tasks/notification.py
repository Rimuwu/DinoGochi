from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.logs import log
from bot.modules.notifications import notification_manager
from bot.taskmanager import add_task
from bot.modules.dinosaur.dinosaur  import Dino
from asyncio import sleep

from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

async def dino_notifications():
    dinos = await dinosaurs.find({}, comment='dino_notifications_dinos')
    for dino in dinos:
        try:
            dino_id = dino['_id']
            for stat in dino['stats']:

                if dino['stats']['heal'] <= 0:
                    dino_cl = await Dino().create(dino['_id'])
                    await dino_cl.dead()
                    continue

                unit = dino['stats'][stat]
                res = await notification_manager(dino_id, stat, unit)
                if res: await sleep(0.2)

        except Exception as e:
            log(f'dino_notifications error {e}', 2)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(dino_notifications, 30, 10.0)