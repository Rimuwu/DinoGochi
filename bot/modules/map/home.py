from bot.const import GAME_SETTINGS as GS
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor

homes = DBconstructor(mongo_client.map.homes)

async def create_home(user_id: int):

    dct = {
        'owner_id': user_id,
        'location': {
            'island': GS['start_location']['island'],
            'x': GS['start_location']['x'],
            'y': GS['start_location']['y']
        },

    }

    res = await homes.find_one({'owner_id': user_id}, comment='create_home')
    if res:
        return res._id
    else:
        res = await homes.insert_one(dct, comment='create_home')
        return res.inserted_id