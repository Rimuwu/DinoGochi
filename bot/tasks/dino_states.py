
from time import time

from bot.config import conf, mongo_client
from bot.modules.dinosaur.dinosaur import mutate_dino_stat
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