from asyncio import sleep
from email import message
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, str_to_seconds, user_name_from_telegram
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log, latest_errors
from bot.modules.managment.events import add_event, create_event
from bot.modules.markup import confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.managment.promo import (create_promo_start, get_promo_pages, promo_ui,
                               use_promo)
from bot.modules.states_tools import (ChooseConfirmState, ChoosePagesState,
                                      ChooseStringState)
from bot.modules.managment.tracking import creat_track, delete_track, get_track_pages, track_info
from bot.modules.user.user import award_premium
from aiogram.types import CallbackQuery, Message, BufferedInputFile

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command

management = DBconstructor(mongo_client.other.management)
promo = DBconstructor(mongo_client.other.promo)
langs = DBconstructor(mongo_client.user.lang)
users = DBconstructor(mongo_client.user.users)

@HDMessage
@main_router.message(Command(commands=['create_tracking', 'create_track']), IsAdminUser())
async def create_tracking(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await ChooseStringState(create_track, userid, chatid, lang, 1, 0)
    await bot.send_message(chatid, t("create_tracking.name", lang), parse_mode='Markdown')

async def create_track(code, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    await creat_track(code, 'admin')
    text, markup = await track_info(code, lang)
    
    await bot.send_message(chatid, text, parse_mode='html', reply_markup=markup)

@HDMessage
@main_router.message(Command(commands=['tracking']), IsAdminUser())
async def tracking(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = await get_track_pages()
    res = await ChoosePagesState(track_info_adp, userid, chatid, lang, options, one_element=False, autoanswer=False)
    await bot.send_message(chatid, t("track_open", lang), parse_mode='html')

async def track_info_adp(data, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, markup = await track_info(data, lang)
    try:
        await bot.send_message(chatid, text, parse_mode='html', reply_markup=markup)
    except:
        await bot.send_message(chatid, text, reply_markup=markup)

@HDCallback
@main_router.callback_query(F.data.startswith('track'), IsPrivateChat())
async def track(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    code = split_d[2]

    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    res = await management.find_one({'_id': 'tracking_links'}, comment='track1')
    if res:
        text = '-'
        if action == 'delete':
            text = t("track_delete", lang)
            
            await delete_track(code)

        # elif action == 'view_users':
            
        # elif action == 'view_concern_links':

        # elif action == 'detailed_statistics':


        await bot.send_message(chatid, text)

@HDMessage
@main_router.message(Command(commands=['create_promo']), IsAdminUser())
async def create_promo(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await create_promo_start(userid, chatid, lang)

@HDMessage
@main_router.message(Command(commands=['promos']), IsAdminUser())
async def promos(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = await get_promo_pages()
    res = await ChoosePagesState(promo_info_adp, userid, chatid, lang, options, 
                                 one_element=False, autoanswer=False)
    await bot.send_message(chatid, t("promo_commands.promo_open", lang), parse_mode='Markdown')

async def promo_info_adp(code, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, markup = await promo_ui(code, lang)
    await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

@HDCallback
@main_router.callback_query(F.data.startswith('promo'))
async def promo_call(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[2]
    code = split_d[1]

    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    res = await promo.find_one({"code": code}, comment='promo_call_res')
    if res:
        if action in ['activ', 'delete'] and userid in conf.bot_devs:

            if action == 'delete': 
                await promo.delete_one({'_id': res['_id']}, comment='promo_call_delete')
                await bot.delete_message(userid, call.message.message_id)

            elif action == 'activ':
                if not res['active']:
                    res['active'] = True

                    if res['time'] != 'inf':
                        res['time_end'] = int(time()) + res['time']

                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            "time_end": res['time_end'],
                            'active': True
                        }}, comment='promo_call_activ')
                    else:
                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            'active': True
                        }}, comment='promo_call_121')

                else:
                    res['active'] = False
                    if res['time'] != 'inf':
                        res['time'] = res['time_end'] - int(time())

                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            "time": res['time'],
                            'active': False
                        }}, comment='promo_call_activ_false')
                    else:
                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            'active': False
                        }}, comment='promo_call_2')

                text, markup = await promo_ui(code, lang)
                await bot.edit_message_text(text, None, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')

        elif action == 'use':
            status, text = await use_promo(code, userid, lang)
            await bot.send_message(userid, text, parse_mode='Markdown')
    else:
        await bot.send_message(userid, t('promo_commands.not_found', lang), parse_mode='Markdown')

@HDMessage
@main_router.message(Command(commands=['link_promo']))
async def link_promo(message):
    user = message.from_user
    msg_args = message.text.split()
    lang = await get_lang(user.id)

    if user.id in conf.bot_devs:
        text_dict = get_data('promo_commands.link', lang)

        if len(msg_args) > 1:

            promo_code = msg_args[1]
            if len(msg_args) > 2:
                but_name = msg_args[2]
            else: but_name = '🎁'

            res = await promo.find_one({"code": promo_code}, comment='link_promo_res')

            if res:

                fw = message.reply_to_message

                if fw != None:
                    fw_ms_id = fw.forward_from_message_id
                    fw_chat_id = fw.forward_from_chat.id
                    
                    but = {
                        but_name: f'promo_activ {promo_code} use'
                    }

                    markup_inline = list_to_inline([but])
                    await bot.edit_message_reply_markup(None, fw_chat_id, fw_ms_id, reply_markup=markup_inline)
                    await bot.send_message(user.id, text_dict['create'])

            else:
                await bot.send_message(user.id, text_dict['not_found'])

@HDMessage
@main_router.message(Command(commands=['add_premium']), IsAdminUser())
async def add_premium(message):
    """
    Аргументы: /add_premium 0/userid None/str_time
    """
    msg_args = message.text.split()
    arg_list = msg_args[2:]

    tt = 'inf'
    if arg_list:
        tt = str_to_seconds(' '.join(arg_list))

    if msg_args[1] != '0':
        userid = int(msg_args[1])
    else: userid = message.from_user.id

    log(f'add_premium userid: {userid} time: {tt}', 4)

    await award_premium(userid, tt)
    await bot.send_message(message.from_user.id, 'ok')

@HDMessage
@main_router.message(Command(commands=['copy_m']), IsAdminUser())
async def copy_m(message):

    """
    Аргументы: /copy_m lang
    """
    msg_args = message.text.split()
    arg_list = msg_args[1:]

    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)

    fw = message.reply_to_message
    try:
        fw_chat_id = fw.forward_from_chat.id
        fw_ms_id = fw.forward_from_message_id
    except:
        fw_chat_id = fw.chat.id
        fw_ms_id = fw.id

    fw_reply = fw.reply_markup

    await bot.copy_message(chatid, fw_chat_id, fw_ms_id, reply_markup=fw_reply)

    trs_data = {
        'forward_chat': fw_chat_id,
        'forward_message': fw_ms_id,
        'markup': fw_reply,
        'to_lang': arg_list[0],
        'start_chat': chatid,
        'start_lang': lang
    }

    users_sends = await langs.find({'lang': arg_list[0]}, comment='copy_m_users_sends')

    await ChooseConfirmState(confirm_send, userid, chatid, lang, True, trs_data)
    await bot.send_message(chatid, f"Confirm the newsletter for {len(users_sends)} users with language {arg_list[0]}", reply_markup=confirm_markup(lang))

async def confirm_send(_, transmitted_data: dict):
    forward_chat = transmitted_data['forward_chat']
    forward_message = transmitted_data['forward_message']
    markup = transmitted_data['markup']
    to_lang = transmitted_data['to_lang']

    start_chat = transmitted_data['start_chat']
    start_lang = transmitted_data['start_lang']
    
    await bot.send_message(start_chat, f"🍡", reply_markup=await m(start_chat, 'last_menu', start_lang))

    users_sends = await langs.find({'lang': to_lang}, comment='confirm_send_users_sends')
    start_time = time()
    col = 0

    for user in users_sends:
        try:
            await bot.copy_message(user['userid'], forward_chat, forward_message, reply_markup=markup)
            col += 1
        except:
            await sleep(0.1)
            try:
                await bot.copy_message(user['userid'], forward_chat, forward_message, reply_markup=markup)
                col += 1
            except:
                await sleep(0.3)
                try:
                    await bot.copy_message(user['userid'], forward_chat, forward_message, reply_markup=markup)
                    col += 1
                except Exception as e:
                    log(f'[copy_m] error: {e}', 2) 

    await bot.send_message(start_chat, f"Completed in {round(time() - start_time, 2)}, sent for {col} / {len(users_sends)}")

@HDMessage
@main_router.message(Command(commands=['eval']), IsAdminUser())
async def evaling(message):

    msg_args = message.text.split()
    msg_args.pop(0)
    text = ' '.join(msg_args)

    try:
        result = await eval(text)
    except TypeError:
        result = eval(text)

    log(f"userid: {message.from_user.id} command: {text} result: {result}", 4)
    try:
        await bot.send_message(message.from_user.id, str(result))
    except:
        await bot.send_message(message.from_user.id, 'moretext')

@HDMessage
@main_router.message(Command(commands=['get_username']), IsAdminUser())
async def get_username(message):
    """
    Аргументы: /get_username userid
    """
    msg_args = message.text.split()

    try:
        chat_user = await bot.get_chat_member(msg_args[1], msg_args[1])
        user = chat_user.user
    except: user = None

    if user:
        await bot.send_message(message.from_user.id, user_name_from_telegram(user))
        await bot.send_message(message.from_user.id, str(user).replace("'", ''))
    else:
        await bot.send_message(message.from_user.id, "nouser")

@HDMessage
@main_router.message(Command(commands=['log']), IsAdminUser())
async def get_log(message):
    errors_text = ''
    for i in range(len(latest_errors)): 
        s = f"{i+1}) ```{latest_errors[i]}```\n"
        if len(errors_text + s) > 4096: 
            break
        errors_text += s
    if not errors_text: errors_text = 'Ошибок нет, так держать!'
    
    await bot.send_message(message.chat.id, errors_text, parse_mode='Markdown')

@main_router.message(Command(commands=['save_users']), IsAdminUser())
@HDMessage
async def save_users_handler(message: Message):
    cursor = await users.find({}, {"userid": 1})
    with open("bot/data/users.txt", "w", encoding="utf-8") as f:
        for doc in cursor:
            f.write(str(doc["userid"]) + "\n")
    await message.answer("User IDs saved.")

    with open("bot/data/users.txt", "rb") as f:
        await bot.send_document(message.chat.id, BufferedInputFile(f.read(), filename="users.txt"))

@main_router.message(Command(commands=['start_easter']), IsAdminUser())
@HDMessage
async def start_easter(message: Message):

    time_end = int(time()) + 86400 * 1

    events_lst = []
    add_hunting = await create_event('add_hunting', time_end)
    add_hunting['data']['items'] = ['easter_egg']
    events_lst.append(add_hunting)

    add_fishing = await create_event('add_fishing', time_end)
    add_fishing['data']['items'] = ['easter_egg']
    events_lst.append(add_fishing)

    add_collecting = await create_event('add_collecting', time_end)
    add_collecting['data']['items'] = ['easter_egg']
    events_lst.append(add_collecting)

    add_all = await create_event('add_all', time_end)
    add_all['data']['items'] = ['easter_egg']
    events_lst.append(add_all)

    for i in events_lst: await add_event(i, True)
    await bot.send_message(conf.bot_group_id, t("events.easter"))

@main_router.message(Command(commands=['count_items']), IsAdminUser())
@HDMessage
async def count_items(message: Message):
    
    msg_args = message.text.split()
    msg_args.pop(0)
    item_id = ' '.join(msg_args)
    
    find_items = await mongo_client.items.items.find({"items_data.item_id": item_id}).to_list(length=None)
    count = 0
    max_count, max_id_user = 0, 0
    for i in find_items:
        count += i['count']
        if i['count'] > max_count:
            max_count = i['count']
            max_id_user = i['userid']
    
    await bot.send_message(message.chat.id, f"Count: {count}\nMax: {max_count} ({max_id_user})")
