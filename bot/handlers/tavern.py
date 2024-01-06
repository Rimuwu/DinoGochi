from datetime import datetime, timedelta
from time import time
from random import randint

from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from bot.config import conf, mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.dinosaur import Dino, random_dino, random_quality
from bot.modules.friends import get_frineds, insert_friend_connect
from bot.modules.item import counts_items, RemoveItemFromUser, CheckCountItemFromUser
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import cancel_markup, confirm_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.inline import inline_menu
from bot.modules.notifications import user_notification
from bot.modules.states_tools import (ChooseConfirmState, ChooseCustomState,
                                      ChooseDinoState, ChooseInlineState,
                                      ChoosePagesState, ChooseStepState)
from bot.modules.user import (AddItemToUser, check_name, daily_award_con,
                              take_coins, user_in_chat, get_dinos)
from bot.modules.over_functions import send_message

events = mongo_client.other.events

@bot.message_handler(pass_bot=True, text='commands_name.dino_tavern.events', is_authorized=True)
async def events_c(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    text = t('events.info', lang)

    res = list(await events.find({}).to_list(None))
    a = 0
    for event in res:
        a += 1

        if event['type'] == 'time_year':
            season = event['data']['season']
            event_text = t(f"events.time_year.{season}", lang)
        else: event_text = t(f"events.{event['type']}", lang)
        text += f'{a}. {event_text}\n\n'

    await send_message(chatid, text)

async def bonus_message(user, message, lang):
    userid = user.id

    add_text = ''
    award_data = GS['daily_award']
    markup_inline = InlineKeyboardMarkup()

    lvl1 = counts_items(award_data['lvl1']['items'], lang) \
        + f', ' + str(award_data['lvl1']['coins'])

    lvl2 = counts_items(award_data['lvl2']['items'], lang) \
        + f', ' + str(award_data['lvl2']['coins'])

    res = await user_in_chat(userid, -1001673242031)
    res2 = check_name(user)

    if res: add_text += t('daily_award.2', lang)
    else: add_text += t('daily_award.1', lang)
    if res2: add_text += t('daily_award.bonus', lang)

    text = t('daily_award.info', lang, lvl_1=lvl1, lvl_2=lvl2)
    if not res2:
        name_dino = f'{user.full_name} loves *DinoGochi* / {user.first_name} 🦕 *DinoGochi*'
        bonus = counts_items(award_data['bonus']['items'], lang) \
        + f', ' + str(award_data['bonus']['coins'])

        text += t('daily_award.bonus_text', lang, name_dino=name_dino, bonus=bonus)

    text += t('daily_award.lvl_now', lang) + add_text
    award = t('daily_award.buttons.activate', lang)

    if not res:
        url_b = t('daily_award.buttons.channel_url', lang)
        markup_inline.add(InlineKeyboardButton(text=url_b, 
                            url='https://t.me/DinoGochi'))
    if not res2:
        rename = t('daily_award.buttons.rename', lang)
        markup_inline.add(InlineKeyboardButton(text=rename, 
                            url='tg://settings/edit_profile'))

    markup_inline.add(InlineKeyboardButton(text=award, 
                            callback_data='daily_award'))

    photo = open('images/remain/taverna/dino_reward.png', 'rb')
    await bot.send_photo(message.chat.id, photo, 
            text, parse_mode='Markdown', reply_markup=markup_inline)

@bot.message_handler(pass_bot=True, text='commands_name.dino_tavern.daily_award', is_authorized=True)
async def bonus(message: Message):
    lang = await get_lang(message.from_user.id)
    user = message.from_user
    await bonus_message(user, message, lang)

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data == 'daily_message', is_authorized=True)
async def daily_message(callback: CallbackQuery):
    user = callback.from_user
    lang = await get_lang(callback.from_user.id)
    message = callback.message
    await bonus_message(user, message, lang)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data == 'daily_award', is_authorized=True)
async def daily_award(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    
    col = len(await get_dinos(userid))
    if not col:
        text = t('no_dinos', lang)
        await send_message(chatid, text)
        return

    if sec := await daily_award_con(userid):
        award_data = GS['daily_award']
        res = await user_in_chat(userid, -1001673242031)

        key, add_bonus = 'lvl1', check_name(callback.from_user)
        if res: key = 'lvl2'

        items, coins = [], 0
        items += award_data[key]['items']
        coins += award_data[key]['coins']
        if add_bonus:
            items += award_data['bonus']['items']
            coins += award_data['bonus']['coins']

        str_items = counts_items(items, lang)
        strtime = seconds_to_str(sec - int(time()), lang)

        text = t('daily_award.use', lang, time=strtime, 
                 items=str_items, coins=coins)
        await send_message(chatid, text, parse_mode='Markdown')

        for i in items: await AddItemToUser(userid, i)
        await take_coins(userid, coins, True)
    else:
        text = t('daily_award.in_base', lang)
        await send_message(chatid, text, parse_mode='Markdown')

@bot.message_handler(pass_bot=True, text='commands_name.dino_tavern.edit', is_authorized=True)
async def edit(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    text = t('edit_dino.info', lang)
    btn = get_data('edit_dino.buttons', lang)
    b_mark = dict(zip(btn.values(), btn.keys()))
    mark = list_to_inline([b_mark], 2)

    image = open('images/remain/taverna/transformation.png', 'rb')
    await bot.send_photo(chatid, image, text, parse_mode='Markdown', reply_markup=mark)

async def edit_appearance(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    dino: Dino = return_data['dino']

    coins_st = await take_coins(userid, -GS['change_appearance']['coins'])
    if coins_st:
        status = []
        for i in GS['change_appearance']['items']:
            st = await CheckCountItemFromUser(userid, 1, i)
            status.append(st)

        if all(status):
            await take_coins(userid, -GS['change_appearance']['coins'], True)
            for i in GS['change_appearance']['items']: await RemoveItemFromUser(userid, i)

            n_id = dino.data_id
            while n_id == dino.data_id: n_id = random_dino(dino.quality)
            await dino.update({'$set': {'data_id': n_id}})

            text = t('edit_dino.new', lang)
            await send_message(chatid, text, parse_mode='Markdown', 
                                   reply_markup=inline_menu('dino_profile', lang, dino_alt_id_markup=dino.alt_id))
            await send_message(chatid, t('edit_dino.return', lang), parse_mode='Markdown', 
                                   reply_markup= await m(userid, 'last_menu', lang))
            return

        else: text = t('edit_dino.no_items', lang)
    else: text = t('edit_dino.no_coins', lang)

    await send_message(chatid, text, parse_mode='Markdown', 
                           reply_markup= await m(userid, 'last_menu', lang))

async def end_edit(code, transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    dino: Dino = transmitted_data['dino']
    o_type = transmitted_data['type']

    m_id = transmitted_data['bmessageid']
    await bot.delete_message(chatid, m_id)
    
    coins = GS['change_rarity'][code]['coins']
    items = GS['change_rarity'][code]['materials']

    coins_st = await take_coins(userid, -coins)
    if coins_st:
        status = []
        for i in items:
            st = await CheckCountItemFromUser(userid, 1, i)
            status.append(st)

        if all(status):
            await take_coins(userid, -coins, True)
            for i in items: await RemoveItemFromUser(userid, i)

            if code == 'random': quality = random_quality()
            else: quality = code

            if o_type == 'all':
                n_id = dino.data_id
                while n_id == dino.data_id: n_id = random_dino(quality)
                await dino.update({'$set': {'data_id': n_id, 'quality': quality}})

            elif o_type == 'rare': 
                await dino.update({'$set': {'quality': quality}})

            text = t('edit_dino.new', lang)
            await send_message(chatid, text, parse_mode='Markdown', 
                                   reply_markup=inline_menu('dino_profile', lang, dino_alt_id_markup=dino.alt_id))

            await send_message(chatid, t('edit_dino.return', lang), parse_mode='Markdown', 
                                   reply_markup= await m(userid, 'last_menu', lang))
            return

        else: text = t('edit_dino.no_items', lang)
    else: text = t('edit_dino.no_coins', lang)

    await send_message(chatid, text, parse_mode='Markdown', 
                           reply_markup= await m(userid, 'last_menu', lang))


async def dino_now(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    dino: Dino = return_data['dino']
    o_type = transmitted_data['type']

    text = t(f'edit_dino.{o_type}', lang)
    buttons = {}
    code = randint(1000, 2000)

    for key, i in GS['change_rarity'].items():
        if dino.quality != key:
            text += f'{t("rare."+key+".2", lang)} {counts_items(i["materials"], lang)} + {i["coins"]} 🪙 ➞ 🦕 {t("rare."+key+".0", lang)}\n\n'
            buttons[f'{t("rare."+key+".2", lang)} {t("rare."+key+".1", lang)}'] = f'chooseinline {code} {key}'
    
    mark = list_to_inline([buttons], 2)
    await send_message(chatid, text, parse_mode='Markdown', reply_markup=mark)

    await ChooseInlineState(end_edit, userid, chatid, lang, str(code), {'dino': dino, 'type': o_type})
    await send_message(chatid,  t('edit_dino.new_rare', lang), parse_mode='Markdown', reply_markup=cancel_markup(lang))

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('transformation') , is_authorized=True)
async def transformation(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    data = callback.data.split()

    steps = [
            {
            "type": 'dino', "name": 'dino', "data": {"add_egg": False}, 
            "translate_message": True,
            'message': {'text': 'edit_dino.dino'}
            }
    ]
    ret_f = dino_now

    if data[1] == 'appearance':
        items_text = counts_items(GS['change_appearance']['items'], lang)
        coins = GS['change_appearance']['coins']
        ret_f = edit_appearance

        steps.append(
            {
            "type": 'bool', "name": 'confirm', 
            "data": {'cancel': True}, 
            'message': {
                'text': t('edit_dino.appearance', lang, items=items_text, coins=coins),
                'reply_markup': confirm_markup(lang)
                }
            }
        )

    await ChooseStepState(ret_f, userid, chatid, lang, steps, {'type': data[1]})
