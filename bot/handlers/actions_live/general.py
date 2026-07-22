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

async def build_active_dino_keyboard(user: User, lang: str):
    dinos = await user.get_dinos()
    last_dinos = await user.get_last_dinos()
    selected_ids = [str(d.id) for d in last_dinos]
    is_multi = user.settings.get('dino_multi_mode', False)

    buttons = []
    # Row 0: Multi-mode switch
    switch_btn = {
        "text": t('edit_dino_button.multi_switch', lang),
        "callback_data": "activ_dino_mode_switch"
    }
    if is_multi:
        switch_btn["style"] = "primary"
    buttons.append([switch_btn])

    # Rows 1+: Dino buttons
    name_counts = {}
    for element in dinos:
        name_counts[element.name] = name_counts.get(element.name, 0) + 1

    name_indices = {}
    dino_row = []
    for element in dinos:
        name = element.name
        if name_counts[name] > 1:
            name_indices[name] = name_indices.get(name, 0) + 1
            txt = f'🦕 {name} ({name_indices[name]})'
        else:
            txt = f'🦕 {name}'

        btn_data = {
            "text": txt,
            "callback_data": f'activ_dino_toggle {element.alt_id}'
        }
        if str(element.id) in selected_ids:
            btn_data["style"] = "primary"
        dino_row.append(btn_data)

        if len(dino_row) == 2:
            buttons.append(dino_row)
            dino_row = []
    if dino_row:
        buttons.append(dino_row)

    if is_multi:
        buttons.append([{
            "text": t('edit_dino_button.done', lang),
            "callback_data": "activ_dino_done"
        }])

    return list_to_inline(buttons)


@main_router.message(
    IsPrivateChat(),
    StartWith('commands_name.action_ask.dino_button')
)
async def edit_dino_buttom(message: Message):
    """ Изменение активного динозавра (команда) """
    user_id = message.from_user.id
    user = await User().create(user_id)
    lang = await get_lang(user_id)

    inline = await build_active_dino_keyboard(user, lang)
    await message.answer(t('edit_dino_button.edit', lang), reply_markup=inline)


@main_router.callback_query(IsPrivateChat(), F.data == 'activ_dino_mode_switch')
async def switch_mode_calb(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_lang(user_id)
    user = await User().create(user_id)

    is_multi = user.settings.get('dino_multi_mode', False)
    user.settings['dino_multi_mode'] = not is_multi
    await user.save()

    inline = await build_active_dino_keyboard(user, lang)
    try:
        await callback.message.edit_reply_markup(reply_markup=inline)
    except Exception: pass
    await callback.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('activ_dino_toggle'))
async def toggle_dino_calb(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_lang(user_id)
    user = await User().create(user_id)
    data = callback.data.split()[1]

    dino = await Dino.find_one(Dino.alt_id == data)
    if not dino:
        await callback.answer(t('edit_dino_button.notfouned', lang), show_alert=True)
        return

    is_multi = user.settings.get('dino_multi_mode', False)
    last_dinos = await user.get_last_dinos()
    current_ids = [d.id for d in last_dinos]

    if not is_multi:
        await user.update_last_dino(dino.id)
        try:
            await bot.delete_message(user_id, callback.message.message_id)
        except Exception: pass
        await bot.send_message(
            user_id,
            t('edit_dino_button.susseful', lang, name=dino.name),
            reply_markup=await m(user_id, 'actions_menu', lang, True)
        )
        await callback.answer()
    else:
        if dino.id in current_ids:
            if len(current_ids) <= 1:
                await callback.answer(t('edit_dino_button.min_one', lang), show_alert=True)
                return
            current_ids.remove(dino.id)
        else:
            if len(current_ids) >= 6:
                await callback.answer(t('edit_dino_button.max_six', lang), show_alert=True)
                return
            current_ids.append(dino.id)

        await user.update_last_dino(current_ids)
        inline = await build_active_dino_keyboard(user, lang)
        try:
            await callback.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
        await callback.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'activ_dino_done')
async def done_dino_calb(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_lang(user_id)
    user = await User().create(user_id)

    try:
        await bot.delete_message(user_id, callback.message.message_id)
    except Exception: pass

    last_dinos = await user.get_last_dinos()
    await bot.send_message(
        user_id,
        t('edit_dino_button.selected_count', lang, count=len(last_dinos)),
        reply_markup=await m(user_id, 'actions_menu', lang, True)
    )
    await callback.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('activ_dino '))
async def answer_edit_legacy(callback: CallbackQuery):
    """ Изменение последнего динозавра (кнопка) """
    user_id = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    user = await User().create(user_id)

    message = callback.message
    data = callback.data.split()[1]

    try:
        await bot.delete_message(user_id, message.message_id)
    except Exception: pass
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