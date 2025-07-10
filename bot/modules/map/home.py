from bot.const import GAME_SETTINGS as GS
from bot.dbmanager import mongo_client
from bot.modules.map.location import Location
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
        
        "upgrades": {
            "inventory": 1,
        }

    }

    res = await homes.find_one({'owner_id': user_id}, comment='create_home')
    if res:
        return res._id
    else:
        res = await homes.insert_one(dct, comment='create_home')
        return res.inserted_id

async def get_home(user_id: int):
    """ Получаем дом пользователя по его id """
    res = await homes.find_one({'owner_id': user_id}, comment='get_home')
    if res:
        return res
    else:
        return None

async def home_location(user_id: int):
    """ Получаем координаты дома пользователя """
    home = await get_home(user_id)
    if home:
        return Location(**home['location'])
    else:
        return None