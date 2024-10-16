from aiogram.types import CallbackQuery, Message

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import main_router, bot
from bot.modules.data_format import escape_markdown, list_to_inline
from bot.modules.items.item import counts_items
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.managment.referals import connect_referal, create_referal
from bot.modules.states_tools import ChooseCustomState, ChooseStringState
from bot.modules.user.user import take_coins
from bot.modules.decorators import HDCallback, HDMessage


from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command


from bot.modules.overwriting.DataCalsses import DBconstructor
referals = DBconstructor(mongo_client.user.referals)

@HDMessage
@main_router.message(Text('commands_name.referal.code'), IsAuthorizedUser(), IsPrivateChat())
async def code(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    if not await referals.find_one({'ownerid': userid}, comment='code'):
        price = GS['referal']['custom_price']

        text = t('referals.generate', lang, price=price)
        buttons = get_data('referals.var_buttons', lang)
    
        inl_buttons = dict(zip(buttons.values(), buttons.keys()))
        markup = list_to_inline([inl_buttons])
        
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)
    else:
        await bot.send_message(message.chat.id, t('referals.have_code', lang))


async def create_custom_code(code: str, transmitted_data: dict):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    if await take_coins(userid, GS['referal']['custom_price'], True):
        code = code.replace(' ', '')
        await create_referal(userid, code)

        iambot = await bot.get_me()
        bot_name = iambot.username

        url = f'https://t.me/{bot_name}/?start={code}'
        text = t('referals.code', lang, code=code, url=url)
    else:
        text = t('referals.custom_code.no_coins', lang)

    await bot.send_message(chatid, text, parse_mode='Markdown', 
                        reply_markup = await m(userid, 'last_menu', lang, True))

async def custom_handler(message: Message, transmitted_data: dict):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    
    code = escape_markdown(str(message.text))
    status = False
    text = ''
    
    if len(code) > 10:
        text = t('referals.custom_code.max_len', lang)
    if len(code) == 0:
        text = t('referals.custom_code.min_len', lang)
    else:
        res = await referals.find_one({'code': code}, comment='custom_handler_refer_res')
        if res:
            text = t('referals.custom_code.found_code', lang)
        else: status = True

    if not status:
        await bot.send_message(chatid, text, parse_mode='Markdown')
    return status, code

@HDCallback
@main_router.callback_query(F.data.startswith('generate_referal'), IsPrivateChat())
async def generate_code(call: CallbackQuery, state):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    action = call.data.split()[1]

    if not await referals.find_one({'ownerid': userid}, comment='generate_code_1'):
        if action == 'random':
            ref = await create_referal(userid)
            code = ref[1]

            iambot = await bot.get_me()
            bot_name = iambot.username

            url = f'https://t.me/{bot_name}/?start={code}'
            await bot.send_message(chatid, t('referals.code', lang, 
                                    code=code, url=url), parse_mode='Markdown', reply_markup= await m(userid, 'last_menu', lang, True))

        elif action == 'custom':
            await bot.send_message(chatid, 
                                   t('referals.custom_code.start', lang), parse_mode='Markdown', reply_markup=cancel_markup(lang))
            await ChooseCustomState(create_custom_code, custom_handler, 
                                    userid, chatid, lang)
    else:
        await bot.send_message(chatid, t('referals.have_code', lang))


@HDMessage
@main_router.message(StartWith('commands_name.referal.my_code'), IsPrivateChat())
async def my_code(message: Message):
    """ Кнопка - мой код ...
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    referal = await referals.find_one({'userid': userid, 'type': 'general'}, comment='my_code_referal')
    if referal:
        code = referal['code']
        referal_find = await referals.find(
            {'code': code, 'type': 'sub'}, comment='my_code_referal_find')

        uses = len(list(referal_find))

        iambot = await bot.get_me()
        bot_name = iambot.username
        url = f'https://t.me/{bot_name}/?start={code}'

        await bot.send_message(chatid, t('referals.my_code', lang, 
                                code=code, url=url, uses=uses), parse_mode='Markdown')

async def check_code(code: str, transmitted_data: dict, send: bool = True):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    coins = GS['referal']['coins']
    items = GS['referal']['items']
    names = counts_items(items, lang)

    result = await connect_referal(code, userid)

    if send or result:
        text = t(f'referals.enter_code.{result}', lang, coins=coins, items=names)
        await bot.send_message(chatid, text, parse_mode='Markdown', 
                        reply_markup= await m(userid, 'last_menu', lang, True))

@HDMessage
@main_router.message(Text('commands_name.referal.enter_code'), IsAuthorizedUser(), IsPrivateChat())
async def enter_code(message: Message, state):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    ref = await referals.find_one({'userid': userid, 'type': 'sub'}, comment='enter_code_ref')
    if not ref:
        await bot.send_message(chatid, t('referals.enter_code.start', lang), parse_mode='Markdown', reply_markup=cancel_markup(lang))
        await ChooseStringState(check_code, userid, chatid, lang, max_len=100)
    else:
        await bot.send_message(chatid, t('referals.enter_code.have_code', lang), parse_mode='Markdown')