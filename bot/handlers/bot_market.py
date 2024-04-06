from datetime import datetime, timedelta
from time import time
from random import randint

from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from bot.config import conf, mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.dinosaur import Dino, random_dino, random_quality
from bot.modules.images import async_open
from bot.modules.item import counts_items, RemoveItemFromUser, CheckCountItemFromUser, counts_items
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import cancel_markup, confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.inline import inline_menu
from bot.modules.states_tools import (ChooseDinoState,
                                      ChooseDinoState, ChooseInlineState,
                                      ChoosePagesState, ChooseStepState)
from bot.modules.user import (AddItemToUser, check_name, daily_award_con,
                              take_coins, user_in_chat, get_dinos)






# @bot.callback_query_handler(pass_bot=True, func=lambda call: 
#     call.data.startswith('ads_limit'), private=True)
# async def ads_limit(call: CallbackQuery):
#     chatid = call.message.chat.id
#     user_id = call.from_user.id
#     lang = await get_lang(call.from_user.id)
    

@bot.message_handler(pass_bot=True, text='commands_name.bot_market.background_market', 
                     is_authorized=True)
async def background_market(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    await ChooseDinoState(back_shop, userid, chatid, lang, False)
    

async def back_shop(dino: Dino, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']