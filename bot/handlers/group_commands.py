

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.filters.reply_message import IsReply
from bot.filters.translated_text import StartWith, Text
from bot.modules.data_format import list_to_inline, random_code, user_name_from_telegram
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.get_state import get_state
from bot.modules.groups import add_message, delete_messages, get_group, get_group_by_chat, group_info, insert_group
from bot.modules.localization import get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
from aiogram.types import CallbackQuery, Message

from aiogram import F
from aiogram.filters import Command

from bot.filters.group_filter import GroupRules
from bot.filters.group_admin import IsGroupAdmin
from bot.filters.private import IsPrivateChat
from bot.modules.states_fabric.state_handlers import ChooseInlineHandler
from bot.modules.user.user import take_coins, user_name

users = DBconstructor(mongo_client.user.users)
groups = DBconstructor(mongo_client.group.groups)
messages = DBconstructor(mongo_client.group.messages)

async def successful_transfer_coins(st:str, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid'] # Тот кто отправляет
    lang = transmitted_data['lang']
    coins = transmitted_data['coins']
    self_name = transmitted_data['self_name']
    user_name = transmitted_data['user_name']
    message_data: Message = transmitted_data['temp']['message_data']
    reply_author = transmitted_data['reply_author'] # Тот кто получает

    state = await get_state(userid, chatid)
    await state.clear()

    self_user = await users.find_one({"userid": userid})
    to_user = await users.find_one({"userid": reply_author})
    
    if not all([self_user, to_user]):
        text = t('group_transfer.no_user', lang)
        await message_data.edit_text(text, parse_mode='Markdown')
        return

    if not await take_coins(userid, coins):
        text = t('group_transfer.no_coins', lang,
                 self_username=self_name
                 )
        await message_data.edit_text(text, parse_mode='Markdown')
        return

    if st == 'yes':
        text = t('group_transfer.answer_yes', lang,
                 self_username=self_name, user_name=user_name, coins=coins
                 )
        await message_data.edit_text(text, parse_mode='Markdown')

        await take_coins(userid, -coins, True)
        await take_coins(reply_author, coins, True)

    else:
        text = t('group_transfer.answer_no', lang)
        await message_data.edit_text(text, parse_mode='Markdown')

@main_router.message(Command(commands=['give_coins']),
                     GroupRules())
async def give_coins(message: Message, message_text: str = None):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(userid)
    
    await add_message(chatid, message.message_id)

    if not message_text:
        args = message.text.split(' ')[1:]
    else:
        args = message_text.split(' ')[1:]

    if not len(args):
        mes = await message.answer(t('group_transfer.no_num', lang))
        await add_message(chatid, mes.message_id)
        return

    coins = args[0]
    if not coins.isdigit():
        mes = await message.answer(t('group_transfer.no_num', lang))
        await add_message(chatid, mes.message_id)
        return
    coins = int(coins)

    if coins <= 0: return

    reply_message = message.reply_to_message
    if not reply_message:
        mes = await message.answer(t('group_transfer.no_reply', lang))
        await add_message(chatid, mes.message_id)
        return

    reply_author = reply_message.from_user
    if reply_author and message.from_user:

        if reply_author.id == message.from_user.id:
            return

        custom_code = random_code()
        self_name = user_name_from_telegram(message.from_user, True)
        user_name = user_name_from_telegram(reply_author, True)

        text = t('group_transfer.question', lang, 
                 self_username=self_name, user_name=user_name, coins=coins)
        markup = list_to_inline(
            [
                {
                t('buttons_name.yes', lang): f"chooseinline {custom_code} yes",
                t('buttons_name.no', lang): f"chooseinline {custom_code} no"
                }
            ]
        )

        await ChooseInlineHandler(
            successful_transfer_coins,
            userid, chatid,
            lang, custom_code,
            {
                "coins": coins,
                "reply_author": reply_author.id,
                "self_name": self_name,
                "user_name": user_name
            }
        ).start()

        mes = await message.answer(text, parse_mode='Markdown', reply_markup=markup)
        await add_message(chatid, mes.message_id)

@main_router.message(
    StartWith('help_command.commands.give_coins.alternative'), GroupRules())
async def give_coins_alt(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    txt = t('help_command.commands.give_coins.alternative', lang)
    text = str(message.text)
    text = text.replace(txt, 'give_coins')

    await give_coins(message, text)