from datetime import datetime, timedelta
from random import randint
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import main_router, bot
from bot.handlers.states import ChooseInt
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino, get_dino_data, random_dino, random_quality, set_standart_specifications
from bot.modules.images import async_open
from bot.modules.inline import inline_menu
from bot.modules.items.item import (CheckCountItemFromUser, RemoveItemFromUser,
                              counts_items, get_name)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import cancel_markup, confirm_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import ChooseInlineState, ChooseIntState, ChooseStepState
from bot.modules.user.inside_shop import get_content, item_buyed
from bot.modules.user.user import (AddItemToUser, check_name, daily_award_con,
                              get_dinos, take_coins, user_in_chat)
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from bot.modules.markup import markups_menu as m

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command

inside_shop = DBconstructor(mongo_client.tavern.inside_shop)

async def page_context(userid, lang):
    items = await get_content(userid)
    text = t('inside_shop.info', lang)
    rmk_data = {}

    for key, value in items.items():
        name = get_name(key, lang)
        col = value['count']
        price = value['price']
        
        if col > 0:
            text += t('inside_shop.item', lang,
                    name=name, col=col, price=price) + '\n\n'
            rmk_data[name] = f'hoarder {key}'

    text += t('inside_shop.down', lang)
    rmk = list_to_inline([rmk_data], 2)
    return text, rmk

@main_router.message(Text('commands_name.dino_tavern.hoarder'), IsAuthorizedUser(), IsPrivateChat())
@HDMessage
async def hoarder(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    userid = message.from_user.id

    text, rmk = await page_context(userid, lang)
    await bot.send_message(message.chat.id, text, parse_mode='Markdown',
          reply_markup = rmk)

@main_router.callback_query(F.data.startswith('hoarder'), IsPrivateChat())
@HDCallback
async def hoarder_calb(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    key = call_data[1]

    items = await get_content(userid)
    if key in items:
        item = items[key]

        transmitted_data = {
            'item': key,
            'messageid': call.message.id
        }
        await ChooseIntState(buy_item, userid, chatid, lang, max_int=item['count'], autoanswer=False, transmitted_data=transmitted_data)
        await bot.send_message(chatid, t('inside_shop.count', lang), 
                               parse_mode='Markdown', 
                               reply_markup=count_markup(item['count'], lang))

    else:
        await bot.send_message(chatid, t('inside_shop.no_item', lang), 
                               parse_mode='Markdown')

async def buy_item(count, transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    item = transmitted_data['item']
    messageid = transmitted_data['messageid']

    res = await item_buyed(userid, item, count)
    await bot.send_message(chatid, t(f'inside_shop.{res}', lang), 
                               parse_mode='Markdown', reply_markup = await m(userid, 'last_menu', lang))

    if res:
        text, rmk = await page_context(userid, lang)
        await bot.edit_message_text(text, None, chatid, messageid, reply_markup=rmk, parse_mode='Markdown')
