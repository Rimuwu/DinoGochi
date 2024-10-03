
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.handlers.actions_live.game import start_game_ent
from bot.modules.data_format import list_to_inline
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino
from bot.modules.logs import log
from bot.modules.user.friends import send_action_invite
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import ChooseDinoState, start_friend_menu
from bot.modules.user.user import User
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text, StartWith
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F
from aiogram.fsm.context import FSMContext

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

@HDMessage
@main_router.message(StartWith('commands_name.action_ask.dino_button'))
async def edit_dino_buttom(message: Message):
    """ Изменение последнего динозавра (команда)
    """
    user_id = message.from_user.id
    user = await User().create(user_id)
    dinos = await user.get_dinos()
    data_names = {}
    lang = await get_lang(message.from_user.id)

    for element in dinos:
        txt = f'🦕 {element.name}'
        data_names[txt] = f'activ_dino {element.alt_id}'
    
    inline = list_to_inline([data_names], 2)
    await message.answer(t('edit_dino_button.edit', lang), 
                           reply_markup=inline)

@HDCallback
@main_router.callback_query(F.data.startswith('activ_dino'))
async def answer_edit(callback: CallbackQuery):
    """ Изменение последнего динозавра (кнопка)
    """
    user_id = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    user = await User().create(user_id)

    message = callback.message
    data = callback.data.split()[1]

    try:
        await bot.delete_message(user_id, message.id)
    except: pass
    dino = await dinosaurs.find_one({'alt_id': data}, {'_id': 1, 'name': 1}, comment='answer_edit_dino')
    if dino:
        await user.update({'$set': {'settings.last_dino': dino['_id']}})
        await bot.send_message(user_id, 
                t('edit_dino_button.susseful', lang, name=dino['name']),
                reply_markup= await m(user_id, 'actions_menu', lang, True))

async def invite_adp(friend, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    action = transmitted_data['action']
    dino_alt = transmitted_data['dino_alt']

    if isinstance(friend, dict):
        log(f'invite_adp error dict {friend}', 3)
    else:
        await send_action_invite(userid, friend.id, action, dino_alt, lang)
        # Возврат в меню
        await bot.send_message(chatid, t('back_text.actions_menu', lang), 
                       reply_markup= await m(userid, 'last_menu', lang))

@HDCallback
@main_router.callback_query(F.data.startswith('invite_to_action'), IsPrivateChat())
async def invite_to_action(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id)
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()

    transmitted_data = {
        'action': data[1],
        'dino_alt': data[2]
    }

    dino = await dinosaurs.find_one({'alt_id': data[2]}, comment='invite_to_action_dino')
    if dino:
        res = await long_activity.find_one({'dino_id': dino['_id'], 'activity_type': 'game'}, comment='invite_to_action_res')
        if res: 
            await start_friend_menu(invite_adp, state, userid, chatid, lang, True, transmitted_data)

            text = t('invite_to_action', lang)
            await bot.send_message(chatid, text, parse_mode='Markdown')

async def join_adp(dino: Dino, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    action = transmitted_data['action']
    friend_dino = transmitted_data['friend_dino']
    friend = transmitted_data['friendid']
    text = ''

    if dino.alt_id == friend_dino:
        text = t('join_to_action.one_dino', lang)
    elif await dino.status != 'pass':
        text = t('alredy_busy', lang)

    if text:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup= await m(userid, 'last_menu', lang))

    else:
        if action == 'game':
            await start_game_ent(userid, chatid, lang, 
                                 dino, friend, True, friend_dino)

@HDCallback
@main_router.callback_query(F.data.startswith('join_to_action'))
async def join(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id)
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()

    action = data[1]
    friend_dino = data[2]
    friendid = data[3]

    dino = await dinosaurs.find_one({'alt_id': friend_dino}, comment='join_dino')
    if dino:
        res = await long_activity.find_one({'dino_id': dino['_id'], 
                                    'activity_type': 'game'}, comment='join_res')
        if not res: 
            text = t('entertainments.join_end', lang)
            await bot.send_message(chatid, text)
        else:
            transmitted_data = {
                'action': action,
                'friend_dino': friend_dino,
                'friendid': friendid
            }

            await ChooseDinoState(join_adp, state, userid, chatid, lang, False, transmitted_data=transmitted_data)