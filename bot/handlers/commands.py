from email import message
from bot.modules.localization import get_data
from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.handlers.start import start_game
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds, user_name
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.inline import inline_menu
from bot.modules.localization import get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.managment.promo import use_promo
from aiogram.types import Message, CallbackQuery
from bot.config import conf

users = DBconstructor(mongo_client.user.users)
puhs = DBconstructor(mongo_client.market.puhs)

@bot.message(commands=['timer'])
@HDMessage
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

@bot.message(commands=['string_to_sec'], private=True)
@HDMessage
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

@bot.message(commands=['pushinfo'])
@HDMessage
async def push_info(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    text = t('push.push_info', lang)
    await bot.send_message(chatid, text, parse_mode='Markdown')

@bot.message(commands=['delete_push'])
@HDMessage
async def delete_push(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id

    await puhs.delete_one({'owner_id': userid}, comment='delete_push')
    await bot.send_message(chatid, '👍', parse_mode='Markdown')

@bot.message(commands=['add_me'], private=False)
@HDMessage
async def add_me_с(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    name = user_name(message.from_user, False)
    text = t("add_me", lang, userid=userid, username=name)
    await bot.reply_to(message, text, parse_mode='HTML',
                    reply_markup=inline_menu('send_request', lang, userid=userid)
                    )

@bot.message(commands=['promo'])
@HDMessage
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

@bot.message(commands=['help'])
@HDMessage
async def help(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    userid = message.from_user.id

    text, inl_m = await help_generate(userid, message.chat.type, 1, lang)
    await bot.send_message(chatid, text, parse_mode='HTML', 
                           reply_markup=inl_m)

@bot.callback_query(F.data.startswith('help'), private=True)
@HDCallback
async def kindergarten(call: CallbackQuery):
    split_d = call.data.split()
    page = int(split_d[1])
    chatid = call.message.chat.id
    userid = call.from_user.id

    text, inl_m = await help_generate(userid, call.message.chat.type, page)
    try:
        await bot.edit_message_text(text, chatid, call.message.id, parse_mode='HTML', reply_markup=inl_m)
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
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page

    text = t('help_command.all', lang) + '\n\n'

    page_items = help_keys[start_index:end_index]
    for c_item in page_items:
        com = commands[c_item]
        text += f'× /{c_item} {com["arguments"]}\n× {com["long"]}\n× ('
        if com['dev']:
            text += t('help_command.for_dev', lang) + ' '
        if com['dm']:
            text += t('help_command.for_dm', lang) + ' '
        if com['group']:
            text += t('help_command.for_group', lang) + ' '
        text += ')\n\n'

    if page - 1 == 0:
        left = help_keys.index(help_keys[-1]) // items_per_page
    else: left = page - 1

    if page + 1 > len(help_keys) / items_per_page + 1:
        right = 1
    else: right = page + 1

    inl_m = list_to_inline([
        {'◀': f'help {left}',
         '▶': f'help {right}'}
    ])

    text += f'{page} | {len(help_keys) // items_per_page + 1}'
    return text, inl_m