
from bot.config import mongo_client
from bot.const import GAME_SETTINGS as gs
from bot.modules.data_format import random_code
from bot.modules.friends import insert_friend_connect
from bot.modules.item import AddItemToUser

referals = mongo_client.user.referals
users = mongo_client.user.users

def get_referal_award(userid: int):
    """ Выдаёт награду за переход по рефералу
    """
    coins = gs['referal']['coins']
    items = gs['referal']['items']

    users.update_one({'userid': userid}, 
                        {'$inc': {'coins': coins}})
    for item in items: AddItemToUser(userid, item)
    
def create_referal(userid: int, code: str = ''):
    """ Создаёт связь между кодом и владельцем, 
        если не указан код, генерирует его
    """

    if not referals.find_one({'userid': userid}):
        if not code: 
            while not code:
                c = random_code(10)
                if not referals.find_one({'code': code}): code = c

        data = {
            'code': code,
            'userid': userid,
            'type': 'general'
        }

        referals.insert_one(data)
        return True, code
    return False, ''

def get_code_owner(code: str):
    """ Получает создателя реферального кода
    """
    return referals.find_one({'code': code, 'type': 'general'})

def get_user_code(userid: int):
    """ Получить код созданный пользователем
    """
    return referals.find_one({'userid': userid, 'type': 'general'})

def get_user_sub(userid: int):
    """ Получить активированный пользователем код
    """
    return referals.find_one({'userid': userid, 'type': 'sub'})

def connect_referal(code: str, userid: int):
    """ Создаёт связь между пользователем и активированным кодом 
    """
    if not referals.find_one({'userid': userid, 'type': 'sub'}):
        code_creator = get_code_owner(code)
        if code_creator:
            if code_creator['userid'] != userid:
                data = {
                    'code': code,
                    'userid': userid,
                    'type': 'sub'
                }
                referals.insert_one(data)

                insert_friend_connect(userid, code_creator['userid'], 'friends')
                get_referal_award(userid)
                return True
    return False
