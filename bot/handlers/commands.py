from telebot.types import Message

from bot.exec import bot
from bot.config import mongo_client
from bot.modules.data_format import seconds_to_str, user_name, str_to_seconds
from bot.modules.inline import inline_menu
from bot.modules.localization import  get_lang, t
from bot.modules.promo import use_promo
from bot.handlers.start import start_game
 


users = mongo_client.user.users

@bot.message_handler(pass_bot=True, commands=['timer'])
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

@bot.message_handler(pass_bot=True, commands=['string_to_sec'], private=True)
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

@bot.message_handler(pass_bot=True, commands=['pushinfo'])
async def push_info(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    text = t('push.push_info', lang)
    await bot.send_message(chatid, text, parse_mode='Markdown')

@bot.message_handler(pass_bot=True, commands=['add_me'], private=False)
async def add_me_с(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    name = user_name(message.from_user, False)
    text = t("add_me", lang, userid=userid, username=name)
    await bot.reply_to(message, text, parse_mode='HTML',
                    reply_markup=inline_menu('send_request', lang, userid=userid)
                    )

@bot.message_handler(pass_bot=True, commands=['promo'])
async def promo(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    msg_args = str(message.text).split()

    if len(msg_args) > 1:
        code = msg_args[1]
        user = await users.find_one({'userid': userid})
        if user:
            status, text = await use_promo(code, userid, lang)
            await bot.send_message(chatid, text, parse_mode='Markdown')
        else:
            await start_game(message, code, 'promo')

@bot.message_handler(pass_bot=True, commands=['help'])
async def help(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    await bot.send_message(chatid, t('help_command.all', lang), parse_mode='html')