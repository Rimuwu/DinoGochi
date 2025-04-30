
from pprint import pprint
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.filters.group_filter import GroupRules
from bot.modules.decorators import  HDMessage
from bot.modules.groups import add_message
from bot.modules.localization import  get_lang
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import user_info
from aiogram.types import Message

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command

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

        if avatar:
            await bot.send_photo(chatid, avatar, caption=text, parse_mode='Markdown')
        else:
            await bot.send_message(message.chat.id, text, parse_mode='Markdown')

@HDMessage
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
        user_exists = await users.find_one({'userid': user_id}, comment='check_user_exists')
        if not user_exists: return
        text, avatar = await user_info(user_id, lang)

        if avatar:
            mes = await message.answer_photo(avatar, caption=text, parse_mode='Markdown')
        else:
            mes = await message.answer(text, parse_mode='Markdown')

        await add_message(message.chat.id, message.message_id)
        await add_message(message.chat.id, mes.message_id)

@main_router.message(Text('help_command.commands.profile.alternative'), GroupRules())
async def infouser_alt(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    text, avatar = await user_info(userid, lang)

    if avatar:
        mes = await message.answer_photo(avatar, caption=text, parse_mode='Markdown')
    else:
        mes = await message.answer(text, parse_mode='Markdown')
    
    await add_message(message.chat.id, message.message_id)
    await add_message(message.chat.id, mes.message_id)