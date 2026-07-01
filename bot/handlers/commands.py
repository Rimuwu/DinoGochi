from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import User
from bot.models.market import Puhs
from bot.filters.group_filter import GroupRules
from bot.modules.groups import add_message
from bot.modules.localization import get_data
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.handlers.start import start_game
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.inline import inline_menu
from bot.modules.localization import get_lang, t
from bot.modules.managment.promo import use_promo
from aiogram.types import Message, CallbackQuery
from bot.config import conf

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command
from aiogram.types import BotCommand, BotCommandScopeChat
from bot.modules.states_fabric.state_handlers import ChooseInventoryHandler
from bot.handlers.transition import (
    settings_menu as handler_settings,
    profile_menu as handler_profile_menu,
    friends_menu as handler_friends_menu,
    market_menu as handler_market_menu,
    actions_menu as handler_actions_menu,
    tavern_menu as handler_tavern_menu,
)
from fuzzywuzzy import fuzz

from bot.modules.user.user import User

users = LazyCollection(User)
puhs = LazyCollection(Puhs)

@HDMessage
@main_router.message(Command(commands=['timer']))
async def timer(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    num, mini, max_lvl = '1', False, 'seconds'
    msg_args = str(message.text).split()

    if len(msg_args) > 1: num: str = msg_args[1]
    if len(msg_args) > 2: max_lvl: str = msg_args[2]
    if len(msg_args) > 3: mini: bool = bool(msg_args[3])

    if num.isdigit():
        try:
            text = seconds_to_str(int(num), lang, mini, max_lvl)
        except: text = 'error'
        await bot.send_message(chatid, text)

@HDMessage
@main_router.message(Command(commands=['string_to_sec']), IsPrivateChat())
async def string_time(message):
    txt = message.text.replace('/string_to_sec', '')
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    if txt == '':
        text = t('string_to_str.info', lang)
        await bot.send_message(chatid, text, parse_mode='Markdown')
    else:
        sec = str_to_seconds(txt)
        await bot.send_message(chatid, str(sec))

@HDMessage
@main_router.message(Command(commands=['pushinfo']))
async def push_info(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    text = t('push.push_info', lang)
    await bot.send_message(chatid, text, parse_mode='Markdown')

@HDMessage
@main_router.message(Command(commands=['delete_push']))
async def delete_push(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id

    await puhs.delete_one({'owner_id': userid}, comment='delete_push')
    await bot.send_message(chatid, '👍', parse_mode='Markdown')

@HDMessage
@main_router.message(Command(commands=['add_me']), GroupRules())
async def add_me_с(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    user = await User().create(userid)
    text = t("add_me", lang, userid=userid, username=user.name)
    mes = await message.answer(text, parse_mode='HTML',
                    reply_markup=inline_menu('send_request', lang, userid=userid)
                    )
    await add_message(message.chat.id, message.message_id)
    await add_message(message.chat.id, mes.message_id)

@HDMessage
@main_router.message(Command(commands=['promo']), IsPrivateChat(True))
async def promo(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    msg_args = str(message.text).split()

    if len(msg_args) > 1:
        code = msg_args[1]
        user = await users.find_one({'userid': userid}, comment='promo_user')
        if user:
            status, text = await use_promo(code, userid, lang)
            await bot.send_message(chatid, text, parse_mode='Markdown')
        else:
            await start_game(message, code, 'promo')

def build_bot_commands(userid: int, chat_type: str, lang: str) -> list[BotCommand]:
    is_dm = chat_type == "private"
    is_group = chat_type != "private"
    is_dev = userid in conf.bot_devs

    commands = get_data('help_command.commands', lang)
    bot_commands = []

    for key, value in commands.items():
        if value['dm'] == is_dm or value['group'] == is_group:
            if value['dev'] and not is_dev:
                continue
            desc = value.get('short', key)
            if len(desc) > 256:
                desc = desc[:253] + "..."
            cmd_name = key.lower()
            bot_commands.append(BotCommand(command=cmd_name, description=desc))
    return bot_commands

@HDMessage
@main_router.message(Command(commands=['help']), GroupRules(True))
async def help(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    userid = message.from_user.id

    try:
        cmds = build_bot_commands(userid, message.chat.type, lang)
        await message.bot.set_my_commands(
            cmds,
            scope=BotCommandScopeChat(chat_id=message.chat.id)
        )
    except Exception as e:
        log(f"Error setting my commands: {e}", 3)

    text, inl_m = await help_generate(userid, message.chat.type, 1, lang)
    mes = await message.answer(text, parse_mode='HTML', 
                           reply_markup=inl_m)
    await add_message(chatid, message.message_id)
    await add_message(chatid, mes.message_id)

@HDCallback
@main_router.callback_query(F.data.startswith('help'))
async def help_query(call: CallbackQuery):
    split_d = call.data.split()
    page = int(split_d[1])
    chatid = call.message.chat.id
    userid = call.from_user.id

    text, inl_m = await help_generate(userid, call.message.chat.type, page)
    try:
        await bot.edit_message_text(text, None, chatid, call.message.message_id, parse_mode='HTML', reply_markup=inl_m)
    except:
        await bot.send_message(chatid, text, parse_mode='HTML', 
                           reply_markup=inl_m)

async def help_generate(userid: int, chat_type: str, page: int, lang = None):
    """ Одна страница - 5 команд
        page - [0:10]
    """
    if not lang: lang = await get_lang(userid)

    is_dm = chat_type == "private"
    is_group = chat_type != "private"
    is_dev = userid in conf.bot_devs

    commands = get_data('help_command.commands', lang)
    help_keys = []

    for key, value in commands.items():

        if value['dm'] == is_dm or \
             value['group'] == is_group:
                if value['dev']:
                    if is_dev:
                        help_keys.append(key)
                else:
                    help_keys.append(key)

    items_per_page = 5
    total_pages = (len(help_keys) - 1) // items_per_page + 1
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page

    text = t('help_command.all', lang) + '\n\n'

    page_items = help_keys[start_index:end_index]
    for c_item in page_items:
        com = commands[c_item]
        alternativ = com.get('alternative', None)
        if alternativ:
            text += f'/{c_item} {com["arguments"]} | <code>{alternativ}</code>'
        else:
            text += f'/{c_item} {com["arguments"]}'
        
        text += f'\n× {com["long"]}\n× ('
        if com['dev']:
            text += t('help_command.for_dev', lang) + ' '
        if com['dm']:
            text += t('help_command.for_dm', lang) + ' '
        if com['group']:
            text += t('help_command.for_group', lang) + ' '
        text = text[:-1] + ')\n\n'

    # Навигация по страницам
    if page - 1 == 0:
        left = total_pages
    else:
        left = page - 1

    if page + 1 > total_pages:
        right = 1
    else:
        right = page + 1

    if total_pages != 1:
        inl_m = list_to_inline([
            {'◀': f'help {left}',
            '▶': f'help {right}'}
        ])
    else:
        inl_m = None

    text += f'{page} | {total_pages}'
    return text, inl_m

@HDMessage
@main_router.message(Command(commands=['inventory', 'inv']), IsPrivateChat(), IsAuthorizedUser())
async def command_inventory(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    await ChooseInventoryHandler(None, userid, chatid, lang).start()

@HDMessage
@main_router.message(Command(commands=['settings']), IsPrivateChat(), IsAuthorizedUser())
async def command_settings(message: Message):
    await handler_settings(message)

@HDMessage
@main_router.message(Command(commands=['profile_menu']), IsPrivateChat(), IsAuthorizedUser())
async def command_profile_menu(message: Message):
    await handler_profile_menu(message)

@HDMessage
@main_router.message(Command(commands=['friends']), IsPrivateChat(), IsAuthorizedUser())
async def command_friends(message: Message):
    await handler_friends_menu(message)

@HDMessage
@main_router.message(Command(commands=['market']), IsPrivateChat(), IsAuthorizedUser())
async def command_market(message: Message):
    await handler_market_menu(message)

@HDMessage
@main_router.message(Command(commands=['tavern']), IsPrivateChat(), IsAuthorizedUser())
async def command_tavern(message: Message):
    await handler_tavern_menu(message)

@HDMessage
@main_router.message(Command(commands=['actions']), IsPrivateChat(), IsAuthorizedUser())
async def command_actions(message: Message):
    await handler_actions_menu(message)

@HDMessage
@main_router.message(Command(commands=['dino', 'd']), IsPrivateChat(), IsAuthorizedUser())
async def command_dino(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        from bot.handlers.main_menu.dino_profile import dino_handler
        await dino_handler(message)
        return

    target_name = args[1].strip()

    from bot.models.user import User as UserModel
    from bot.handlers.main_menu.dino_profile import dino_profile

    user = await UserModel().create(userid)
    dinos = await user.get_dinos()

    if not dinos:
        await message.answer(t('p_profile.no_dinos_yet', lang))
        return

    best_dino = None
    best_ratio = 0
    matches = []

    for dino in dinos:
        ratio = fuzz.WRatio(target_name.lower(), dino.name.lower())
        matches.append((dino, ratio))
        if ratio > best_ratio:
            best_ratio = ratio
            best_dino = dino

    if best_dino and best_ratio >= 55:
        await dino_profile(userid, chatid, best_dino, lang, None)
    else:
        matches.sort(key=lambda x: x[1], reverse=True)
        top_matches = [f"• {m[0].name}" for m in matches[:3]]
        matches_str = "\n".join(top_matches)
        await message.answer(t('p_profile.dino_not_found', lang, name=target_name, matches=matches_str))