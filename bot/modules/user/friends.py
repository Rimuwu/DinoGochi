

from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline
from bot.modules.localization import t, get_lang
from bot.modules.user.user import user_name
 
from bot.modules.overwriting.DataCalsses import DBconstructor
friends = DBconstructor(mongo_client.user.friends)
users = DBconstructor(mongo_client.user.users)

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
    alt = {'friendid': 'userid', 
           'userid': 'friendid'
           }

    for st in ['userid', 'friendid']:
        data_list = await friends.find({st: userid, 
                                  'type': 'friends'}, comment='get_frineds_data_list')

        for conn_data in data_list:
            friends_dict['friends'].append(conn_data[alt[st]])

        if st == 'friendid':
            data_list = await friends.find({st: userid, 
                                      'type': 'request'}, comment='get_frineds_data_list_1')

            for conn_data in data_list:
                friends_dict['requests'].append(conn_data[alt[st]])
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

    if chat2_user:
        friend_lang = await get_lang(friendid)
    else: friend_lang = 'en'

    send_text = t(f'send_action.{action}.send', friend_lang, 
                  username=username)
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
                   friendname=chat2_user['name'])
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

            if 'name' not in result:
                if not friendUser['name']:
                    # Если имени нет, то используем id
                    name = await user_name(friendid)

                result['name'] = name

                # # Обновляем данные
                # if str(friendid) != name:
                    # await friends.update_one({'_id': res['_id']}, {
                    #     '$set': {
                    #         f'{data_path}_data.name': name
                    #     }
                    # }, comment='get_friend_data_update')
        return result
    return {}
