

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline, user_name
from bot.modules.localization import t, get_lang

friends = mongo_client.user.friends
game_task = mongo_client.dino_activity.game

def get_frineds(userid: int) -> dict:
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
        data_list = list(friends.find({st: userid, 'type': 'friends'}))
        
        for conn_data in data_list:
            friends_dict['friends'].append(conn_data[alt[st]])

        if st == 'friendid':
            data_list = list(friends.find({st: userid, 'type': 'request'}))

            for conn_data in data_list:
                friends_dict['requests'].append(conn_data[alt[st]])
    return friends_dict

def insert_friend_connect(userid: int, friendid: int, action: str):
    """ Создаёт связь между пользователями
        friends, request
    """
    assert action in ['friends', 'request'], f'Неподходящий аргумент {action}'
    
    res = friends.find_one({
        'userid': userid,
        'friendid': friendid,
        'type': action
    })

    res2 = friends.find_one({
        'userid': friendid,
        'friendid': userid,
        'type': action
    })

    if not res and not res2:
        data = {
            'userid': userid,
            'friendid': friendid,
            'type': action
        }
        return friends.insert_one(data)
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

    try:
        chat2_user = await bot.get_chat_member(friendid, friendid)
        friend_lang = get_lang(chat2_user.user.id)
    except: friend_lang = lang

    send_text = t(f'send_action.{action}.send', friend_lang, 
                  username=username)
    button = t(f'send_action.{action}.send_button', friend_lang)
    markup = list_to_inline([{button: f'join_to_action {action} {dino_alt} {userid}'}])
    try:
        await bot.send_message(friendid, send_text, reply_markup=markup)
        ok = True
    except: ok = False

    if chat2_user and ok:
        for_me = t(f'send_action.{action}.for_me', lang, 
                   friendname=user_name(chat2_user.user))
        await bot.send_message(userid, for_me)
    else:
        await bot.send_message(userid, t('send_action.error', lang))