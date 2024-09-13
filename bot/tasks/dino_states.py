
from random import choice, randint, uniform
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.data_format import transform
from bot.modules.dinosaur.dino_status import end_skill_activity
from bot.modules.dinosaur.dinosaur import Dino, mutate_dino_stat
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.mood import add_mood
from bot.modules.dinosaur.rpg_states import use_states
from bot.modules.dinosaur.skills import add_skill_point, check_skill
from bot.modules.dinosaur.works import end_work
from bot.modules.items.item import get_items_names
from bot.modules.items.item_tools import use_item
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang, t
from bot.modules.notifications import dino_notification
from bot.modules.user.user import get_inventory_from_i
from bot.taskmanager import add_task

from bot.modules.overwriting.DataCalsses import DBconstructor
states = DBconstructor(mongo_client.dinosaur.states)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

async def states_check():
    res_list = await states.find(
        {'last_check': {'$lte': int(time()) - 600}
         }
    )

    for state in res_list:

        dino = await dinosaurs.find_one({'_id': state['dino_id']})
        if dino:
            await mutate_dino_stat(dino, 
                    state['char_edit'], state['char_unit'])

        await states.update_one({'_id': state['_id']}, {
            '$set': {
                'last_check': int(time())
                }
        })


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(states_check, 300.0, 30.0)