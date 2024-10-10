from time import time

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import (escape_markdown, list_to_inline,
                                     seconds_to_str, user_name)
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import premium, user_info
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command, StateFilter

from aiogram.fsm.context import FSMContext

management = DBconstructor(mongo_client.other.management)

@HDMessage
@main_router.message(Text('commands_name.profile.information'), 
                     IsAuthorizedUser(), IsPrivateChat())
async def infouser(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    if message.from_user:
        text = await user_info(userid, lang, 
                               name=user_name(message.from_user))

        photos = await bot.get_user_profile_photos(userid, limit=1)
        if photos.photos:
            photo_id = photos.photos[0][0].file_id
            await bot.send_photo(chatid, photo_id, caption=text, parse_mode='Markdown')
        else:
            await bot.send_message(message.chat.id, text, parse_mode='Markdown')

@HDMessage
@main_router.message(Command(commands=['profile']), IsAuthorizedUser(), IsPrivateChat())
async def infouser_com(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    if message.from_user:
        text = await user_info(userid, lang, 
                               name=user_name(message.from_user))

        photos = await bot.get_user_profile_photos(userid, limit=1)
        if photos.photos:
            photo_id = photos.photos[0][0].file_id 
            await bot.send_photo(chatid, photo_id, caption=text, parse_mode='Markdown')
        else:
            await bot.send_message(message.chat.id, text, parse_mode='Markdown')

@HDMessage
@main_router.message(Text('commands_name.profile.rayting'), 
                     IsAuthorizedUser(), IsPrivateChat())
async def rayting(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    time_update_rayt = 0

    t_upd = await management.find_one({'_id': 'rayt_update'}, comment='rayting_t_upd')
    if t_upd:
        time_update_rayt = seconds_to_str(int(time()) - t_upd['time'], lang)
        if t_upd['time'] == 0:

            text = t("rayting.no_rayting", lang)
            await bot.send_message(chatid, text)
        else:
            text = f'{t("rayting.info", lang)}\n_{time_update_rayt}_'
            text_data = get_data('rayting', lang)

            buttons = {}
            for i in ['lvl', 'coins', 'super']: # 'dungeon',
                buttons[text_data[i]] = f'rayting {i}'

            markup = list_to_inline([buttons])
            await bot.send_message(chatid, text, reply_markup=markup, parse_mode='Markdown')

@HDCallback
@main_router.callback_query(F.data.startswith('rayting'))
async def rayting_call(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)
    rayt_data = {}

    rayt_data = await management.find_one({'_id': f'rayting_{data[1]}'},    
                                          comment='rayting_call_rayt_data')
    if len(data) > 2: 
        max_ind = int(data[2]) + 4
        min_ind = max_ind - 10
    else:  max_ind, min_ind = 10, 0

    if rayt_data:
        add_my_rivals, text = False, ''
        markup, my_place = None, 0

        if userid in rayt_data['ids']:
            my_place = rayt_data['ids'].index(userid) + 1
        top_10 = rayt_data['data'][min_ind:max_ind]
        if my_place > 10: add_my_rivals = True

        text += t(f"rayting.rayting_{data[1]}", lang) + '\n'
        text += t("rayting.place", lang, place=my_place) + '\n\n'

        for user in top_10:
            sign, add_text = '*├*', ''
            if user == top_10[-1]: sign = '*└*'

            try:
                chat_user = await bot.get_chat_member(user['userid'], 
                                                      user['userid'])
                name = escape_markdown(user_name(chat_user.user, False))
            except: name = str(user['userid'])

            n = rayt_data['ids'].index(user['userid']) + 1
            if n == 1: n = '🥇'
            elif n == 2: n = '🥈'
            elif n == 3: n = '🥉'

            if await premium(user['userid']):
                add_text += t(f"rayting.premium", lang) + '\n     '

            add_text += t(f"rayting.{data[1]}_text", lang, **user)
            text += f'{sign} #{n} *{name}*\n     {add_text}\n'

        if add_my_rivals:
            but_name = t("rayting.my_place", lang)
            buttons = [{but_name: f'rayting {data[1]} {my_place}'}]
            markup = list_to_inline(buttons)

        try:
            await bot.edit_message_text(text, None, chatid, callback.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception as e:
            log(message=f'Rayting edit error {e}', lvl=2)
