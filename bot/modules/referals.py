
from bot.config import mongo_client
from bot.const import GAME_SETTINGS as gs
from bot.modules.data_format import random_code
from bot.modules.friends import insert_friend_connect
from bot.modules.item import AddItemToUser

referals = mongo_client.user.referals
users = mongo_client.user.users

async def get_referal_award(userid: int):
    """ Выдаёт награду за переход по рефералу
    """
    coins = gs['referal']['coins']
    items = gs['referal']['items']

    await users.update_one({'userid': userid}, 
                        {'$inc': {'coins': coins}})
    for item in items: await AddItemToUser(userid, item)
    
async def create_referal(userid: int, code: str = ''):
    """ Создаёт связь между кодом и владельцем, 
        если не указан код, генерирует его
    """

    if not await referals.find_one({'userid': userid}):
        if not code: 
            while not code:
                c = random_code(10)
                if not await referals.find_one({'code': code}): code = c

        data = {
            'code': code,
            'userid': userid,
            'type': 'general'
        }

        await referals.insert_one(data)
        return True, code
    return False, ''

async def get_code_owner(code: str):
    """ Получает создателя реферального кода
    """
    return await referals.find_one({'code': code, 'type': 'general'})

async def get_user_code(userid: int):
    """ Получить код созданный пользователем
    """
    return await referals.find_one({'userid': userid, 'type': 'general'})

async def get_user_sub(userid: int):
    """ Получить активированный пользователем код
    """
    return await referals.find_one({'userid': userid, 'type': 'sub'})

async def connect_referal(code: str, userid: int):
    """ Создаёт связь между пользователем и активированным кодом 
    """
    if not await referals.find_one({'userid': userid, 'type': 'sub'}):
        code_creator = await get_code_owner(code)
        if code_creator:
            if code_creator['userid'] != userid:
                data = {
                    'code': code,
                    'userid': userid,
                    'type': 'sub'
                }
                await referals.insert_one(data)

                await insert_friend_connect(userid, code_creator['userid'], 'friends')
                await get_referal_award(userid)
                return True
    return False
