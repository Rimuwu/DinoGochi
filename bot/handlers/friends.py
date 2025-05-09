from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.data_format import escape_markdown, list_to_inline
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino, create_dino_connection
from bot.modules.logs import log
from bot.modules.managment.events import get_event
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler, ChooseCustomHandler, ChooseFriendHandler, ChooseIntHandler, ChoosePagesStateHandler, ChooseStepHandler, ChooseStringHandler
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, DinoStepData, StepMessage
from bot.modules.user.friends import get_frineds, insert_friend_connect, get_friend_data
from bot.modules.items.item import AddItemToUser, get_name
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import cancel_markup, confirm_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import user_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
# from bot.modules.states_tools import (ChooseConfirmState, ChooseCustomState,
#                                       ChooseIntState, ChoosePagesState,
#                                       ChooseStepState, ChooseStringState, start_friend_menu)
from bot.modules.user.user import take_coins, user_name
from aiogram.types import CallbackQuery, Message
from bot.modules.market.market import seller_ui

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from aiogram import F

users = DBconstructor(mongo_client.user.users)
friends = DBconstructor(mongo_client.user.friends)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
events = DBconstructor(mongo_client.other.events)
sellers = DBconstructor(mongo_client.market.sellers)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.friends.add_friend'))
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

            friend_lang = await get_lang(friendid)
            await user_notification(friendid, 'send_request', friend_lang, user_name=user_name)
        else:
            text = t('add_friend.already', lang)
            await bot.send_message(chatid, text, 
                                reply_markup= await m(userid, 'last_menu', lang))

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('add_friend'))
async def add_friend_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]
    transmitted_data = {'code': code, 
                        'user_name': await user_name(user_id), 
                        'chatid': chatid}

    text = t(f'add_friend.var_messages.{code}', lang)
    await bot.send_message(chatid, text, reply_markup=cancel_markup(lang))

    # await ChooseCustomState(add_friend_end, friend_add_handler, 
    #                         user_id, chatid, lang, 
    #                         transmitted_data)

    await ChooseCustomHandler(add_friend_end, friend_add_handler,
                            user_id, chatid, lang, 
                            transmitted_data).start()

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.friends.friends_list'))
async def friend_list(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(chatid, t('friend_list.wait', lang))
    # await start_friend_menu(None, userid, chatid, lang, False)
    
    await ChooseFriendHandler(None, userid, chatid, lang, False).start()


async def adp_requests(data: dict, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']

    if data['action'] == 'delete': 
        await friends.delete_one(
            {
                'userid': data['friend'],
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
            {
                'userid': data['friend'],
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
        friend_res = await get_friend_data(friend_id, userid)
        if friend_res:
            a += 1

            name = friend_res['name']
            if name in options: name = name + str(a)

            options[f"✅ {a}"] = {'action': 'add', 
                                 'friend': friend_id, 
                                 'key': a, 'name': name}

            options[name] = {'action': 'pass'}

            options[f"❌ {a}"] = {'action': 'delete', 
                                 'friend': friend_id, 'key': a, 
                                 'name': name}

    # await ChoosePagesState(
    #     adp_requests, userid, chatid, lang, options, 
    #     horizontal=3, vertical=3,
    #     autoanswer=False, one_element=False)
    await ChoosePagesStateHandler(
        adp_requests, userid, chatid, lang, options, 3, 3, 
        autoanswer=False,one_element=False).start()

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.friends.requests'))
async def requests_list(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(chatid, t('requests.wait', lang))
    await request_open(userid, chatid, lang)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('requests'))
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

    transmitted_data['friendid'] = friendid

    # await ChooseConfirmState(delete_friend, userid, chatid, lang, True, transmitted_data)
    await ChooseConfirmHandler(delete_friend, userid, chatid, lang, True, transmitted_data).start()
    
    await bot.send_message(chatid, t('friend_delete.confirm', lang,     
                                     name=transmitted_data['key']), 
                           reply_markup=confirm_markup
                           (lang))

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.friends.remove_friend'))
async def remove_friend(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    friends = await get_frineds(userid)
    requests = friends['friends']
    options = {}
    a = 0

    for friend_id in requests:
        friend_res = await get_friend_data(friend_id, userid)
        if friend_res:
            a += 1

            name = friend_res['name']
            if name in options: name = name + str(a)
            options[name] = friend_id

    await bot.send_message(chatid, t('friend_delete.delete_info', lang))
    # await ChoosePagesState(
    #     adp_delte, userid, chatid, lang, options, 
    #     autoanswer=False, one_element=True)
    await ChoosePagesStateHandler(
        adp_delte, userid, chatid, lang, options, autoanswer=False, one_element=True).start()

async def joint(return_data: dict, 
                transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    friendid = transmitted_data['friendid']
    username = transmitted_data['username']
    dino_id: ObjectId = return_data['dino']
    dino = await Dino().create(dino_id)

    if not dino:
        text = t('css.no_dino', lang)
        await bot.send_message(chatid, text, reply_markup=await m(userid, 'last_menu', lang))
        return

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
@main_router.callback_query(IsPrivateChat(), F.data.startswith('joint_dinosaur'))
async def joint_dinosaur(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    # steps = [
    #     {"type": 'bool', 'name': 'check',
    #      "data": {'cancel': True},
    #      'translate_message': True,
    #      'message': {'text': 'joint_dinosaur.check',
    #      'reply_markup': confirm_markup(lang)
    #                 }
    #     },
    #     {"type": 'dino', 'name': 'dino',
    #      "data": {'add_egg': False, 'all_dinos': False},
    #      "message": {}
    #     }
    # ]
    
    steps = [
        ConfirmStepData('check', StepMessage(
            'joint_dinosaur.check', markup=confirm_markup(lang), translate_message=True),
            cancel=True
        ),
        
        DinoStepData('dino', StepMessage(
            'joint_dinosaur.dino', markup=confirm_markup(lang), translate_message=True),
            add_egg=False, all_dinos=False
        ),
    ]

    # await ChooseStepState(joint, userid, chatid, lang, steps, 
    #                       {'friendid': int(data[1]), 'username': await user_name(userid)})
    
    await ChooseStepHandler(
        joint, userid, chatid, lang, steps,
        {'friendid': int(data[1]), 'username': await user_name(userid)}).start()

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('take_dino'))
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
                text_to_owner = t('take_dino.message_to_owner', lang, dinoname=dino['name'], username=await user_name(userid))
                if owner: await bot.send_message(owner, text_to_owner)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('take_money'))
async def take_money(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    friendid = int(data[1])
    user = await users.find_one({'userid': userid}, comment='take_money')

    if user:
        max_int = user['coins']
        if max_int > 0:
            # await ChooseIntState(transfer_coins, userid, chatid, lang, 
            #                     max_int=max_int, transmitted_data={
            #                         'friendid': friendid, 
            #                         'username': await user_name(userid)})
            await ChooseIntHandler(
                transfer_coins, userid, chatid, lang,
                max_int=max_int, transmitted_data={
                    'friendid': friendid, 
                    'username': await user_name(userid)}).start()

            text = t('take_money.col_coins', lang, max_int=max_int)
            await bot.send_message(chatid, text, reply_markup=
                                count_markup(max_int, lang))
        else:
            text = t('take_money.zero_coins', lang)
            await bot.send_message(chatid, text)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('take_coins'))
async def take_super_coins(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    friendid = int(data[1])
    user = await users.find_one({'userid': userid}, comment='take_super_coins')

    if user:
        max_int = user['super_coins']
        if max_int > 0:
            # await ChooseIntState(transfer_super_coins, userid, 
            #                      chatid, lang, 
            #                     max_int=max_int, transmitted_data={
            #                         'friendid': friendid, 
            #                         'username': await user_name(userid)})
            await ChooseIntHandler(
                transfer_super_coins, userid, chatid, lang,
                max_int=max_int, transmitted_data={
                    'friendid': friendid, 
                    'username': await user_name(userid)}).start()

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
                                        user_name=await user_name(userid))
            else:
                text = t('add_friend.already', lang)
                await bot.answer_callback_query(call.id, text)
    else:
        await bot.answer_callback_query(call.id, '❌')

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('new_year'))
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

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('change_friend_name'))
async def change_name(call: CallbackQuery):

    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    friendid = int(data[1])
    user = await users.find_one({'userid': userid}, comment='change_name')

    if user:
        text = t('edit_friend_name', lang, none='none', name=await user_name(friendid))
        await bot.send_message(chatid, text, reply_markup=cancel_markup(lang))
        # await ChooseStringState(edit_name, userid, chatid, lang, max_len=30, transmitted_data={
        #     'friendid': friendid
        # })
        await ChooseStringHandler(
            edit_name, userid, chatid, lang, max_len=30, transmitted_data={
                'friendid': friendid
            }).start()


async def edit_name(new_name: str, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    friendid = transmitted_data['friendid']

    for i_key, f_key in [['friendid', 'userid'], ['userid', 'friendid']]:
            res = await friends.find_one({
                i_key: friendid,
                f_key: userid
            }, comment='get_friend_data_res')

            if res: break
    if res:
        if friendid == res['userid']: data_path = 'user'
        else: data_path = 'friend'

        if new_name == 'none':
                await friends.update_one({'_id': res['_id']}, 
                                        {'$set': {f'{data_path}_data.name': ''}}, 
                                        comment='edit_name')
                await bot.send_message(chatid, '✅', 
                                    reply_markup=await m(userid, 'last_menu', lang))
                return

        new_name = escape_markdown(new_name)
        if new_name:
            await friends.update_one({'_id': res['_id']}, 
                                        {'$set': {f'{data_path}_data.name': new_name}}, 
                                        comment='edit_name')
            await bot.send_message(chatid, '✅', 
                                    reply_markup=await m(userid, 'last_menu', lang))
            return

    await bot.send_message(chatid, '❌', 
                            reply_markup=await m(userid, 'last_menu', lang))

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('open_market'))
async def open_market_friend(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    friendid = int(call.data.split()[1])
    text, markup, img = await seller_ui(friendid, lang, False)
    if text:
        try:
            await bot.send_photo(chatid, img, caption=text, parse_mode="Markdown", reply_markup=markup)
        except:
            await bot.send_photo(chatid, img, caption=text, reply_markup=markup, parse_mode=None)
    else:
        await bot.send_message(chatid, '❌', 
                    reply_markup=await m(userid, 'last_menu', lang))
