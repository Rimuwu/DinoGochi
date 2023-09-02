from bot.config import conf, mongo_client
from bot.modules.notifications import notification_manager
from bot.taskmanager import add_task
from bot.modules.dinosaur import Dino

dinosaurs = mongo_client.dinosaur.dinosaurs

async def dino_notifications():
    dinos = dinosaurs.find({})
    for dino in dinos:
        dino_id = dino['_id']
        for stat in dino['stats']:

            if dino['stats']['heal'] <= 0:
                Dino(dino['_id']).dead()
                continue

            unit = dino['stats'][stat]
            await notification_manager(dino_id, stat, unit)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(dino_notifications, 10, 10.0)