
from bot.config import mongo_client
from bot.const import GAME_SETTINGS as gs
from bot.modules.data_format import random_code
from bot.modules.user.friends import insert_friend_connect
from bot.modules.items.item import AddItemToUser

from bot.modules.overwriting.DataCalsses import DBconstructor
referals = DBconstructor(mongo_client.user.referals)
users = DBconstructor(mongo_client.user.users)

async def get_referal_award(userid: int):
    """ Выдаёт награду за переход по рефералу
    """
    coins = gs['referal']['coins']
    items = gs['referal']['items']

    await users.update_one({'userid': userid}, 
                        {'$inc': {'coins': coins}}, comment='get_referal_award')
    for item in items: await AddItemToUser(userid, item)
    
async def create_referal(userid: int, code: str = ''):
    """ Создаёт связь между кодом и владельцем, 
        если не указан код, генерирует его
    """

    if not await referals.find_one({'userid': userid, 'type': 'general'}, comment='create_referal_1'):
        if not code: 
            while not code:
                c = random_code(10)
                if not await referals.find_one({'code': code}, comment='create_referal_code'): code = c

        data = {
            'code': code,
            'userid': userid,
            'type': 'general'
        }

        await referals.insert_one(data, comment='create_referal')
        return True, code
    return False, ''

async def get_code_owner(code: str):
    """ Получает создателя реферального кода
    """
    return await referals.find_one({'code': code, 'type': 'general'}, comment='get_code_owner')

async def get_user_code(userid: int):
    """ Получить код созданный пользователем
    """
    return await referals.find_one({'userid': userid, 'type': 'general'}, comment='get_user_code')

async def get_user_sub(userid: int):
    """ Получить активированный пользователем код
    """
    return await referals.find_one({'userid': userid, 'type': 'sub'}, comment='get_user_sub')

async def connect_referal(code: str, userid: int):
    """ Создаёт связь между пользователем и активированным кодом 
    """
    if not await referals.find_one({'userid': userid, 'type': 'sub'}, comment='connect_referal'):
        code_creator = await get_code_owner(code)
        if code_creator:
            if code_creator['userid'] != userid:
                data = {
                    'code': code,
                    'userid': userid,
                    'type': 'sub'
                }
                await referals.insert_one(data, comment='connect_referal')

                await insert_friend_connect(userid, code_creator['userid'], 'friends')
                await get_referal_award(userid)
                return True
    return False
