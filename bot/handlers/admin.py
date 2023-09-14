from telebot.types import CallbackQuery, Message

from bot.config import mongo_client, conf
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.states_tools import start_friend_menu
from bot.modules.friends import get_frineds, insert_friend_connect
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import cancel_markup, confirm_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import user_notification
from bot.modules.states_tools import (ChooseConfirmState, ChooseCustomState,
                                      ChoosePagesState, ChooseDinoState, ChooseStepState, ChooseStringState)
from bot.modules.user import user_name, take_coins
from bot.modules.dinosaur import Dino, create_dino_connection
from bot.modules.states_tools import (ChooseOptionState, ChoosePagesState,
                                      ChooseStepState, prepare_steps, ChooseStringState)
from bot.modules.tracking import creat_track, get_track_pages, track_info
from bot.modules.promo import create_promo_start, get_promo_pages, promo_ui, use_promo
from time import time
from bot.modules.user import User, max_dino_col, award_premium
from bot.modules.over_functions import send_message


management = mongo_client.other.management
promo = mongo_client.other.promo

@bot.message_handler(pass_bot=True, commands=['s_message'], is_admin=True)
async def s_message(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    
    # Рассылка

@bot.message_handler(pass_bot=True, commands=['create_tracking'], is_admin=True)
async def create_tracking(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await ChooseStringState(create_track, userid, chatid, lang, 1, 0)
    await send_message(chatid, t("create_tracking.name", lang), parse_mode='Markdown')

async def create_track(name, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    res, text = await creat_track(name.lower()), '-'
    if res == 1:
        iambot = await bot.get_me()
        bot_name = iambot.username

        url = f'https://t.me/{bot_name}/?promo={name}'
        text = t("create_tracking.ok", lang, url=url)
    elif res == 0: text = 'error no document'
    elif res == -1: text = 'error name no find'
    elif res == -2: text = t("create_tracking.already", lang)

    await send_message(chatid, text, parse_mode='Markdown')

@bot.message_handler(pass_bot=True, commands=['tracking'], is_admin=True)
async def tracking(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = await get_track_pages()
    res = await ChoosePagesState(track_info_adp, userid, chatid, lang, options, one_element=False, autoanswer=False)
    await send_message(chatid, t("track_open", lang), parse_mode='Markdown')

async def track_info_adp(data, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, markup = await track_info(data, lang)
    await send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('track'), private=True)
async def track(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    code = split_d[2]

    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    res = await management.find_one({'_id': 'tracking_links'})
    if res:
        text = '-'
        if action == 'delete':
            text = t("track_delete", lang)
            await management.update_one({'_id': 'tracking_links'}, 
                                {'$unset': {f'links.{code}': 0}})

        elif action == 'clear':
            text = t("track_clear", lang)
            await management.update_one({'_id': 'tracking_links'}, 
                                {'$set': {f'links.{code}.col': 0}})

        await send_message(chatid, text)

@bot.message_handler(pass_bot=True, commands=['create_promo'], is_admin=True)
async def create_promo(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await create_promo_start(userid, chatid, lang)

@bot.message_handler(pass_bot=True, commands=['promos'], is_admin=True)
async def promos(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = await get_promo_pages()
    res = await ChoosePagesState(promo_info_adp, userid, chatid, lang, options, one_element=False, autoanswer=False)
    await send_message(chatid, t("promo_commands.promo_open", lang), parse_mode='Markdown')

async def promo_info_adp(code, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, markup = await promo_ui(code, lang)
    await send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('promo'))
async def promo_call(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[2]
    code = split_d[1]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    res = await promo.find_one({"code": code})
    if res:
        if action in ['activ', 'delete'] and userid in conf.bot_devs:

            if action == 'delete': 
                await promo.delete_one({'_id': res['_id']})
                await bot.delete_message(userid, call.message.id)

            elif action == 'activ':
                if not res['active']:
                    res['active'] = True

                    if res['time'] != 'inf':
                        res['time_end'] = int(time()) + res['time']
                        
                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            "time_end": res['time_end'],
                            'active': True
                        }})
                    else:
                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            'active': True
                        }})

                else:
                    res['active'] = False
                    if res['time'] != 'inf':
                        res['time'] = res['time_end'] - int(time())

                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            "time": res['time'],
                            'active': False
                        }})
                    else:
                        await promo.update_one({'_id': res['_id']}, {"$set": {
                            'active': False
                        }})

                text, markup = await promo_ui(code, lang)
                await bot.edit_message_text(text, userid, call.message.message_id, reply_markup=markup, parse_mode='markdown')

        elif action == 'use':
            status, text = await use_promo(code, userid, lang)
            await send_message(userid, text, parse_mode='Markdown')
    else:
        await send_message(userid, t('promo_commands.not_found', lang), parse_mode='Markdown')

@bot.message_handler(pass_bot=True, commands=['link_promo'])
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

            res = await promo.find_one({"code": promo_code})

            if res:

                fw = message.reply_to_message

                if fw != None:
                    fw_ms_id = fw.forward_from_message_id
                    fw_chat_id = fw.forward_from_chat.id
                    
                    but = {
                        but_name: f'promo_activ {promo_code} use'
                    }

                    markup_inline = list_to_inline([but])
                    await bot.edit_message_reply_markup(fw_chat_id, fw_ms_id, reply_markup=markup_inline)
                    await send_message(user.id, text_dict['create'])

            else:
                await send_message(user.id, text_dict['not_found'])

@bot.message_handler(commands=['inf_premium'], is_admin=True)
async def give_me_premium(message):
    msg_args = message.text.split()
    
    if len(msg_args) > 1:
        userid = int(msg_args[1])
    else:
        userid = message.from_user.id

    await award_premium(userid, 'inf')
    await send_message(message.from_user.id, 'ok')