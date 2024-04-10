import io
import requests
from telebot.types import CallbackQuery, Message

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.data_format import chunks, list_to_keyboard, escape_markdown
from bot.modules.dinosaur import Dino
from bot.modules.images import async_open
from bot.modules.localization import get_data, t, get_lang, get_all_locales
from bot.modules.markup import confirm_markup, cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.markup import tranlate_data
from bot.modules.states_tools import (ChooseConfirmState, ChooseDinoState,
                                      ChooseOptionState, ChooseStringState, ChooseStepState)
from bot.modules.user import premium, User
from random import randint
from bot.const import BACKGROUNDS

users = mongo_client.user.users
langs = mongo_client.user.lang

async def back_edit(content: str, transmitted_data: dict):
    dino = transmitted_data['dino']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    try:
        response = requests.get(content, stream = True)
        response = await async_open(io.BytesIO(response.content))
        response = response.convert("RGBA")
    except: content = ''
    
    if content:
        await dino.update({
            '$set': {
                "profile.background_type": 'custom',
                'profile.background_id': content
            }
        })

        text = t('custom_profile.ok', lang)
    else:
        text = t('custom_profile.error', lang)

    await bot.send_message(chatid, text, 
                            reply_markup= await m(userid, 'last_menu', lang))

async def transition_back(dino: Dino, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    text = t('custom_profile.manual', lang)
    keyboard = [t('buttons_name.cancel', lang)]
    markup = list_to_keyboard(keyboard, one_time_keyboard=True)

    data = {
        'dino': dino
    }
    await ChooseStringState(back_edit, userid, chatid, lang, max_len=200, transmitted_data=data)
    await bot.send_message(userid, text, reply_markup=markup)

@bot.message_handler(pass_bot=True, text='commands_name.backgrounds.custom_profile', 
                     is_authorized=True)
async def custom_profile(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    if await premium(userid):
        await ChooseDinoState(transition_back, userid, message.chat.id, lang, False)
    else:
        text = t('no_premium', lang)
        await bot.send_message(userid, text)


@bot.message_handler(pass_bot=True, text='commands_name.backgrounds.standart', 
                     is_authorized=True)
async def standart(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    await ChooseDinoState(standart_end, userid, message.chat.id, lang, False)
    
async def standart_end(dino: Dino, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    
    await dino.update({
            '$set': {
                "profile.background_type": 'standart',
                'profile.background_id': 0
            }
        })

    await bot.send_message(chatid, t('standart_background', lang), 
                            reply_markup= await m(userid, 'last_menu', lang))


async def back_page(userid: int, page: int):
    user = users.find_one({"userid": userid})

    if page in user['saved']['backgrounds']:
        buttons = {
            "◀": f"page {}",
            "": ""
            "▶": f"page {}"
        }
    
    else:
        buttons = {
            "◀": f"page {}",
            "🛒": f"buy {page}"
            "▶": f"page {}"
        }

@bot.message_handler(pass_bot=True, text='commands_name.backgrounds.backgrounds', 
                     is_authorized=True)
async def backgrounds(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    
    
