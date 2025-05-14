
from random import randint

from bson import ObjectId

from bot.const import GAME_SETTINGS
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import chunks, escape_markdown, list_to_keyboard
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.localization import get_all_locales, get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import cancel_markup, confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.markup import tranlate_data
from bot.modules.overwriting.DataCalsses import DBconstructor
# from bot.modules.states_tools import (ChooseConfirmState, ChooseDinoState,
#                                       ChooseOptionState, ChooseStepState,
#                                       ChooseStringState)
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler, ChooseDinoHandler, ChooseOptionHandler, ChooseStepHandler, ChooseStringHandler
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, StepMessage, StringStepData
from bot.modules.user.user import User, take_coins
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command, StateFilter

from aiogram.fsm.context import FSMContext
import re

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

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings.notification'), 
                     IsAuthorizedUser())
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
    
    # await ChooseConfirmState(notification, userid, chatid, lang)
    await ChooseConfirmHandler(notification, userid, chatid, lang).start()
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

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings.dino_profile'), 
                     IsAuthorizedUser())
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
    # await ChooseOptionState(dino_profile, userid, chatid, lang, settings_data)
    await ChooseOptionHandler(dino_profile, userid, chatid, lang, settings_data).start()
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

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings.inventory'), 
                     IsAuthorizedUser())
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

    # await ChooseOptionState(inventory, userid, chatid, lang, settings_data)
    await ChooseOptionHandler(inventory, userid, chatid, lang, settings_data).start()
    await bot.send_message(userid, t('inv_set_pages.info', lang), 
                           reply_markup=keyboard)

async def rename_dino_post_state(content: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    dino_id = transmitted_data['dino']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    last_name = dino.name
    await dino.update({'$set': {'name': content}})

    text = t('rename_dino.rename', lang, 
             last_name=last_name, dino_name=content)
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))


async def transition(dino_id: ObjectId, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    text = t('rename_dino.info', lang, last_name=dino.name)
    keyboard = [t('buttons_name.cancel', lang)]
    markup = list_to_keyboard(keyboard, one_time_keyboard=True)

    data = {
        'dino': dino_id
    }

    # await ChooseStringState(rename_dino_post_state, userid, chatid, lang, max_len=20, transmitted_data=data)
    await ChooseStringHandler(rename_dino_post_state, userid, 
                            chatid, lang, max_len=20, transmitted_data=data).start()

    await bot.send_message(userid, text, reply_markup=markup)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings.dino_name'), 
                     IsAuthorizedUser())
async def rename_dino(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    # await ChooseDinoState(transition, userid, message.chat.id, lang, False)
    await ChooseDinoHandler(transition, userid, 
                            message.chat.id, lang, False).start()

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('rename_dino'), IsAuthorizedUser())
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
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return
    await transition(dino._id, trans_data)

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

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings.delete_me'), 
                     IsAuthorizedUser())
async def delete_me(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    code = str(randint(100, 1000))
    
    conf3 = confirm_markup(lang)
    conf3.one_time_keyboard = True

    # steps = [
    #     {
    #     "type": 'bool', "name": 'confirm', 
    #     "data": {'cancel': True}, 
    #     "translate_message": True,
    #     'message': {
    #         'text': 'delete_me.confirm', 
    #         'reply_markup': confirm_markup(lang)
    #         }
    #     },
    #     {
    #     "type": 'bool', "name": 'confirm2', 
    #     "data": {'cancel': True}, 
    #     "translate_message": True,
    #     'message': {
    #         'text': 'delete_me.dead_dino',
    #         'reply_markup': confirm_markup(lang)
    #         }
    #     },
    #     {
    #     "type": 'bool', "name": 'confirm3', 
    #     "data": {'cancel': True}, 
    #     "translate_message": True,
    #     'message': {
    #         'text': 'delete_me.rex_boss', 
    #         'reply_markup': conf3
    #         }
    #     },
    #     {"type": 'str', "name": 'code', "data": {}, 
    #         'message': {
    #             'text': t('delete_me.code', lang, code=code),
    #             'reply_markup': cancel_markup(lang)}
    #     }
    # ]
    
    steps = [
        ConfirmStepData('confirm', StepMessage('delete_me.confirm', 
                                            confirm_markup(lang), True),
                        cancel=True
                        ),
        ConfirmStepData('confirm2', StepMessage('delete_me.dead_dino', 
                                            confirm_markup(lang), True),
                        cancel=True
                        ),
        ConfirmStepData('confirm3', StepMessage('delete_me.rex_boss', 
                                            confirm_markup(lang), True),
                        cancel=True
                        ),
        StringStepData('code', StepMessage(t('delete_me.code', lang, code=code),
                                            cancel_markup(lang), False),
                        max_len=10
                        )
    ]

    await ChooseStepHandler(adapter_delete, userid, chatid, lang, steps,
                            transmitted_data={'code': code}).start()

    # await ChooseStepState(adapter_delete, userid, chatid, 
    #                               lang, steps, 
    #                             transmitted_data=transmitted_data)
    
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

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings2.my_name'), IsAuthorizedUser())
async def my_name(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    await bot.send_message(chatid, t('my_name.info', lang),
                               parse_mode='Markdown', 
                               reply_markup=cancel_markup(lang))

    # await ChooseStringState(my_name_end, userid, chatid, lang, max_len=20)
    await ChooseStringHandler(my_name_end, userid, chatid, lang, max_len=20).start()

async def lang_set(new_lang: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    await langs.update_one({'userid': userid}, 
                           {'$set': {'lang': new_lang}},
                           comment='lang_set')

    await bot.send_message(chatid, t('new_lang', new_lang),
                               reply_markup= await m(userid, 'last_menu', new_lang))

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings2.lang'), IsAuthorizedUser())
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

    # await ChooseOptionState(lang_set, userid, chatid, lang, options)
    await ChooseOptionHandler(lang_set, userid, chatid, lang, options).start()

async def dino_talk_set(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'no_talk.{result}', lang)
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    await users.update_one({'userid': userid}, 
                           {"$set": {'settings.no_talk': result}}, 
                           comment='no_talk_1'
                           )

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings2.dino_talk'), 
                     IsAuthorizedUser())
async def dino_talk(message: Message):
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

    # await ChooseConfirmState(dino_talk_set, userid, chatid, lang)
    await ChooseConfirmHandler(dino_talk_set, userid, chatid, lang).start()
    await bot.send_message(userid, t('no_talk.info', lang), 
                           reply_markup=keyboard)

async def my_nick_set(nick: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    nick = escape_markdown(nick)
    for i in list(nick):
        if i in ['\n', '\r', '\t', ' ', 'ᅠ']:
            nick = nick.replace(i, ' ')

    if 'ᅠ' in nick: nick.replace('ᅠ', '')

    if not nick.strip() or nick.isspace():
        await bot.send_message(chatid, t('null_nick', lang), 
                    reply_markup= await m(userid, 'last_menu', lang))
        return


    # Regex to allow only letters, numbers, emojis, and spaces
    if not re.match(r'^[\w\s\U0001F300-\U0001FAD6\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+$', nick):
        await bot.send_message(chatid, t('null_nick', lang), 
                    reply_markup= await m(userid, 'last_menu', lang))
        return

    if await take_coins(userid, -7500, True):
        await bot.send_message(chatid, t('new_nick', lang, nick=nick), 
                        reply_markup= await m(userid, 'last_menu', lang))
        await users.update_one({'userid': userid}, 
                            {"$set": {'name': nick}}, 
                            comment='my_nick_1'
                            )
    else:
        await bot.send_message(chatid, t('no_coins', lang), 
                        reply_markup= await m(userid, 'last_menu', lang))

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings2.nick'), 
                     IsAuthorizedUser())
async def my_nick(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    # await ChooseStringState(my_nick_set, userid, chatid, lang, max_len=20, min_len=3)
    await ChooseStringHandler(my_nick_set, userid, chatid, lang, max_len=20, min_len=3).start()
    await bot.send_message(userid, t('edit_nick', lang), 
                           reply_markup=cancel_markup(lang))

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings2.reset_avatar'), 
                     IsAuthorizedUser())
async def reset_avatar(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await users.update_one({'userid': userid}, 
                           {"$set": {'avatar': ''}}, 
                           comment='reset_avatar_1'
                           )
    await bot.send_message(chatid, t('reset_avatar', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))
    log(f'User {userid} reset avatar', 1)

async def confidentiality_set(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    price = GAME_SETTINGS['conf_set_price']
    
    have_coins = False
    user = await User().create(userid)
    if user.super_coins >= price:
        have_coins = True
        await user.update({'$inc': {'super_coins': -price}})

    if await user.premium or have_coins:

        text = t(f'confidentiality.{result}', lang)
        await bot.send_message(chatid, text, 
                        reply_markup= await m(userid, 'last_menu', lang))
        await users.update_one({'userid': userid}, 
                            {"$set": {'settings.confidentiality': result}}, 
                            comment='confidentiality_1'
                            )

    else:
        text = t(f'confidentiality.no_coins', lang,
                 price=price
                 )
        await bot.send_message(chatid, text, 
                        reply_markup= await m(userid, 'last_menu', lang))

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.settings2.confidentiality'), 
                     IsAuthorizedUser())
async def confidentiality(message: Message):
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

    await ChooseConfirmHandler(confidentiality_set, userid, chatid, lang).start()
    await bot.send_message(userid, t('confidentiality.info', lang,
                                     price=GAME_SETTINGS['conf_set_price']
                                     ), 
                           reply_markup=keyboard
                           )
