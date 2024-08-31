
from time import time

from bson.objectid import ObjectId

from bot.config import mongo_client
from bot.modules.dinosaur.dinosaur import mutate_dino_stat

from bot.modules.overwriting.DataCalsses import DBconstructor
dino_states = DBconstructor(mongo_client.dinosaur.state)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

async def add_state(dino_id: ObjectId, char: str, unit: int, time_state: int):
    """ Выдача раз в 10 минут
    """

    data = {
        "dino_id": dino_id,
        "char_edit": char,
        "char_unit": unit, 

        "time_end": int(time()) + time_state,
        "last_check": int(time())
    }

    await dino_states.insert_one(data)

async def use_states(dino_id: ObjectId):

    res = await dino_states.find({'_id': dino_id})
    for state in res:
        dino = await dinosaurs.find_one({'_id': dino_id})
        if dino:
            await mutate_dino_stat(dino, 
                                   state['char_edit'], state['char_unit'])