from bot.models.user import User
from bot.exec import main_router, bot
from bot.filters.group_filter import GroupRules
from bot.modules.groups import add_message
from bot.modules.localization import  get_lang
from bot.modules.user.user import user_dinos_info, user_info, user_profile_markup, user_inventory_info
from aiogram.types import Message, CallbackQuery

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F
from aiogram.exceptions import TelegramBadRequest


async def send_user_profile(chatid: int, user_id: int, lang: str, secret: bool = False, reply_to_message: Message = None):
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
        await send_user_profile(chatid, userid, lang)

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
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)

    page_type = data[1]
    who_userid = int(data[2])
    page = int(data[3])
    text = 'type_error'

    if page_type == 'main':
        text, avatar = await user_info(who_userid, lang)

    if page_type == 'dino':
        text, image = await user_dinos_info(who_userid, lang, page)

    if page_type == 'inventory':
        text, image = await user_inventory_info(who_userid, lang, page)

    markup = await user_profile_markup(who_userid, lang, page_type, page)

    try:
        if isinstance(callback.message, Message) and callback.message.photo is not None:
            await callback.message.edit_caption(caption=text,
                            parse_mode='Markdown', reply_markup=markup)
        elif hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(text=text,
                            parse_mode='Markdown', reply_markup=markup)
    except TelegramBadRequest:
        pass
