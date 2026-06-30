from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import Friend
from bot.models.user import User


from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline
from bot.modules.localization import t, get_lang
 
from bot.modules.logs import log
friends = LazyCollection(Friend)
users = LazyCollection(User)

async def get_frineds(userid: int) -> dict:
    """ Получает друзей (id) и запросы к пользователю

        Return\n
        { 'friends': [],
          'requests': [] }
    """
    friends_dict = {
        'friends': [],
        'requests': []
    }
    
    conns = await friends.find({
        '$or': [
            {'userid': userid},
            {'friendid': userid}
        ]
    }, comment='get_frineds_combined_opt')

    for conn in conns:
        c_type = conn.get('type')
        c_user = conn.get('userid')
        c_friend = conn.get('friendid')
        
        if c_type == 'friends':
            if c_user == userid:
                friends_dict['friends'].append(c_friend)
            else:
                friends_dict['friends'].append(c_user)
        elif c_type == 'request':
            # Запрос отправлен другому пользователю, userid является получателем (friendid)
            if c_friend == userid:
                friends_dict['requests'].append(c_user)

    return friends_dict

async def insert_friend_connect(userid: int, friendid: int, 
                                action: str, user_name: str = '', 
                                friend_name: str = ''):
    """ Создаёт связь между пользователями
        friends, request
    """
    assert action in ['friends', 'request'], f'Неподходящий аргумент {action}'

    res = await friends.find_one({
        'userid': userid,
        'friendid': friendid,
        'type': action
    }, comment='insert_friend_connect_res')

    res2 = await friends.find_one({
        'userid': friendid,
        'friendid': userid,
        'type': action
    }, comment='insert_friend_connect_res2')

    if not res and not res2:
        data = {
            'userid': userid,
            'user_data': {
                'name': user_name
            },
            'friendid': friendid,
            'friend_data': {
                'name': friend_name
            },
            'type': action
        }
        return await friends.insert_one(data, comment='insert_friend_connect')
    return False

async def send_action_invite(userid: int, friendid: int, action: str, dino_alt: str, lang: str):
    """ userid - отправитель
        friendid - тот кто присоединится к активности
    """
    chat2_user = await get_friend_data(friendid, userid)
    username = chat2_user['name'] # Имя друга / отправителя
    my = await bot.get_chat_member(userid, userid)
    my_name = f'@{my.user.username}'

    if chat2_user:
        friend_lang = await get_lang(friendid)
    else: friend_lang = 'en'

    send_text = t(f'send_action.{action}.send', friend_lang, 
                  username=my_name)
    button = t(f'send_action.{action}.send_button', friend_lang)
    markup = list_to_inline([
        {button: f'join_to_action {action} {dino_alt} {userid}'}])

    try:
        await bot.send_message(friendid, send_text, 
                               reply_markup=markup)
        ok = True
    except: ok = False

    if chat2_user and ok:
        for_me = t(f'send_action.{action}.for_me', lang, 
                   friendname=username)
        await bot.send_message(userid, for_me)
    else:
        await bot.send_message(userid, t('send_action.error', lang))

async def get_friend_data(friendid: int, userid: int):
    """
    Функция оптимизации получения данных пользователя

    Передаём id друга, чтобы найти его имя и аватарку,
    userid - id юзера
    """
    # Ищим данные друга
    for i_key, f_key in [['friendid', 'userid'], ['userid', 'friendid']]:
        res = await friends.find_one({
            i_key: friendid,
            f_key: userid
        }, comment='get_friend_data_res')
        if res: break

    # Если данные есть, то смотрим, можем ли мы вернуть данные, а не запрашивать их из тг
    if res:
        friendUser = await users.find_one({'userid': friendid}, comment='get_friend_data_friendUser')
        result = {}

        if friendUser:
            # Определяем где хранятся данные друга
            if friendid == res['userid']: data_path = 'user'
            else: data_path = 'friend'

            if f'{data_path}_data' in res:
                # Проверяем, что данные есть, иначе это старый формат и создаём данные 
                if res[f'{data_path}_data']['name']:
                    # Проверясем, что есть имя 
                    result['name'] = res[f'{data_path}_data']['name']
                else:
                    result['name'] = friendUser['name']

            else:
                result['name'] = friendUser['name']

            if 'name' not in result:
                if not friendUser['name']:
                    # Если имени нет, то запрашиваем его из тг
                    chat_user = await bot.get_chat_member(friendid, friendid)
                    if chat_user:
                        name = chat_user.user.first_name
                        await users.update_one({'userid': friendid}, 
                                            {'$set': {'name': name}}, comment='set_user_name_23')

                        result['name'] = name
        return result
    return {}
