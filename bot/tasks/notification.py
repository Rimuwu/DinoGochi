from bot.config import conf, mongo_client
from bot.modules.notifications import notification_manager
from bot.taskmanager import add_task
from bot.modules.dinosaur import Dino

dinosaurs = mongo_client.dinosaur.dinosaurs

async def dino_notifications():
    dinos = await dinosaurs.find({}).to_list(None) 
    for dino in dinos:
        dino_id = dino['_id']
        for stat in dino['stats']:

            if dino['stats']['heal'] <= 0:
                dino_cl = await Dino().create(dino['_id'])
                await dino_cl.dead()
                continue

            unit = dino['stats'][stat]
            await notification_manager(dino_id, stat, unit)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(dino_notifications, 15, 10.0)