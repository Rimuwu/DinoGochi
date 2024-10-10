

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, user_name
from bot.modules.localization import t, get_lang
 
from bot.modules.overwriting.DataCalsses import DBconstructor
friends = DBconstructor(mongo_client.user.friends)

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

async def insert_friend_connect(userid: int, friendid: int, action: str):
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
                'name': '',
                'avatar': ''
            },
            'friendid': friendid,
            'friend_data': {
                'name': '',
                'avatar': ''
            },
            'type': action
        }
        return await friends.insert_one(data, comment='insert_friend_connect')
    return False

async def send_action_invite(userid: int, friendid: int, action: str, dino_alt: str, lang: str):
    """ userid - отправитель
        friendid - тот кто присоединится к активности
    """
    chat_user, chat2_user = None, None

    try:
        chat_user = await bot.get_chat_member(userid, userid)
        username = user_name(chat_user.user)
    except: username = '-'

    chat2_user = await get_friend_data(friendid, userid)
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
        result = {}

        # Определяем где хранятся данные друга
        if friendid == res['userid']: data_path = 'user'
        else: data_path = 'friend'

        if f'{data_path}_data' in res:
            # Проверяем, что данные есть, иначе это старый формат и создаём данные 
            if res[f'{data_path}_data']['name']:
                # Проверясем, что есть имя 
                result['name'] = res[f'{data_path}_data']['name']

            if res[f'{data_path}_data']['avatar']:
                # Проверясем, что есть аватарку
                result['avatar'] = res[f'{data_path}_data']['avatar']

                if not await bot.get_file(result['avatar']):
                    # Файла уже не существует, удаляем данные для обновления
                    del result['avatar']

        if 'avatar' not in result or 'name' not in result:
            try:
                chat_user = await bot.get_chat_member(friendid, friendid)
                friend = chat_user.user
            except: return {} # Если нет данных, то возвращаем пустой словарь

            if friend:
                name = user_name(friend)
                result['name'] = name

                photos = await bot.get_user_profile_photos(friend.id, 
                                                            limit=1)
                if photos.photos:
                    photo_id = photos.photos[0][0].file_id
                    result['avatar'] = photo_id
                else: result['avatar'] = None

                # Обновляем данные
                await friends.update_one({'_id': res['_id']}, {
                    '$set': {
                        f'{data_path}_data': result
                    }
                })
        return result
    return {}
