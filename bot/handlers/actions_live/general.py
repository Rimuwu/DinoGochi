from bot.models.dinosaur import Dino
from bot.models.activity import  GameActivity

from bson import ObjectId
from bot.exec import main_router, bot
from bot.handlers.actions_live.game import start_game_ent
from bot.modules.data_format import list_to_inline
from bot.models.dinosaur import Dino
from bot.modules.user.friends import send_action_invite
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseDinoHandler, ChooseFriendHandler

from bot.modules.user.user import User
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import StartWith
from bot.filters.private import IsPrivateChat
from aiogram import F

@main_router.message(
    IsPrivateChat(),
    StartWith('commands_name.action_ask.dino_button')
    )
async def edit_dino_buttom(message: Message):
    """ Изменение последнего динозавра (команда)
    """
    user_id = message.from_user.id
    user = await User().create(user_id)
    dinos = await user.get_dinos()
    data_names = {}
    lang = await get_lang(message.from_user.id)

    name_counts = {}
    for element in dinos:
        name_counts[element.name] = name_counts.get(element.name, 0) + 1

    name_indices = {}
    for element in dinos:
        name = element.name
        if name_counts[name] > 1:
            name_indices[name] = name_indices.get(name, 0) + 1
            txt = f'🦕 {name} ({name_indices[name]})'
        else:
            txt = f'🦕 {name}'
        data_names[txt] = f'activ_dino {element.alt_id}'
    
    inline = list_to_inline([data_names], 2)
    await message.answer(t('edit_dino_button.edit', lang), 
                           reply_markup=inline)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('activ_dino'))
async def answer_edit(callback: CallbackQuery):
    """ Изменение последнего динозавра (кнопка)
    """
    user_id = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    user = await User().create(user_id)

    message = callback.message
    data = callback.data.split()[1]

    try:
        await bot.delete_message(user_id, message.message_id)
    except: pass
    dino = await Dino.find_one(Dino.alt_id == data)
    if dino:
        await user.update_last_dino(dino.id)
        await bot.send_message(user_id, 
                t('edit_dino_button.susseful', lang, name=dino.name),
                reply_markup= await m(user_id, 'actions_menu', lang, True))

async def invite_adp(friend, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    action = transmitted_data['action']
    dino_alt = transmitted_data['dino_alt']

    if isinstance(friend, dict):
        await send_action_invite(userid, friend['userid'], action, dino_alt, lang)
        await bot.send_message(chatid, t('back_text.actions_menu', lang), 
                       reply_markup= await m(userid, 'last_menu', lang))
    else:
        await send_action_invite(userid, friend.id, action, dino_alt, lang)
        # Возврат в меню
        await bot.send_message(chatid, t('back_text.actions_menu', lang), 
                       reply_markup= await m(userid, 'last_menu', lang))

@main_router.callback_query(IsPrivateChat(), F.data.startswith('invite_to_action'))
async def invite_to_action(callback: CallbackQuery):
    lang = await get_lang(callback.from_user.id)
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()

    transmitted_data = {
        'action': data[1],
        'dino_alt': data[2]
    }

    dino = await Dino.find_one(Dino.alt_id == data[2])
    if dino:
        res = await GameActivity.find_one(GameActivity.dino.id == dino.id)
        if res: 
            await ChooseFriendHandler(
                invite_adp, userid, chatid, lang, True, transmitted_data=transmitted_data).start()

            text = t('invite_to_action', lang)
            await bot.send_message(chatid, text)

async def join_adp(dino_ID: ObjectId, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    action = transmitted_data['action']
    friend_dino = transmitted_data['friend_dino']
    friend = transmitted_data['friendid']
    text = ''

    dino = await Dino().create(dino_ID)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    if dino.alt_id == friend_dino:
        text = t('join_to_action.one_dino', lang)
    elif await dino.status != 'pass':
        text = t('alredy_busy', lang)

    if text:
        await bot.send_message(chatid, text, 
                    reply_markup = await m(userid, 'last_menu', lang))

    else:
        if action == 'game':
            await start_game_ent(userid, chatid, lang, 
                                 dino, friend, True, friend_dino)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('join_to_action'))
async def join(callback: CallbackQuery):
    lang = await get_lang(callback.from_user.id)
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()

    action = data[1]
    friend_dino = data[2]
    friendid = data[3]

    dino = await Dino.find_one(Dino.alt_id == friend_dino)
    if dino:
        res = await GameActivity.find_one(GameActivity.dino.id == dino.id)
        if not res: 
            text = t('entertainments.join_end', lang)
            await bot.send_message(chatid, text)
        else:
            transmitted_data = {
                'action': action,
                'friend_dino': friend_dino,
                'friendid': friendid
            }

            await ChooseDinoHandler(join_adp, userid, chatid, lang, False, transmitted_data=transmitted_data).start()