from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import Dino, State

from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.models.dinosaur import Dino
from bot.taskmanager import add_task

states = LazyCollection(State)
dinosaurs = LazyCollection(Dino)

async def states_check():
    res_list = await states.find(
        {'last_check': {'$lte': int(time()) - 600}
         }
    )

    for state in res_list:

        if time() >= state['time_end']:
            await states.delete_one({'_id': state['_id']})
            continue

        dino = await dinosaurs.find_one({'_id': state['dino_id']})
        if dino:
            await Dino.mutate_stat(dino, 
                    state['char_edit'], state['char_unit'])

        await states.update_one({'_id': state['_id']}, {
            '$set': {
                'last_check': int(time())
                }
        })


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(states_check, 300.0, 30.0)