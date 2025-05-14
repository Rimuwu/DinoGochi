
from email import message
from pprint import pprint
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.filters.group_filter import GroupRules
from bot.modules.decorators import  HDCallback, HDMessage
from bot.modules.groups import add_message
from bot.modules.localization import  get_lang
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import user_dinos_info, user_info, user_profile_markup
from aiogram.types import Message, CallbackQuery

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F

users = DBconstructor(mongo_client.user.users)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.profile.information'), 
                     IsAuthorizedUser())
async def infouser(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    

    if message.from_user:
        text, avatar = await user_info(userid, lang)
        markup = await user_profile_markup(userid, lang, 'main', 0)

        if avatar:
            await bot.send_photo(chatid, avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            await bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@HDMessage
@main_router.message(Command(commands=['profile']), 
                     GroupRules(True))
async def infouser_com(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    args = message.text.split(' ')[1:]
    markup = None

    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
    else:
        user_id = userid
    
    if args:
        if args[0] == 'me': user_id = userid

    if message.from_user:
        secret = False
        user_exists = await users.find_one({'userid': user_id}, comment='check_user_exists')
        if not user_exists: return

        confidentiality = user_exists['settings'].get('confidentiality', False)
        if confidentiality and message.chat.type != 'private':
            secret = True

        text, avatar = await user_info(user_id, lang, secret)
        if not secret:
            markup = await user_profile_markup(userid, lang, 'main', 0)

        if avatar:
            mes = await message.answer_photo(avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            mes = await message.answer(text, 
                        parse_mode='Markdown', reply_markup=markup)

        await add_message(message.chat.id, message.message_id)
        await add_message(message.chat.id, mes.message_id)

@main_router.message(Text('help_command.commands.profile.alternative'), 
                     GroupRules())
async def infouser_alt(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    secret = False
    user_exists = await users.find_one({'userid': user_id}, comment='check_user_exists')
    if not user_exists: return

    confidentiality = user_exists['settings'].get('confidentiality', False)
    if confidentiality and message.chat.type != 'private':
        secret = True

    text, avatar = await user_info(userid, lang, secret)

    if avatar:
        mes = await message.answer_photo(avatar, caption=text, parse_mode='Markdown')
    else:
        mes = await message.answer(text, parse_mode='Markdown')
    
    await add_message(message.chat.id, message.message_id)
    await add_message(message.chat.id, mes.message_id)

@HDCallback
@main_router.callback_query(F.data.startswith('user_profile'))
async def user_profile_menu(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
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

    markup = await user_profile_markup(who_userid, lang, page_type, page)

    if callback.message.photo is None:
        await callback.message.edit_text(text=text, 
                        parse_mode='Markdown', reply_markup=markup)
    else:
        await callback.message.edit_caption(caption=text,
                        parse_mode='Markdown', reply_markup=markup)
