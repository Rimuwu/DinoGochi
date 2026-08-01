from bot.models.user import Lang
from bot.models.user import User

from random import randint

from bson import ObjectId

from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.data_format import chunks, escape_markdown, list_to_keyboard, list_to_inline
from bot.models.dinosaur import Dino
from bot.modules.localization import get_all_locales, get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import cancel_markup, confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.markup import tranlate_data
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler, ChooseDinoHandler, ChooseOptionHandler, ChooseStepHandler, ChooseStringHandler
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, StepMessage, StringStepData
from bot.models.user import User
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F
import re


async def notification(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'not_set.{result}', lang)
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.notifications': result}})

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
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.profile_view': result}})

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

    await ChooseOptionHandler(dino_profile, userid, chatid, lang, settings_data).start()
    await bot.send_message(userid, t('profile_view.info', lang), 
                           reply_markup=keyboard)


async def inv_sort_setting_save(result: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    ans_list = get_data('inv_sort.ans', lang)
    keys_list = get_data('inv_sort.keys', lang)
    try:
        idx = keys_list.index(result)
        res_text = ans_list[idx]
    except Exception:
        res_text = result

    text = t('inv_sort.result', lang, res=res_text)
    await bot.send_message(chatid, text, 
                    reply_markup=await m(userid, 'last_menu', lang))
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.inv_sort': result}})

@main_router.message(IsPrivateChat(), Text('commands_name.settings.inv_sort'), 
                     IsAuthorizedUser())
async def inv_sort_setting_set(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    settings_data, time_list = {}, []
    ans_list = get_data('inv_sort.ans', lang)
    keys_list = get_data('inv_sort.keys', lang)

    for i, ans in enumerate(ans_list):
        time_list.append(ans)
        settings_data[ans] = keys_list[i]

    buttons = chunks(time_list, 2)
    buttons.append([t('buttons_name.cancel', lang)])
    keyboard = list_to_keyboard(buttons, 2)

    await ChooseOptionHandler(inv_sort_setting_save, userid, chatid, lang, settings_data).start()
    await bot.send_message(userid, t('inv_sort.info', lang), 
                           reply_markup=keyboard)



async def inventory(result: list, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'inv_set_pages.accept', lang, 
             gr = result[0], vr = result[1])

    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.inv_view': result}})

@main_router.message(IsPrivateChat(), Text('commands_name.settings.inventory'), 
                     IsAuthorizedUser())
async def inventory_set(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    settings_data, time_list = {}, []

    for i in get_data('inv_set_pages.data', lang):
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

    prompt_msg_id = transmitted_data.get('prompt_msg_id')
    user_msg_id = transmitted_data.get('umessageid')
    main_msg_id = transmitted_data.get('main_msg_id')
    return_page = transmitted_data.get('return_page', 'notif_dino')

    await clean_context_messages(chatid, prompt_msg_id, user_msg_id)
    await refresh_main_settings_message(userid, chatid, lang, main_msg_id, return_page)

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

    prompt_msg = await bot.send_message(userid, text, reply_markup=markup)

    data = {
        'dino': dino_id,
        'main_msg_id': transmitted_data.get('main_msg_id'),
        'prompt_msg_id': prompt_msg.message_id,
        'return_page': transmitted_data.get('return_page', 'notif_dino')
    }

    await ChooseStringHandler(rename_dino_post_state, userid, 
                            chatid, lang, max_len=20, transmitted_data=data).start()

@main_router.message(IsPrivateChat(), Text('commands_name.settings.dino_name'), 
                     IsAuthorizedUser())
async def rename_dino(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await ChooseDinoHandler(transition, userid, 
                            message.chat.id, lang, False).start()

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
                               reply_markup= await m(userid, 'last_menu', lang))

    else:
        user = await User.find_one(User.userid == userid)
        if user:
            await user.full_delete()

        # Set cooldown in Redis for 7 days (604800 seconds)
        from bot.redismanager import redis_set
        await redis_set(f"delete_cooldown:{userid}", 1, ex=604800)

        r = list_to_keyboard([t('commands_name.start_game', lang)])

        await bot.send_message(chatid, t('delete_me.delete', lang), 
                               reply_markup=r)

async def start_delete_me_flow(userid: int, chatid: int, lang: str):
    from bot.redismanager import get_redis
    from bot.modules.data_format import seconds_to_str

    r = get_redis()
    ttl = await r.ttl(f"delete_cooldown:{userid}")
    if ttl > 0:
        time_str = seconds_to_str(ttl, lang)
        await bot.send_message(chatid, 
            t('delete_me.cooldown', lang, time=time_str),
            reply_markup=await m(userid, 'last_menu', lang))
        return

    code = str(randint(100, 1000))
    
    conf3 = confirm_markup(lang)
    conf3.one_time_keyboard = True
    
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

@main_router.message(IsPrivateChat(), Text('commands_name.settings.delete_me'), 
                     IsAuthorizedUser())
async def delete_me(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    await start_delete_me_flow(userid, chatid, lang)


async def my_name_end(content: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    name = escape_markdown(content)

    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.my_name': name}})

    prompt_msg_id = transmitted_data.get('prompt_msg_id')
    user_msg_id = transmitted_data.get('umessageid')
    main_msg_id = transmitted_data.get('main_msg_id')
    return_page = transmitted_data.get('return_page', 'notif_dino')

    await clean_context_messages(chatid, prompt_msg_id, user_msg_id)
    await refresh_main_settings_message(userid, chatid, lang, main_msg_id, return_page)

    await bot.send_message(chatid, t('my_name.end', lang, owner_name=name), 
                           reply_markup=await m(userid, 'last_menu', lang))

@main_router.message(IsPrivateChat(), Text('commands_name.settings2.my_name'), IsAuthorizedUser())
async def my_name(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    prompt_msg = await bot.send_message(chatid, t('my_name.info', lang), reply_markup=cancel_markup(lang))
    trans_data = {
        'prompt_msg_id': prompt_msg.message_id,
        'return_page': 'notif_dino'
    }

    await ChooseStringHandler(my_name_end, userid, chatid, lang, max_len=20, transmitted_data=trans_data).start()

async def lang_set(new_lang: str, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    from bot.models.user import Lang
    await Lang.set_user_lang(userid, new_lang)

    await bot.send_message(chatid, t('new_lang', new_lang),
                               reply_markup= await m(userid, 'settings_menu', new_lang))

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
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.no_talk': result}})

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

    prompt_msg_id = transmitted_data.get('prompt_msg_id')
    user_msg_id = transmitted_data.get('umessageid')
    main_msg_id = transmitted_data.get('main_msg_id')
    return_page = transmitted_data.get('return_page', 'account')

    nick = escape_markdown(nick)
    for i in list(nick):
        if i in ['\n', '\r', '\t', ' ', 'ᅠ']:
            nick = nick.replace(i, ' ')

    if 'ᅠ' in nick: nick.replace('ᅠ', '')

    if not nick.strip() or nick.isspace() or not re.match(r'^[\w\s\U0001F300-\U0001FAD6\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+$', nick):
        await clean_context_messages(chatid, prompt_msg_id, user_msg_id)
        await bot.send_message(chatid, t('null_nick', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    from bot.modules.overwriting.DataCalsses import Transaction
    async with Transaction():
        user = await User.find_one(User.userid == userid)
        if user and await user.remove_coins(7500):
            await user.set_name(nick)
            await clean_context_messages(chatid, prompt_msg_id, user_msg_id)
            await refresh_main_settings_message(userid, chatid, lang, main_msg_id, return_page)
        else:
            await clean_context_messages(chatid, prompt_msg_id, user_msg_id)
            await bot.send_message(chatid, t('no_coins', lang), reply_markup=await m(userid, 'last_menu', lang))

@main_router.message(IsPrivateChat(), Text('commands_name.settings2.nick'), 
                     IsAuthorizedUser())
async def my_nick(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    prompt_msg = await bot.send_message(userid, t('edit_nick', lang), reply_markup=cancel_markup(lang))
    trans_data = {
        'prompt_msg_id': prompt_msg.message_id,
        'return_page': 'account'
    }
    await ChooseStringHandler(my_nick_set, userid, chatid, lang, max_len=20, min_len=3, transmitted_data=trans_data).start()

@main_router.message(IsPrivateChat(), Text('commands_name.settings2.reset_avatar'), 
                     IsAuthorizedUser())
async def reset_avatar(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'avatar': ''}})
    await bot.send_message(chatid, t('reset_avatar', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))
    log(f'User {userid} reset avatar', 1)

async def confidentiality_set(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    price = GAME_SETTINGS['conf_set_price']
    user = await User.find_one(User.userid == userid)
    premium_st = await user.premium

    have_coins = False
    if premium_st: have_coins = True

    if not have_coins and user.super_coins >= price:
        have_coins = True
        await user.update({'$inc': {'super_coins': -price}})
        log(f"Edit super_coins: user: {userid} col: {-price}", 1, "confidentiality_set")

    if have_coins:

        text = t(f'confidentiality.{result}', lang)
        await bot.send_message(chatid, text, 
                        reply_markup= await m(userid, 'last_menu', lang))
        user = await User.find_one(User.userid == userid)
        if user:
            await user.update({"$set": {'settings.confidentiality': result}})

    else:
        text = t(f'confidentiality.no_coins', lang,
                 price=price
                 )
        await bot.send_message(chatid, text, 
                        reply_markup= await m(userid, 'last_menu', lang))

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


async def rare_emoji_set(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'rare_emoji.{result}', lang)
    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.rare_emoji': result}})
        try:
            from bot.redismanager import get_redis
            redis = get_redis()
            await redis.set(f"user:rare_emoji:{userid}", "1" if result else "0")
        except Exception:
            pass

@main_router.message(IsPrivateChat(), Text('commands_name.settings3.rare_emoji'), 
                     IsAuthorizedUser())
async def rare_emoji_setting(message: Message):
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

    await ChooseConfirmHandler(rare_emoji_set, userid, chatid, lang).start()
    await bot.send_message(userid, t('rare_emoji.info', lang), 
                           reply_markup=keyboard)


async def only_emoji_set(result: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t(f'only_emoji.{result}', lang)
    await bot.send_message(chatid, text, 
                    reply_markup=await m(userid, 'last_menu', lang))
    user = await User.find_one(User.userid == userid)
    if user:
        await user.update({"$set": {'settings.only_emoji': result}})

@main_router.message(IsPrivateChat(), Text('commands_name.settings3.only_emoji'), 
                     IsAuthorizedUser())
async def only_emoji_setting(message: Message):
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

    await ChooseConfirmHandler(only_emoji_set, userid, chatid, lang).start()
    await bot.send_message(userid, t('only_emoji.info', lang), 
                           reply_markup=keyboard)


async def inv_columns_set(result: int, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t('inv_columns.result', lang, res=result)
    await bot.send_message(chatid, text, 
                    reply_markup=await m(userid, 'last_menu', lang))
    user = await User.find_one(User.userid == userid)
    if user:
        inv_view = user.settings.get('inv_view', [2, 3])
        inv_view[0] = result
        await user.update({"$set": {'settings.inv_view': inv_view}})

@main_router.message(IsPrivateChat(), Text('commands_name.settings3.inv_columns'), 
                     IsAuthorizedUser())
async def inv_columns_setting(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    options = ["1", "2", "3", "4", "5"]
    settings_data = {opt: int(opt) for opt in options}

    buttons = [options]
    buttons.append([t('buttons_name.cancel', lang)])
    keyboard = list_to_keyboard(buttons, 5)

async def clean_context_messages(chatid: int, *msg_ids):
    for mid in msg_ids:
        if mid:
            try:
                await bot.delete_message(chatid, mid)
            except Exception:
                pass

async def refresh_main_settings_message(userid: int, chatid: int, lang: str, main_msg_id: int | None, page: str = 'main'):
    user = await User.find_one(User.userid == userid)
    if not user:
        return
    text, inline_kb = await build_settings_page(user, page, lang)
    if main_msg_id:
        try:
            await bot.edit_message_text(text, chat_id=chatid, message_id=main_msg_id, reply_markup=inline_kb)
            return
        except Exception:
            pass
    reply_kb = await m(userid, 'settings_menu', lang)
    await bot.send_message(chatid, text, reply_markup=inline_kb)


async def build_settings_page(user: User, page: str, lang: str):
    settings = user.settings if user.settings else {}

    status_on = t('settings_menu.status_on', lang)
    status_off = t('settings_menu.status_off', lang)

    # Extract settings statuses
    notif = settings.get('notifications', True)
    notif_str = status_on if notif else status_off

    no_talk = settings.get('no_talk', False)
    talk_active = not no_talk
    talk_str = status_on if talk_active else status_off

    my_name = settings.get('my_name', '')
    if not my_name:
        my_name = t('owner', lang)

    lang_str = t('language_name', lang)

    prf_view_ans = get_data('profile_view.ans', lang)
    prf_view_idx = settings.get('profile_view', 1) - 1
    if 0 <= prf_view_idx < len(prf_view_ans):
        profile_view_str = prf_view_ans[prf_view_idx]
    else:
        profile_view_str = str(settings.get('profile_view', 1))

    keys_list = get_data('inv_sort.keys', lang)
    ans_list = get_data('inv_sort.ans', lang)
    curr_sort = settings.get('inv_sort', 'name_asc')
    if curr_sort in keys_list:
        inv_sort_str = ans_list[keys_list.index(curr_sort)]
    else:
        inv_sort_str = str(curr_sort)

    inv_columns_val = settings.get('inv_view', [2, 3])[0]
    inv_columns_str = str(inv_columns_val)

    inv_rows_val = settings.get('inv_view', [2, 3])[1]
    inv_rows_str = str(inv_rows_val)

    rare_emoji = settings.get('rare_emoji', True)
    rare_emoji_str = status_on if rare_emoji else status_off

    only_emoji = settings.get('only_emoji', False)
    only_emoji_str = status_on if only_emoji else status_off

    confidentiality = settings.get('confidentiality', False)
    conf_str = status_on if confidentiality else status_off

    buttons = []

    if page == 'main':
        text = t('settings_menu.title_main', lang,
                 notif=notif_str,
                 talk_mode=talk_str,
                 my_name=my_name,
                 lang=lang_str,
                 profile_view=profile_view_str,
                 inv_sort=inv_sort_str,
                 inv_columns=inv_columns_str,
                 inv_rows=inv_rows_str,
                 rare_emoji=rare_emoji_str,
                 only_emoji=only_emoji_str,
                 conf_mode=conf_str)
        buttons = [
            [{"text": t('settings_menu.buttons.notif_dino', lang), "callback_data": "settings_page notif_dino"}],
            [{"text": t('settings_menu.buttons.interface', lang), "callback_data": "settings_page interface"}],
            [{"text": t('settings_menu.buttons.account', lang), "callback_data": "settings_page account"}]
        ]
    elif page == 'notif_dino':
        text = t('settings_menu.title_notif_dino', lang,
                 notif=notif_str,
                 talk_mode=talk_str,
                 my_name=my_name)
        buttons = [
            [{"text": t('settings_menu.buttons.notifications', lang, status=notif_str), "callback_data": "settings_toggle notifications notif_dino"}],
            [{"text": t('settings_menu.buttons.talk_mode', lang, status=talk_str), "callback_data": "settings_toggle no_talk notif_dino"}],
            [{"text": t('settings_menu.buttons.my_name', lang), "callback_data": "settings_act my_name"}],
            [{"text": t('settings_menu.buttons.dino_name', lang), "callback_data": "settings_act dino_name"}],
            [{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page main"}]
        ]
    elif page == 'interface':
        text = t('settings_menu.title_interface', lang,
                 lang=lang_str,
                 profile_view=profile_view_str,
                 inv_sort=inv_sort_str,
                 inv_columns=inv_columns_str,
                 inv_rows=inv_rows_str,
                 rare_emoji=rare_emoji_str,
                 only_emoji=only_emoji_str)
        buttons = [
            [{"text": t('settings_menu.buttons.lang', lang, status=lang_str), "callback_data": "settings_select lang interface"}],
            [{"text": t('settings_menu.buttons.profile_view', lang, status=profile_view_str), "callback_data": "settings_select profile_view interface"}],
            [{"text": t('settings_menu.buttons.inv_sort', lang, status=inv_sort_str), "callback_data": "settings_select inv_sort interface"}],
            [{"text": t('settings_menu.buttons.inv_columns', lang, status=inv_columns_str), "callback_data": "settings_select inv_columns interface"}],
            [{"text": t('settings_menu.buttons.inv_rows', lang, status=inv_rows_str), "callback_data": "settings_select inv_rows interface"}],
            [{"text": t('settings_menu.buttons.rare_emoji', lang, status=rare_emoji_str), "callback_data": "settings_toggle rare_emoji interface"}],
            [{"text": t('settings_menu.buttons.only_emoji', lang, status=only_emoji_str), "callback_data": "settings_toggle only_emoji interface"}],
            [{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page main"}]
        ]
    elif page == 'account':
        text = t('settings_menu.title_account', lang, conf_mode=conf_str)
        buttons = [
            [{"text": t('settings_menu.buttons.nick', lang), "callback_data": "settings_act nick"}],
            [{"text": t('settings_menu.buttons.confidentiality', lang, status=conf_str), "callback_data": "settings_toggle confidentiality account"}],
            [{"text": t('settings_menu.buttons.reset_avatar', lang), "callback_data": "settings_act reset_avatar"}],
            [{"text": t('settings_menu.buttons.delete_me', lang), "callback_data": "settings_act delete_me"}],
            [{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page main"}]
        ]
    elif page == 'select_lang':
        text = t('settings_menu.buttons.select_lang_title', lang)
        locales = get_all_locales('language_name')
        btn_rows = []
        for l_code, l_name in locales.items():
            btn_rows.append([{"text": l_name, "callback_data": f"settings_set lang {l_code} interface"}])
        btn_rows.append([{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page interface"}])
        buttons = btn_rows
    elif page == 'select_profile':
        text = t('settings_menu.buttons.select_profile_title', lang)
        prf_ans = get_data('profile_view.ans', lang)
        btn_rows = []
        for i, ans in enumerate(prf_ans, 1):
            btn_rows.append([{"text": ans, "callback_data": f"settings_set profile_view {i} interface"}])
        btn_rows.append([{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page interface"}])
        buttons = btn_rows
    elif page == 'select_sort':
        text = t('settings_menu.buttons.select_sort_title', lang)
        keys_list = get_data('inv_sort.keys', lang)
        ans_list = get_data('inv_sort.ans', lang)
        btn_rows = []
        for k, a in zip(keys_list, ans_list):
            btn_rows.append([{"text": a, "callback_data": f"settings_set inv_sort {k} interface"}])
        btn_rows.append([{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page interface"}])
        buttons = btn_rows
    elif page == 'select_columns':
        text = t('settings_menu.buttons.select_columns_title', lang)
        col_row = []
        for col_num in [1, 2, 3, 4, 5]:
            col_row.append({"text": str(col_num), "callback_data": f"settings_set inv_columns {col_num} interface"})
        buttons = [
            col_row,
            [{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page interface"}]
        ]
    elif page == 'select_rows':
        text = t('settings_menu.buttons.select_rows_title', lang)
        rows_list = []
        for r_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            rows_list.append({"text": str(r_num), "callback_data": f"settings_set inv_rows {r_num} interface"})
        buttons = [
            rows_list[:5],
            rows_list[5:],
            [{"text": t('settings_menu.buttons.back_main', lang), "callback_data": "settings_page interface"}]
        ]
    else:
        return await build_settings_page(user, 'main', lang)

    return text, list_to_inline(buttons)


async def send_settings_page(message: Message, page: str = 'main'):
    userid = message.from_user.id
    lang = await get_lang(userid)
    user = await User.find_one(User.userid == userid)
    if not user:
        return

    text, inline_kb = await build_settings_page(user, page, lang)
    back_txt = t('back_text.settings_menu', lang)
    if not back_txt or back_txt.startswith('back_text.'):
        back_txt = t('settings_menu.title_main', lang)
    await bot.send_message(message.chat.id, back_txt, reply_markup=reply_kb)
    await bot.send_message(message.chat.id, text, reply_markup=inline_kb)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('settings_page'), IsAuthorizedUser())
async def settings_page_callback(callback: CallbackQuery):
    parts = callback.data.split()
    page = parts[1] if len(parts) > 1 else 'main'
    userid = callback.from_user.id
    lang = await get_lang(userid)
    user = await User.find_one(User.userid == userid)
    if not user:
        await callback.answer()
        return

    text, inline_kb = await build_settings_page(user, page, lang)
    try:
        await callback.message.edit_text(text, reply_markup=inline_kb)
    except Exception:
        pass
    await callback.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('settings_toggle'), IsAuthorizedUser())
async def settings_toggle_callback(callback: CallbackQuery):
    parts = callback.data.split()
    if len(parts) < 3:
        await callback.answer()
        return
    setting_key = parts[1]
    return_page = parts[2]

    userid = callback.from_user.id
    lang = await get_lang(userid)
    user = await User.find_one(User.userid == userid)
    if not user:
        await callback.answer()
        return

    settings = user.settings if user.settings else {}
    if setting_key == 'notifications':
        curr = settings.get('notifications', True)
        settings['notifications'] = not curr
    elif setting_key == 'no_talk':
        curr = settings.get('no_talk', False)
        settings['no_talk'] = not curr
    elif setting_key == 'rare_emoji':
        curr = settings.get('rare_emoji', True)
        settings['rare_emoji'] = not curr
        try:
            from bot.redismanager import get_redis
            redis = get_redis()
            await redis.set(f"user:rare_emoji:{userid}", "1" if settings['rare_emoji'] else "0")
        except Exception:
            pass
    elif setting_key == 'only_emoji':
        curr = settings.get('only_emoji', False)
        settings['only_emoji'] = not curr
    elif setting_key == 'confidentiality':
        curr = settings.get('confidentiality', False)
        price = GAME_SETTINGS['conf_set_price']
        is_premium = await user.premium
        if not curr:
            if is_premium or user.super_coins >= price:
                if not is_premium:
                    await user.update({'$inc': {'super_coins': -price}})
                settings['confidentiality'] = True
            else:
                await callback.answer(t('confidentiality.no_coins', lang, price=price), show_alert=True)
                return
        else:
            settings['confidentiality'] = False

    await user.update({"$set": {'settings': settings}})

    text, inline_kb = await build_settings_page(user, return_page, lang)
    try:
        await callback.message.edit_text(text, reply_markup=inline_kb)
    except Exception:
        pass
    await callback.answer(t('settings_menu.updated', lang))


@main_router.callback_query(IsPrivateChat(), F.data.startswith('settings_select'), IsAuthorizedUser())
async def settings_select_callback(callback: CallbackQuery):
    parts = callback.data.split()
    if len(parts) < 2:
        await callback.answer()
        return
    setting_key = parts[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)
    user = await User.find_one(User.userid == userid)
    if not user:
        await callback.answer()
        return

    page_map = {
        'lang': 'select_lang',
        'profile_view': 'select_profile',
        'inv_sort': 'select_sort',
        'inv_columns': 'select_columns',
        'inv_rows': 'select_rows'
    }
    target_page = page_map.get(setting_key, 'interface')
    text, inline_kb = await build_settings_page(user, target_page, lang)
    try:
        await callback.message.edit_text(text, reply_markup=inline_kb)
    except Exception:
        pass
    await callback.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('settings_set'), IsAuthorizedUser())
async def settings_set_callback(callback: CallbackQuery):
    parts = callback.data.split()
    if len(parts) < 4:
        await callback.answer()
        return
    setting_key = parts[1]
    val_raw = parts[2]
    return_page = parts[3]

    userid = callback.from_user.id
    lang = await get_lang(userid)
    user = await User.find_one(User.userid == userid)
    if not user:
        await callback.answer()
        return

    settings = user.settings if user.settings else {}

    if setting_key == 'lang':
        from bot.models.user import Lang
        await Lang.set_user_lang(userid, val_raw)
        lang = val_raw
        await bot.send_message(
            callback.message.chat.id,
            t('new_lang', lang),
            reply_markup=await m(userid, 'settings_menu', lang)
        )
    elif setting_key == 'profile_view':
        settings['profile_view'] = int(val_raw)
        await user.update({"$set": {'settings': settings}})
    elif setting_key == 'inv_sort':
        settings['inv_sort'] = val_raw
        await user.update({"$set": {'settings': settings}})
    elif setting_key == 'inv_columns':
        inv_view = settings.get('inv_view', [2, 3])
        inv_view[0] = int(val_raw)
        settings['inv_view'] = inv_view
        await user.update({"$set": {'settings': settings}})
    elif setting_key == 'inv_rows':
        inv_view = settings.get('inv_view', [2, 3])
        inv_view[1] = int(val_raw)
        settings['inv_view'] = inv_view
        await user.update({"$set": {'settings': settings}})
    elif setting_key == 'inv_columns':
        inv_view = settings.get('inv_view', [2, 3])
        inv_view[0] = int(val_raw)
        settings['inv_view'] = inv_view
        await user.update({"$set": {'settings': settings}})

    text, inline_kb = await build_settings_page(user, return_page, lang)
    try:
        await callback.message.edit_text(text, reply_markup=inline_kb)
    except Exception:
        pass
    await callback.answer(t('settings_menu.updated', lang))


@main_router.callback_query(IsPrivateChat(), F.data.startswith('settings_act'), IsAuthorizedUser())
async def settings_act_callback(callback: CallbackQuery):
    parts = callback.data.split()
    if len(parts) < 2:
        await callback.answer()
        return
    act = parts[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    main_msg_id = callback.message.message_id

    if act == 'my_name':
        await callback.answer()
        prompt_msg = await bot.send_message(chatid, t('my_name.info', lang), reply_markup=cancel_markup(lang))
        trans_data = {
            'main_msg_id': main_msg_id,
            'prompt_msg_id': prompt_msg.message_id,
            'return_page': 'notif_dino'
        }
        await ChooseStringHandler(my_name_end, userid, chatid, lang, max_len=20, transmitted_data=trans_data).start()

    elif act == 'dino_name':
        await callback.answer()
        trans_data = {
            'main_msg_id': main_msg_id,
            'return_page': 'notif_dino'
        }
        await ChooseDinoHandler(transition, userid, chatid, lang, False, transmitted_data=trans_data).start()

    elif act == 'nick':
        await callback.answer()
        prompt_msg = await bot.send_message(chatid, t('edit_nick', lang), reply_markup=cancel_markup(lang))
        trans_data = {
            'main_msg_id': main_msg_id,
            'prompt_msg_id': prompt_msg.message_id,
            'return_page': 'account'
        }
        await ChooseStringHandler(my_nick_set, userid, chatid, lang, max_len=20, min_len=3, transmitted_data=trans_data).start()

    elif act == 'reset_avatar':
        user = await User.find_one(User.userid == userid)
        if user:
            await user.update({"$set": {'avatar': ''}})
        await callback.answer(t('reset_avatar', lang), show_alert=True)
        text, inline_kb = await build_settings_page(user, 'account', lang)
        try:
            await callback.message.edit_text(text, reply_markup=inline_kb)
        except Exception:
            pass

    elif act == 'delete_me':
        await callback.answer()
        await start_delete_me_flow(userid, chatid, lang)


@main_router.message(IsPrivateChat(), Text('settings_menu.groups.notif_dino'), IsAuthorizedUser())
async def settings_group_notif_dino(message: Message):
    await send_settings_page(message, 'notif_dino')


@main_router.message(IsPrivateChat(), Text('settings_menu.groups.interface'), IsAuthorizedUser())
async def settings_group_interface(message: Message):
    await send_settings_page(message, 'interface')


@main_router.message(IsPrivateChat(), Text('settings_menu.groups.account'), IsAuthorizedUser())
async def settings_group_account(message: Message):
    await send_settings_page(message, 'account')

