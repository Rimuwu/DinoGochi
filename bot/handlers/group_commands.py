

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.filters.reply_message import IsReply
from bot.filters.translated_text import StartWith, Text
from bot.modules.data_format import list_to_inline, random_code, user_name_from_telegram
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.get_state import get_state
from bot.modules.groups import add_message, delete_messages, get_group, get_group_by_chat, group_info, insert_group
from bot.modules.localization import get_lang, t, get_data
from bot.modules.overwriting.DataCalsses import DBconstructor
from aiogram.types import CallbackQuery, Message
from bot.modules.inline import list_to_inline

from aiogram import F
from aiogram.filters import Command

from bot.const import GAME_SETTINGS

from bot.filters.group_filter import GroupRules
from bot.filters.group_admin import IsGroupAdmin
from bot.filters.private import IsPrivateChat
from bot.modules.states_fabric.state_handlers import ChooseInlineHandler
from bot.modules.user.user import take_coins, user_name
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router

users = DBconstructor(mongo_client.user.users)
groups = DBconstructor(mongo_client.group.groups)
messages = DBconstructor(mongo_client.group.messages)
group_users = DBconstructor(mongo_client.group.users)

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

users_page_page = 10

async def generate_group_rating_message(top_users, ret_type, lang, 
                                        group_name, page=1):
    if not top_users:
        return t('group_rating.no_users', lang)

    field_names = {
        'coins': t('group_rating.field.coins', lang),
        'super_coins': t('group_rating.field.super_coins', lang),
        'lvl': t('group_rating.field.lvl', lang)
    }

    # Pagination
    page = max(1, int(page) if page else 1)
    total_users = len(top_users)
    max_pages = (total_users + users_page_page - 1) // users_page_page
    start_idx = (page - 1) * users_page_page
    end_idx = start_idx + users_page_page
    page_users = top_users[start_idx:end_idx]

    lines = [t('group_rating.title', lang, 
                field=field_names[ret_type],
                group_name=group_name,
                )]
    for idx, user in enumerate(page_users, start=start_idx + 1):
        uname = await user_name(user['userid'])
        value = user.get(ret_type, 0)
        
        if idx == 1:
            idx_str = f'🥇 '
        elif idx == 2:
            idx_str = f'🥈 '
        elif idx == 3:
            idx_str = f'🥉 '
        else:
            idx_str = f'  *{idx}*. '

        if ret_type == 'lvl':
            value = f"{user.get('lvl', 0)} ({user.get('xp', 0)}) ⚡"
        elif ret_type == 'coins':
            value = f"{user.get('coins', 0)} 🪙"
        elif ret_type == 'super_coins':
            value = f"{user.get('super_coins', 0)} ⭐"

        lines.append(f"{idx_str} `{uname}` — {value}")

    # Add page info
    lines.append('\n' + f'{page}/{max_pages}')

    return '\n'.join(lines)

async def get_data_for_rayting(chatid, ret_type, lang, message):
    group = await get_group_by_chat(chatid)
    if not group:
        return None, None
    
    # Получаем пользователей группы 
    group_users_list = await group_users.find(
        {"group_id": group['group_id']})

    if not group_users_list:
        mes = await message.answer(t('group_rating.no_users', lang))
        await add_message(chatid, mes.message_id)
        return None, None

    # Получаем userids
    user_ids = [u['user_id'] for u in group_users_list]

    # Получаем пользователей из базы
    users_list = await users.find({
        "userid": {"$in": user_ids},
        "$or": [
            {"setting.confidentiality": False},
            {"setting.confidentiality": None}
        ]
    }, comment="get_group_rating")

    # Сортируем по нужному полю
    if ret_type == 'lvl':
        users_list = sorted(
            users_list,
            key=lambda u: (u.get('lvl', 0), u.get('xp', 0)),
            reverse=True
        )
    else:
        users_list = sorted(users_list, key=lambda u: u.get(ret_type, 0), reverse=True)

    # Берём только первую страницу (например, топ 10)
    group_name = await bot.get_chat(chatid)
    group_name = group_name.title

    return users_list, group_name

@main_router.message(Command(commands=['rating']),
                        GroupRules())
async def group_rating(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(userid)

    await add_message(chatid, message.message_id)

    data = message.text.split(' ')
    if len(data) == 1:
        ret_type = 'lvl'
    else:
        ret_type = data[1]

    commands_args: dict = get_data('group_rating.commands_args', lang)
    # Проверяем, если ret_type не в списке допустимых, ищем совпадение по ключам
    if ret_type not in commands_args:
        for key in commands_args:
            if ret_type in commands_args[key]:
                ret_type = key
                break
        else:
            ret_type = 'lvl'

    group = await get_group_by_chat(chatid)
    if not group:
        return

    top_users, group_name = await get_data_for_rayting(
        chatid, ret_type, lang, message)

    if not top_users:
        return

    max_pages = (len(top_users) + users_page_page - 1) // users_page_page
    markup = get_rating_markup(ret_type, 1, max_pages)
    text = await generate_group_rating_message(top_users,
                                ret_type, lang, group_name)
    mes = await message.answer(text, parse_mode='Markdown', reply_markup=markup)
    await add_message(chatid, mes.message_id)

def get_rating_markup(ret_type, page, max_pages):
    buttons = {}
    if page > 1:
        buttons[GAME_SETTINGS['back_button']] = f"group_rating {ret_type} {page-1}"
    if page < max_pages:
        buttons[GAME_SETTINGS['forward_button']] = f"group_rating {ret_type} {page+1}"
    if buttons:
        return list_to_inline([buttons])
    return None

@main_router.callback_query(F.data.startswith("group_rating"))
async def group_rating_page_handler(callback: CallbackQuery):
    data = callback.data.split(" ")
    if len(data) != 3:
        await callback.answer("Invalid data", show_alert=True)
        return

    _, ret_type, page = data
    page = int(page)

    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(userid)

    top_users, group_name = await get_data_for_rayting(chatid, 
                                ret_type, lang, callback.message)
    if not top_users: return

    text = await generate_group_rating_message(top_users, 
                                ret_type, lang, group_name, page)
    max_pages = (len(top_users) + users_page_page - 1) // users_page_page
    markup = get_rating_markup(ret_type, page, max_pages)
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=markup)

@main_router.message(
    StartWith('help_command.commands.rating.alternative'), GroupRules())
async def group_rating_alt(message: Message):
    await group_rating(message)