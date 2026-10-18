from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import Egg
from bot.models.user import User
from math import e
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.models.dinosaur import Dino
from bot.modules.managment.tracking import update_all_user_track
from bot.modules.notifications import user_notification
from bot.modules.user.user import User
from bot.taskmanager import add_task
from bot.modules.localization import get_lang
from bot.exec import bot
from bson import ObjectId
from bot.modules.task_queue import task_handler

incubations = LazyCollection(Egg)
users = LazyCollection(User)

@task_handler("incubation")
async def incubation(data: dict):
    """Проверка инкубируемых яиц по ID из очереди задач"""
    egg_id = data.get("egg_id")
    if egg_id:
        await Egg.hatch(egg_id)

async def check_incubations():
    """Периодическая проверка и вылупление созревших яиц (failsafe для очереди задач)."""
    now = int(time())
    try:
        ready_eggs = await Egg.find(
            Egg.incubation_time <= now,
            Egg.stage == "incubation"
        ).to_list()
        for egg in ready_eggs:
            try:
                await Egg.hatch(egg)
            except Exception as e:
                from bot.modules.logs import log
                log(f"Ошибка при вылуплении яйца {egg.id}: {e}", lvl=3)
    except Exception as e:
        from bot.modules.logs import log
        log(f"Ошибка в check_incubations: {e}", lvl=3)

async def delete_choosing():
    """Проверка инкубируемых яиц
    """

    data = await incubations.find(
        {
            'start_choosing': {'$lte': int(time()) - 12 * 60 * 60},
            'stage': 'choosing',
            'id_message': {'$ne': 0}
        },
        comment='incubation_data'
    )

    for message_egg in data:
        #удаляем динозавра из инкубаций
        await incubations.delete_one({'_id': message_egg['_id']}, comment='incubation_2')

        if message_egg['id_message']:
            try:
                await bot.delete_message(message_egg['owner_id'], 
                                         message_egg['id_message'])
            except Exception as e: pass

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(check_incubations, 20.0, 5.0)
        add_task(delete_choosing, 3600.0, 15.0)