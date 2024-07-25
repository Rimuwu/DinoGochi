from random import randint

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.data_format import chunks, escape_markdown, list_to_keyboard
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.localization import get_all_locales, get_data, get_lang, t
from bot.modules.markup import cancel_markup, confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.markup import tranlate_data
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import (ChooseConfirmState, ChooseDinoState,
                                      ChooseOptionState, ChooseStepState,
                                      ChooseStringState)
from bot.modules.user.user import User
from telebot.types import CallbackQuery, Message

users = DBconstructor(mongo_client.user.users)
langs = DBconstructor(mongo_client.user.lang)

async def notification(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'not_set.{result}', lang)
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    await users.update_one({'userid': userid}, 
                           {"$set": {'settings.notifications': result}}, 
                           comment='notification_1'
                           )

@bot.message_handler(pass_bot=True, text='commands_name.settings.notification', 
                     is_authorized=True, private=True)
@HDMessage
async def notification_set(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    prefix = 'buttons_name.'
    buttons = [
        ['enable', 'disable'],
        ['cancel']
    ]
    translated = tranlate_data(buttons, lang, prefix)
    keyboard = list_to_keyboard(translated, 2)
    
    await ChooseConfirmState(notification, userid, chatid, lang)
    await bot.send_message(userid, t('not_set.info', lang), 
                           reply_markup=keyboard)

async def dino_profile(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    data = get_data('profile_view.ans', lang)
    text = t(f'profile_view.result', lang, res = data[result-1])
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 
                    'last_menu', lang))
    await users.update_one({'userid': userid}, 
                           {"$set": {'settings.profile_view': result}}, 
                           comment='dino_profile_1'
                           )

@bot.message_handler(pass_bot=True, text='commands_name.settings.dino_profile', 
                     is_authorized=True, private=True)
@HDMessage
async def dino_profile_set(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    settings_data, time_list = {}, []

    for i in get_data('profile_view.ans', lang):
        time_list.append(i)
        ind = time_list.index(i) + 1
        settings_data[i] = ind

    buttons = chunks(time_list, 2)
    buttons.append([t('buttons_name.cancel', lang)])

    keyboard = list_to_keyboard(buttons, 2)
    await ChooseOptionState(dino_profile, userid, chatid, lang, settings_data)
    await bot.send_message(userid, t('profile_view.info', lang), 
                           reply_markup=keyboard)


async def inventory(result: list, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'inv_set_pages.accept', lang, 
             gr = result[0], vr = result[1])

    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    await users.update_one({'userid': userid}, 
                           {"$set": {'settings.inv_view': result}}, 
                           comment='inventory_1'
                           )

@bot.message_handler(pass_bot=True, text='commands_name.settings.inventory', 
                     is_authorized=True, private=True)
@HDMessage
async def inventory_set(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    settings_data, time_list = {}, []

    for i in get_data('inv_set_pages.ans', lang):
        time_list.append(i)
        settings_data[i] = list(int(strn) for strn in i.split(' | '))

    buttons = chunks(time_list, 2)
    buttons.append([t('buttons_name.cancel', lang)])
    keyboard = list_to_keyboard(buttons, 2)

    await ChooseOptionState(inventory, userid, chatid, lang, settings_data)
    await bot.send_message(userid, t('inv_set_pages.info', lang), 
                           reply_markup=keyboard)

async def rename_dino_post_state(content: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    dino = transmitted_data['dino']

    last_name = dino.name
    await dino.update({'$set': {'name': content}})

    text = t('rename_dino.rename', lang, 
             last_name=last_name, dino_name=content)
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))


async def transition(dino: Dino, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t('rename_dino.info', lang, last_name=dino.name)
    keyboard = [t('buttons_name.cancel', lang)]
    markup = list_to_keyboard(keyboard, one_time_keyboard=True)

    data = {
        'dino': dino
    }
    await ChooseStringState(rename_dino_post_state, userid, 
                            chatid, lang, max_len=20, transmitted_data=data)

    await bot.send_message(userid, text, reply_markup=markup)

@bot.message_handler(pass_bot=True, text='commands_name.settings.dino_name', 
                     is_authorized=True, private=True)
@HDMessage
async def rename_dino(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await ChooseDinoState(transition, userid, message.chat.id, lang, False)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('rename_dino'), is_authorized=True, private=True)
@HDCallback
async def rename_button(callback: CallbackQuery):
    dino_data = callback.data.split()[1]
    lang = await get_lang(callback.from_user.id)
    userid = callback.from_user.id
    chatid = callback.message.chat.id

    trans_data = {
        'userid': userid,
        'chatid': chatid,
        'lang': lang
    }
    dino = await Dino().create(dino_data)
    await transition(dino, trans_data)

async def adapter_delete(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    if return_data['code'] != transmitted_data['code']:
        await bot.send_message(chatid, t('delete_me.incorrect_code', lang),     
                               parse_mode='Markdown', 
                               reply_markup= await m(userid, 'last_menu', lang))

    else:
        user = await User().create(userid)
        await user.full_delete()
        r = list_to_keyboard([t('commands_name.start_game', lang)])

        await bot.send_message(chatid, t('delete_me.delete', lang),     
                               parse_mode='Markdown', 
                               reply_markup=r)

    
@bot.message_handler(pass_bot=True, text='commands_name.settings.delete_me', 
                     is_authorized=True, private=True)
@HDMessage
async def delete_me(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    code = str(randint(100, 1000))
    transmitted_data = {'code': code, 'delete_steps': False}
    
    conf3 = confirm_markup(lang)
    conf3.one_time_keyboard = True

    steps = [
        {
        "type": 'bool', "name": 'confirm', 
        "data": {'cancel': True}, 
        "translate_message": True,
        'message': {
            'text': 'delete_me.confirm', 
            'reply_markup': confirm_markup(lang)
            }
        },
        {
        "type": 'bool', "name": 'confirm2', 
        "data": {'cancel': True}, 
        "translate_message": True,
        'message': {
            'text': 'delete_me.dead_dino',
            'reply_markup': confirm_markup(lang)
            }
        },
        {
        "type": 'bool', "name": 'confirm3', 
        "data": {'cancel': True}, 
        "translate_message": True,
        'message': {
            'text': 'delete_me.rex_boss', 
            'reply_markup': conf3
            }
        },
        {"type": 'str', "name": 'code', "data": {}, 
            'message': {
                'text': t('delete_me.code', lang, code=code),
                'reply_markup': cancel_markup(lang)}
        }
    ]
    
    await ChooseStepState(adapter_delete, userid, chatid, 
                                  lang, steps, 
                                transmitted_data=transmitted_data)
    
async def my_name_end(content: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    name = escape_markdown(content)
    
    await bot.send_message(chatid, t('my_name.end', lang,
                                     owner_name=name),
                               parse_mode='Markdown', 
                               reply_markup= await m(userid, 'last_menu', lang))

    await users.update_one({'userid': userid}, 
                           {'$set': {'settings.my_name': name}}, 
                           comment='my_name_end'
                           )

@bot.message_handler(pass_bot=True, text='commands_name.settings2.my_name', is_authorized=True, private=True)
@HDMessage
async def my_name(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    await bot.send_message(chatid, t('my_name.info', lang),
                               parse_mode='Markdown', 
                               reply_markup=cancel_markup(lang))

    await ChooseStringState(my_name_end, userid, chatid, lang, max_len=20)

async def lang_set(new_lang: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    await langs.update_one({'userid': userid}, 
                           {'$set': {'lang': new_lang}},
                           comment='lang_set')

    await bot.send_message(chatid, t('new_lang', new_lang),
                               reply_markup= await m(userid, 'last_menu', new_lang))

@bot.message_handler(pass_bot=True, text='commands_name.settings2.lang', is_authorized=True, private=True)
@HDMessage
async def lang(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    lang_data = get_all_locales('language_name')
    b_list = [list(lang_data.values()), []]
    b_list[1].append(t('buttons_name.cancel', lang))

    buttons = list_to_keyboard(b_list)
    options = dict(zip(lang_data.values(), lang_data.keys()))

    await bot.send_message(chatid, t('lang_set', lang),
                               reply_markup=buttons)

    await ChooseOptionState(lang_set, userid, chatid, lang, options)