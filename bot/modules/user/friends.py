from bot.models.user import Friend
from bot.models.user import User


from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline
from bot.modules.localization import t, get_lang
 
from bot.modules.logs import log

async def get_frineds(userid: int) -> dict:
    """ Получает друзей (id) и запросы к пользователю

        Return
        { 'friends': [],
          'requests': [] }
    """
    friends_dict = {
        'friends': [],
        'requests': []
    }
    
    conns = await Friend.find({
        '$or': [
            {'userid': userid},
            {'friendid': userid}
        ]
    }).to_list()

    for conn in conns:
        c_type = conn.type
        c_user = conn.userid
        c_friend = conn.friendid
        
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

    res = await Friend.find_one(
        Friend.userid == userid,
        Friend.friendid == friendid,
        Friend.type == action
    )

    res2 = await Friend.find_one(
        Friend.userid == friendid,
        Friend.friendid == userid,
        Friend.type == action
    )

    if not res and not res2:
        friend_conn = Friend(
            userid=userid,
            user_data={'name': user_name},
            friendid=friendid,
            friend_data={'name': friend_name},
            type=action
        )
        await friend_conn.insert()
        if action == 'friends':
            from bot.modules.user.achievements import check_achievements
            await check_achievements(userid, "friends")
            await check_achievements(friendid, "friends")
        return friend_conn
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
    res = await Friend.find_one(Friend.friendid == friendid, Friend.userid == userid)
    if not res:
        res = await Friend.find_one(Friend.userid == friendid, Friend.friendid == userid)

    # Если данные есть, то смотрим, можем ли мы вернуть данные, а не запрашивать их из тг
    if res:
        friendUser = await User.find_one(User.userid == friendid)
        result = {}

        if friendUser:
            # Определяем где хранятся данные друга
            if friendid == res.userid:
                friend_data_dict = res.user_data
            else:
                friend_data_dict = res.friend_data

            if friend_data_dict and friend_data_dict.get('name'):
                result['name'] = friend_data_dict['name']
            else:
                result['name'] = friendUser.name

            if 'name' not in result or not result['name']:
                if not friendUser.name:
                    # Если имени нет, то запрашиваем его из тг
                    chat_user = await bot.get_chat_member(friendid, friendid)
                    if chat_user:
                        name = chat_user.user.first_name
                        await friendUser.set_name(name)
                        result['name'] = name
                else:
                    result['name'] = friendUser.name
        return result
    return {}
