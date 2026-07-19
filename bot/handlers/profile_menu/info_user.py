from bot.models.user import User
from bot.exec import main_router, bot
from bot.filters.group_filter import GroupRules
from bot.modules.groups import add_message
from bot.modules.localization import get_lang, t
from bot.modules.user.user import user_dinos_info, user_info, user_profile_markup, user_inventory_info, user_achievements_info, user_levels_info
from aiogram.types import Message, CallbackQuery

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F
from aiogram.exceptions import TelegramBadRequest


async def send_user_profile(chatid: int, user_id: int, lang: str, secret: bool = False, reply_to_message: Message = None):
    from bot.modules.user.achievements import check_all_achievements
    await check_all_achievements(user_id)
    text, avatar = await user_info(user_id, lang, secret)
    markup = None
    if not secret:
        markup = await user_profile_markup(user_id, lang, 'main', 0)

    if avatar:
        try:
            if reply_to_message:
                mes = await reply_to_message.answer_photo(avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
            else:
                mes = await bot.send_photo(chatid, avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
            return mes
        except Exception:
            # If sending failed (e.g. file_id was invalid/expired), reset avatar in database
            user_exists = await User.find_one(User.userid == user_id)
            if user_exists:
                await user_exists.set_avatar('')
            # Fetch fresh avatar
            from bot.modules.user.avatar import get_avatar
            avatar = await get_avatar(user_id)
            
            if avatar:
                try:
                    if reply_to_message:
                        mes = await reply_to_message.answer_photo(avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
                    else:
                        mes = await bot.send_photo(chatid, avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
                    return mes
                except Exception:
                    pass

    # Fallback to text message
    if reply_to_message:
        mes = await reply_to_message.answer(text, parse_mode='Markdown', reply_markup=markup)
    else:
        mes = await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)
    return mes

@main_router.message(IsPrivateChat(), 
        Text('commands_name.profile.information'), 
                     IsAuthorizedUser())
async def infouser(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    if message.from_user:
        from bot.modules.markup import markups_menu as m
        await bot.send_message(chatid, t('menu_text.info_menu', lang), reply_markup=await m(userid, 'info_menu', lang))
        from bot.modules.tutorial import advance_tutorial_if_step
        await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="profile_info")

@main_router.message(IsPrivateChat(), 
        Text('commands_name.info_menu.my_profile'), 
                     IsAuthorizedUser())
async def infouser_my_profile(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)
    if message.from_user:
        await send_user_profile(chatid, userid, lang)

@main_router.message(IsPrivateChat(), 
        Text('commands_name.info_menu.achievements'), 
                     IsAuthorizedUser())
async def infouser_achievements(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)
    if message.from_user:
        from bot.modules.user.achievements import check_all_achievements
        await check_all_achievements(userid)
        text, image = await user_achievements_info(userid, lang, 0, is_own_profile=True)
        markup = await user_profile_markup(userid, lang, 'achievements', 0)
        if image:
            await bot.send_photo(chatid, image, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

@main_router.message(IsPrivateChat(), 
        Text('commands_name.info_menu.levels'), 
                     IsAuthorizedUser())
async def infouser_levels(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)
    if message.from_user:
        text, image = await user_levels_info(userid, lang, 0)
        markup = await user_profile_markup(userid, lang, 'levels', 0)
        if image:
            await bot.send_photo(chatid, image, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

@main_router.message(Command(commands=['profile']), 
                     GroupRules(True))
async def infouser_com(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    args = message.text.split(' ')[1:]

    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
    else:
        user_id = userid

    if args:
        if args[0] == 'me': user_id = userid

    if message.from_user:
        secret = False
        user_exists = await User.find_one(User.userid == user_id)
        if not user_exists: return

        confidentiality = user_exists.settings.get('confidentiality', False) if user_exists.settings else False
        if confidentiality and message.chat.type != 'private':
            secret = True

        mes = await send_user_profile(message.chat.id, user_id, lang, secret, reply_to_message=message)

        await add_message(message.chat.id, message.message_id)
        await add_message(message.chat.id, mes.message_id)

@main_router.message(Text('help_command.commands.profile.alternative'), 
                     GroupRules())
async def infouser_alt(message: Message):
    userid = message.from_user.id

    secret = False
    user_exists = await User.find_one(User.userid == userid)
    if not user_exists: return

    lang = await get_lang(userid)
    confidentiality = user_exists.settings.confidentiality if user_exists.settings else False
    if confidentiality and message.chat.type != 'private':
        secret = True

    mes = await send_user_profile(message.chat.id, userid, lang, secret, reply_to_message=message)

    await add_message(message.chat.id, message.message_id)
    await add_message(message.chat.id, mes.message_id)

@main_router.callback_query(F.data.startswith('user_profile'))
async def user_profile_menu(callback: CallbackQuery):
    await callback.answer()
    try:
        data = callback.data.split()
        lang = await get_lang(callback.from_user.id)

        page_type = data[1]
        who_userid = int(data[2])
        page = int(data[3])
        filter_idx = int(data[4]) if len(data) > 4 else 0
        is_own_profile = callback.from_user.id == who_userid
        text = 'type_error'

        if page_type == 'main':
            text, avatar = await user_info(who_userid, lang)

        if page_type == 'dino':
            text, image = await user_dinos_info(who_userid, lang, page)

        if page_type == 'inventory':
            text, image = await user_inventory_info(who_userid, lang, page)
            from bot.modules.tutorial import advance_tutorial_if_step
            await advance_tutorial_if_step(who_userid, callback.message.chat.id, lang, bot, expected_step="profile_top")

        if page_type == 'achievements':
            if is_own_profile:
                from bot.modules.user.achievements import check_all_achievements
                await check_all_achievements(who_userid)
            text, image = await user_achievements_info(who_userid, lang, page, is_own_profile=is_own_profile)
            from bot.modules.tutorial import advance_tutorial_if_step
            await advance_tutorial_if_step(who_userid, callback.message.chat.id, lang, bot, expected_step="profile_info_user")

        if page_type == 'levels':
            text, image = await user_levels_info(who_userid, lang, page)

        markup = await user_profile_markup(who_userid, lang, page_type, page, filter_idx)

        # Check if the text actually changed
        text_changed = True
        current_text = None
        if isinstance(callback.message, Message):
            if callback.message.photo is not None:
                current_text = callback.message.caption
            else:
                current_text = callback.message.text

        if current_text and current_text.strip() == text.strip():
            text_changed = False

        try:
            if not text_changed:
                await callback.message.edit_reply_markup(reply_markup=markup)
            else:
                if isinstance(callback.message, Message) and callback.message.photo is not None:
                    await callback.message.edit_caption(caption=text,
                                    parse_mode='Markdown', reply_markup=markup)
                elif hasattr(callback.message, 'edit_text'):
                    await callback.message.edit_text(text=text,
                                    parse_mode='Markdown', reply_markup=markup)
        except TelegramBadRequest as e:
            from bot.modules.logs import log
            log(f"user_profile_menu TelegramBadRequest [{callback.data}]: {e}", 3)
    except Exception as e:
        from bot.modules.logs import log
        import traceback
        log(f"user_profile_menu error [{callback.data}]: {e}\n{traceback.format_exc()}", 4)
