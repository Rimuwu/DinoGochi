from random import choice

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot, botworker
from bot.handlers.referal_menu import check_code
from bot.handlers.states import cancel
from bot.modules.data_format import list_to_keyboard, seconds_to_str, user_name
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import incubation_egg
from bot.modules.images import async_open, create_eggs_image
from bot.modules.images_save import send_SmartPhoto
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.managment.promo import use_promo
from bot.modules.managment.referals import connect_referal
from bot.modules.managment.tracking import add_track
from bot.modules.user.user import award_premium, insert_user
from aiogram import types

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command


referals = DBconstructor(mongo_client.user.referals)
management = DBconstructor(mongo_client.other.management)
dead_users = DBconstructor(mongo_client.other.dead_users)

@bot.message(Command(commands=['start']), IsAuthorizedUser(), IsPrivateChat())
@HDMessage
async def start_command_auth(message: types.Message):
    stickers = await botworker.get_sticker_set('Stickers_by_DinoGochi_bot')
    sticker = choice(list(stickers.stickers)).file_id

    lang = await get_lang(message.from_user.id)
    await botworker.send_sticker(message.chat.id, sticker, 
                           reply_markup=await m(message.from_user.id, language_code=lang))

    content = str(message.text).split()
    if len(content) > 1:
        referal = str(content[1])

        await check_code(referal, 
                         {'userid': message.from_user.id,
                          'chatid': message.chat.id,
                          'lang': await get_lang(message.from_user.id)}, False)

        track = await management.find_one({'_id': 'tracking_links'}, comment='start_command_auth_track')
        if referal in track['links']: # type: ignore
            await management.update_one({'_id': 'tracking_links'}, 
                                        {"$inc": {f"{referal}.col": 1}}, 
                                        comment='start_command_auth_management')

        lang = await get_lang(message.from_user.id)
        st, text = await use_promo(referal, message.from_user.id, lang)

        if st == 'ok':
            await botworker.send_message(message.chat.id, text)

@bot.message(Text('commands_name.start_game'), IsAuthorizedUser(False))
@HDMessage
async def start_game(message: types.Message, code: str = '', code_type: str = ''):

    #Сообщение-реклама
    text = t('start_command.request_subscribe.text', message.from_user.language_code)
    b1, b2 = get_data('start_command.request_subscribe.buttons', message.from_user.language_code)

    markup_inline = []
    markup_inline.append(types.InlineKeyboardButton(text=b1, url='https://t.me/DinoGochi'))
    markup_inline.append(types.InlineKeyboardButton(text=b2, url='https://t.me/+pq9_21HXXYY4ZGQy'))

    inl = types.InlineKeyboardMarkup(inline_keyboard=markup_inline)
    await botworker.send_message(message.chat.id, text, parse_mode='html', reply_markup=inl)

    #Создание изображения
    img, id_l = await create_eggs_image()

    markup_inline = []
    markup_inline.append(*[types.InlineKeyboardButton(
            text=f'🥚 {id_l.index(i) + 1}', 
            callback_data=f'start_egg {i} {code_type} {code}') for i in id_l]
    )
    inl = types.InlineKeyboardMarkup(inline_keyboard=markup_inline)

    start_game = t('start_command.start_game', message.from_user.language_code)
    await botworker.send_photo(message.chat.id, img, start_game, reply_markup=inl)

@bot.message(Command(commands=['start']), IsAuthorizedUser(False))
@HDMessage
async def start_game_message(message: types.Message):
    langue_code = message.from_user.language_code
    if not langue_code: langue_code = 'en'

    username = user_name(message.from_user)

    content = str(message.text).split()
    add_referal = False
    markup = None
    referal = ''

    if len(content) > 1: 
        referal = str(content[1])
        if await referals.find_one({'code': referal}, comment='start_game_message'): add_referal = True
        await add_track(content[1])

    if not add_referal:
        buttons_list = [get_data('commands_name.start_game', locale=langue_code)]
        markup = list_to_keyboard(buttons_list)

    image = await async_open('images/remain/start/placeholder.png', True)
    text = t('start_command.first_message', langue_code, username=username)

    await send_SmartPhoto(message.chat.id, image, text, 'HTML', markup)

    if add_referal:
        text = t('start_command.referal', langue_code, username=username)
        await botworker.send_message(message.chat.id, text)

        await start_game(message, referal, 'referal') 


@bot.callback_query(IsAuthorizedUser(False), 
                            F.data.startswith('start_egg'), IsPrivateChat())
@HDCallback
async def egg_answer_callback(callback: types.CallbackQuery):
    egg_id = int(callback.data.split()[1])
    lang = callback.from_user.language_code
    userid = callback.from_user.id

    # Сообщение
    edited_text = t('start_command.end_answer.edited_text', lang)
    send_text = t('start_command.end_answer.send_text', lang, inc_time=
                  seconds_to_str(GAME_SETTINGS['first_dino_time_incub'], lang))

    await botworker.edit_message_caption(edited_text, callback.message.chat.id, callback.message.message_id)
    await botworker.send_message(callback.message.chat.id, send_text, parse_mode='Markdown', 
                           reply_markup= await m(callback.from_user.id, language_code=lang))

    # Создание юзера и добавляем динозавра в инкубацию
    await insert_user(callback.from_user.id, lang)
    await incubation_egg(egg_id, callback.from_user.id, quality=GAME_SETTINGS['first_egg_rarity'])

    if len(callback.data.split()) > 2:
        if callback.data.split()[2] == 'referal':
            referal = callback.data.split()[3]
            await connect_referal(referal, callback.from_user.id)

        if callback.data.split()[2] == 'promo':
            code = callback.data.split()[3]
            await use_promo(code, userid, lang)

@bot.callback_query(IsAuthorizedUser(), 
                            F.data.startswith('start_cmd'), IsPrivateChat())
@HDCallback
async def start_inl(callback: types.CallbackQuery):
    """ start_cmd promo/  
    """
    lang = await get_lang(callback.from_user.id)
    userid = callback.from_user.id
    content = ''

    spl = callback.data.split()
    if len(spl) > 1: content = spl[1]
    
    if content:
        # Активация премиума после возвращения 
        fr = await dead_users.find_one({'promo': content})
        if fr:
            await award_premium(fr['userid'], 259_200) # 3 дня
            await dead_users.delete_one({'_id': fr['_id']})

            lang = await get_lang(userid)
            text = '✨'
            await botworker.send_message(callback.message.chat.id, text, 
                            reply_markup=await m(userid, language_code=lang))
    
    else:
        stickers = await botworker.get_sticker_set('Stickers_by_DinoGochi_bot')
        sticker = choice(list(stickers.stickers)).file_id

        lang = await get_lang(userid)
        await botworker.send_sticker(callback.message.chat.id, sticker, 
                            reply_markup=await m(userid, language_code=lang))