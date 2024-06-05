from bot.config import conf, mongo_client
from bot.modules.notifications import notification_manager
from bot.taskmanager import add_task
from bot.modules.dinosaur import Dino
from asyncio import sleep

dinosaurs = mongo_client.dinosaur.dinosaurs

async def dino_notifications():
    dinos = await dinosaurs.find({}).to_list(None) 
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
                if res: await sleep(0.5)

        except Exception as e: pass

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(dino_notifications, 30, 10.0)