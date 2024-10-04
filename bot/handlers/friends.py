from ast import Is
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino, create_dino_connection
from bot.modules.managment.events import get_event
from bot.modules.user.friends import get_frineds, insert_friend_connect
from bot.modules.items.item import AddItemToUser, get_name
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import cancel_markup, confirm_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import user_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import (ChooseConfirmState, ChooseCustomState,
                                      ChooseIntState, ChoosePagesState,
                                      ChooseStepState, start_friend_menu)
from bot.modules.user.user import take_coins, user_name
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command

users = DBconstructor(mongo_client.user.users)
friends = DBconstructor(mongo_client.user.friends)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
events = DBconstructor(mongo_client.other.events)

@HDMessage
@main_router.message(Text('commands_name.friends.add_friend'), IsPrivateChat())
async def add_friend(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    text = t('add_friend.var', lang)
    buttons = get_data('add_friend.var_buttons', lang)

    inl_buttons = dict(zip(buttons.values(), buttons.keys()))
    markup = list_to_inline([inl_buttons])
    
    await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

async def friend_add_handler(message: Message, transmitted_data: dict):
    code = transmitted_data['code']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']

    content = str(message.text)
    text, status, friendid = '', False, 0

    if code == 'id':
        # Обработчик, проверяющий является ли контекст сообщения id
        if content.isdigit(): friendid = int(content)
        else: text = t('add_friend.check.nonint', lang, userid=userid)

    elif code == 'message':
        # Обработчик, проверяющий является ли сообщение пересылаемым кем то
        if message.forward_from: 
            friendid = message.forward_from.id
        else: text = t('add_friend.check.forward', lang)

    if friendid:
        result = await users.find_one({'userid': friendid}, comment='friend_add_handler')
        if result:
            if userid == friendid:
                text = t('add_friend.check.notyou', lang)
            else: status = True
        else:
            text = t('add_friend.check.nonbase', lang)

    if not status: await bot.send_message(chatid, text)
    return status, friendid
    
async def add_friend_end(friendid: int, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    user_name = transmitted_data['user_name']

    frineds = await get_frineds(userid)
    for act_type in ['friends', 'requests']:
        if friendid in frineds[act_type]:
            text = t(f'add_friend.check.{act_type}', lang)
            await bot.send_message(chatid, text)
            return
    else:
        res = await insert_friend_connect(userid, friendid, 'request')
        if res:
            text = t('add_friend.correct', lang)
            await bot.send_message(chatid, text, 
                                reply_markup= await m(userid, 'last_menu', lang))
            
            await user_notification(friendid, 'send_request', lang, user_name=user_name)
        else:
            text = t('add_friend.already', lang)
            await bot.send_message(chatid, text, 
                                reply_markup= await m(userid, 'last_menu', lang))

@HDCallback
@main_router.callback_query(F.data.startswith('add_friend'), IsPrivateChat())
async def add_friend_callback(call: CallbackQuery, state):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]
    transmitted_data = {'code': code, 'user_name': user_name(call.from_user)}

    text = t(f'add_friend.var_messages.{code}', lang)
    await bot.send_message(chatid, text, reply_markup=cancel_markup(lang))

    await ChooseCustomState(add_friend_end, state, friend_add_handler, 
                            user_id, chatid, lang, 
                            transmitted_data)

@HDMessage
@main_router.message(Text('commands_name.friends.friends_list'), IsPrivateChat())
async def friend_list(message: Message, state):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(chatid, t('friend_list.wait', lang))
    await start_friend_menu(None, state, userid, chatid, lang, False)


async def adp_requests(data: dict, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']

    if data['action'] == 'delete': 
        await friends.delete_one(
            {'userid': data['friend'],
             'friendid': userid,
             'type': 'request'
             }, comment='adp_requests_delete'
            )

        await bot.send_message(userid, t('requests.decline', lang, user_name=data['name']))
        return {'status': 'edit', 'elements': {'delete': [
            f'✅ {data["key"]}', f'❌ {data["key"]}', data['name']
            ]}}

    elif data['action'] == 'add':
        res = await friends.find_one(
            {'userid': data['friend'],
             'friendid': userid,
             'type': 'request'
             }, comment='adp_requests_add'
            )

        if res:
            await friends.update_one({'_id': res['_id']}, 
                               {'$set': {'type': 'friends'}}, comment='adp_requests_add_res')

        await bot.send_message(chatid, t('requests.accept', lang, user_name=data['name']))
        return {'status': 'edit', 'elements': {'delete': [
            f'✅ {data["key"]}', f'❌ {data["key"]}', data['name']
            ]}}

async def request_open(userid: int, chatid: int, lang: str):
    friends = await get_frineds(userid)
    requests = friends['requests']
    options = {}
    a = 0
    
    for friend_id in requests:
        try:
            chat_user = await bot.get_chat_member(friend_id, friend_id)
            friend = chat_user.user
        except: friend = None
        if friend:
            a += 1
            name = user_name(friend)
            if name in options: name = name + str(a)

            options[f"✅ {a}"] = {'action': 'add', 'friend': friend_id, 'key': a, 'name': name}
            
            options[name] = {'action': 'pass'}
            
            options[f"❌ {a}"] = {'action': 'delete', 'friend': friend_id, 'key': a, 'name': name}
    
    await ChoosePagesState(
        adp_requests, userid, chatid, lang, options, 
        horizontal=3, vertical=3,
        autoanswer=False, one_element=False)

@HDMessage
@main_router.message(Text('commands_name.friends.requests'), IsPrivateChat())
async def requests_list(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(chatid, t('requests.wait', lang))
    await request_open(userid, chatid, lang)

@HDCallback
@main_router.callback_query(F.data.startswith('requests'), IsPrivateChat())
async def requests_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    await bot.send_message(chatid, t('requests.wait', lang))
    await request_open(user_id, chatid, lang)

async def delete_friend(_: bool, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']

    friendid = transmitted_data['friendid']

    await friends.delete_one({"userid": userid, 'friendid': friendid, 'type': 'friends'}
                             , comment='delete_friend1')
    await friends.delete_one({"friendid": userid, 'userid': friendid, 'type': 'friends'}
                             , comment='delete_friend1')

    await bot.send_message(chatid, t('friend_delete.delete', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))

async def adp_delte(friendid: int, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    state = transmitted_data['state']

    transmitted_data['friendid'] = friendid

    await ChooseConfirmState(delete_friend, state, userid, chatid, lang, True, transmitted_data)
    await bot.send_message(chatid, t('friend_delete.confirm', lang,     
                                     name=transmitted_data['key']), 
                           reply_markup=confirm_markup
                           (lang))

@HDMessage
@main_router.message(Text('commands_name.friends.remove_friend'), IsPrivateChat())
async def remove_friend(message: Message, state):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    friends = await get_frineds(userid)
    requests = friends['friends']
    options = {}
    a = 0

    for friend_id in requests:
        try:
            chat_user = await bot.get_chat_member(friend_id, friend_id)
            friend = chat_user.user
        except: friend = None
        if friend:
            a += 1
            name = user_name(friend)
            if name in options: name = name + str(a)
            options[name] = friend_id

    await bot.send_message(chatid, t('friend_delete.delete_info', lang))
    await ChoosePagesState(
        adp_delte, state, userid, chatid, lang, options, 
        autoanswer=False, one_element=True)

async def joint(return_data: dict, 
                transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    friendid = transmitted_data['friendid']
    username = transmitted_data['username']
    dino: Dino = return_data['dino']

    res = await dino_owners.find({'dino_id': dino._id}, comment='joint_res')
    res2 = await dino_owners.find(
        {'owner_id': friendid, 'type': 'add_owner'}, comment='joint_res2')

    if len(list(res)) >= 2:
        text = t('joint_dinosaur.max_owners', lang)
    elif len(list(res2)) >= 1:
        text = t('joint_dinosaur.max_dino', lang)
    else:
        text = t('joint_dinosaur.ok', lang)

        friend_text = t('joint_dinosaur.message_to_friend', lang, username=username, dinoname=dino.name)
        transl_data = get_data('joint_dinosaur.button', lang)
        reply = list_to_inline([
            {transl_data[0]: f'take_dino {dino.alt_id}',
             transl_data[1]: "delete_message"
             }
        ])
        await bot.send_message(friendid, friend_text, reply_markup=reply)

    await bot.send_message(chatid, text, reply_markup= await m(userid, 'last_menu', lang))

@HDCallback
@main_router.callback_query(F.data.startswith('joint_dinosaur'), IsPrivateChat())
async def joint_dinosaur(call: CallbackQuery, state):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    steps = [
        {"type": 'bool', 'name': 'check',
         "data": {'cancel': True},
         'translate_message': True,
         'message': {'text': 'joint_dinosaur.check',
         'reply_markup': confirm_markup(lang)
                    }
        },
        {"type": 'dino', 'name': 'dino',
         "data": {'add_egg': False, 'all_dinos': False},
         "message": {}
        }
    ]

    await ChooseStepState(joint, state, userid, chatid, lang, steps, {'friendid': int(data[1]), 'username': user_name(call.from_user)})

@HDCallback
@main_router.callback_query(F.data.startswith('take_dino'), IsPrivateChat())
async def take_dino(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    dino_alt = data[1]
    await bot.delete_message(chatid, call.message.message_id)

    res2 = await dino_owners.find(
        {'owner_id': userid, 'type': 'add_owner'}, comment='take_dino_res2')
    if len(list(res2)) >= 1:
        text = t('take_dino.max_dino', lang)
        await bot.send_message(chatid, text)
    else:
        dino = await dinosaurs.find_one({'alt_id': dino_alt}, comment='take_dino_dino')
        if dino:
            res = await dino_owners.find({'dino_id': dino['_id']}, comment='take_dino_res')

            # Получение владельца
            owner = 0
            for i in list(res):
                if i['type'] == 'owner': owner = i['owner_id']
            
            if len(list(res)) >= 2:
                text = t('take_dino.max_owners', lang)
                await bot.send_message(chatid, text)
            else:
                # Сообщение и свзяь для дополнительного владельца
                await create_dino_connection(dino['_id'], userid, 'add_owner')
                text = t('take_dino.ok', lang, dinoname=dino['name'])
                await bot.send_message(chatid, text)

                # Сообщение для владульца дино
                text_to_owner = t('take_dino.message_to_owner', lang, dinoname=dino['name'], username=user_name(call.from_user))
                if owner: await bot.send_message(owner, text_to_owner)

@HDCallback
@main_router.callback_query(F.data.startswith('take_money'), IsPrivateChat())
async def take_money(call: CallbackQuery, state):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    friendid = int(data[1])
    user = await users.find_one({'userid': userid}, comment='take_money')

    if user:
        max_int = user['coins']
        if max_int > 0:
            await ChooseIntState(transfer_coins, state, userid, chatid, lang, 
                                max_int=max_int, transmitted_data={'friendid': friendid, 'username': user_name(call.from_user)})

            text = t('take_money.col_coins', lang, max_int=max_int)
            await bot.send_message(chatid, text, reply_markup=
                                count_markup(max_int, lang))
        else:
            text = t('take_money.zero_coins', lang)
            await bot.send_message(chatid, text)

@HDCallback
@main_router.callback_query(F.data.startswith('take_coins'), IsPrivateChat())
async def take_super_coins(call: CallbackQuery, state):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    friendid = int(data[1])
    user = await users.find_one({'userid': userid}, comment='take_super_coins')

    if user:
        max_int = user['super_coins']
        if max_int > 0:
            await ChooseIntState(transfer_super_coins, state, userid, 
                                 chatid, lang, 
                                max_int=max_int, transmitted_data={'friendid': friendid, 'username': user_name(call.from_user)})

            text = t('take_coins.col_coins', lang, max_int=max_int)
            await bot.send_message(chatid, text, reply_markup=
                                count_markup(max_int, lang))
        else:
            text = t('take_coins.zero_coins', lang)
            await bot.send_message(chatid, text)

async def transfer_coins(col: int, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    friendid = transmitted_data['friendid']
    username = transmitted_data['username']

    status = await take_coins(userid, -col, True)

    if status:
        text = t('take_money.send', lang)
        await bot.send_message(chatid, text, 
                            reply_markup= await m(userid, 'last_menu', lang))

        text = t('take_money.transfer', lang, username=username, coins=col)
        await bot.send_message(friendid, text)
        await take_coins(friendid, col, True)

    else:
        text = t('take_money.no_coins', lang)
        await bot.send_message(chatid, text, 
                            reply_markup= await m(userid, 'last_menu', lang))

async def transfer_super_coins(col: int, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    friendid = transmitted_data['friendid']
    username = transmitted_data['username']

    text = t('take_coins.send', lang)
    await bot.send_message(chatid, text, 
                        reply_markup= await m(userid, 'last_menu', lang))

    text = t('take_coins.transfer', lang, username=username, coins=col)
    await bot.send_message(friendid, text)

    await users.update_one({'userid': userid}, {'$inc': {'super_coins': -col}}, 
                           comment='transfer_super_coins')
    await users.update_one({'userid': friendid}, {'$inc': {'super_coins': col}}, 
                           comment='transfer_super_coins')

@HDCallback
@main_router.callback_query(F.data.startswith('send_request'), IsPrivateChat(False))
async def send_request(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    userid = call.from_user.id
    data = call.data.split()

    friendid = int(data[1])
    frineds = await get_frineds(userid)
    if friendid != userid:
        for act_type in ['friends', 'requests']:
            if friendid in frineds[act_type]:
                text = t(f'add_friend.check.{act_type}', lang)
                await bot.answer_callback_query(call.id, text)
                return
        else:
            res = await insert_friend_connect(userid, friendid, 'request')
            if res:
                text = t('add_friend.correct', lang)
                await bot.answer_callback_query(call.id, text)
                await user_notification(friendid, 'send_request', 
                                        user_name=user_name(call.from_user))
            else:
                text = t('add_friend.already', lang)
                await bot.answer_callback_query(call.id, text)
    else:
        await bot.answer_callback_query(call.id, '❌')

@HDCallback
@main_router.callback_query(F.data.startswith('new_year'), IsPrivateChat())
async def new_year(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    data = call.data.split()

    friendid = int(data[1])
    ev_data = await get_event("new_year")
    if ev_data:
        if friendid in ev_data['data']['send']:
            text = t('new_year.not', lang)
            await bot.answer_callback_query(call.id, text)
        else:
            text = t('new_year.ok', lang)
            await bot.answer_callback_query(call.id, text)

            await AddItemToUser(friendid, GAME_SETTINGS['new_year_item'])
            await events.update_one({"type": "new_year"}, 
                                    {"$push": {"data.send": friendid}}, comment='new_year')

            lang = await get_lang(friendid)
            text = t('new_year.to_friend', lang, 
                     item=get_name(GAME_SETTINGS['new_year_item'], lang))
            await bot.send_message(friendid, text)