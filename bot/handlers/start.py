from random import choice

from telebot import types

from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.handlers.states import cancel
from bot.modules.data_format import list_to_keyboard, seconds_to_str, user_name
from bot.modules.dinosaur import incubation_egg
from bot.modules.images import async_open, create_eggs_image
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import markups_menu as m
from bot.modules.user import insert_user
from bot.modules.referals import connect_referal
from bot.handlers.referal_menu import check_code
from bot.modules.promo import use_promo
 
from bot.modules.tracking import add_track

referals = mongo_client.user.referals
management = mongo_client.other.management

@bot.message_handler(pass_bot=True, commands=['start'], is_authorized=True, private=True)
async def start_command_auth(message: types.Message):
    stickers = await bot.get_sticker_set('Stickers_by_DinoGochi_bot')
    sticker = choice(list(stickers.stickers)).file_id

    lang = await get_lang(message.from_user.id)
    await bot.send_sticker(message.chat.id, sticker, 
                           reply_markup=await m(message.from_user.id, language_code=lang))

    content = str(message.text).split()
    if len(content) > 1:
        referal = str(content[1])

        await check_code(referal, 
                         {'userid': message.from_user.id,
                          'chatid': message.chat.id,
                          'lang': await get_lang(message.from_user.id)}, False)

        track = await management.find_one({'_id': 'tracking_links'})
        if referal in track['links']:
            await management.update_one({'_id': 'tracking_links'}, {"$inc": {f"{referal}.col": 1}})

        lang = await get_lang(message.from_user.id)
        st, text = await use_promo(referal, message.from_user.id, lang)

        if st == 'ok':
            await bot.send_message(message.chat.id, text)

@bot.message_handler(text='commands_name.start_game', is_authorized=False)
async def start_game(message: types.Message, code: str = '', code_type: str = ''):

    #Сообщение-реклама
    text = t('start_command.request_subscribe.text', message.from_user.language_code)
    b1, b2 = get_data('start_command.request_subscribe.buttons', message.from_user.language_code)

    markup_inline = types.InlineKeyboardMarkup()
    markup_inline.add(types.InlineKeyboardButton(text=b1, url='https://t.me/DinoGochi'))
    markup_inline.add(types.InlineKeyboardButton(text=b2, url='https://t.me/+pq9_21HXXYY4ZGQy'))

    await bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup_inline)

    #Создание изображения
    img, id_l = await create_eggs_image()

    markup_inline = types.InlineKeyboardMarkup()
    markup_inline.add(*[types.InlineKeyboardButton(
            text=f'🥚 {id_l.index(i) + 1}', 
            callback_data=f'start_egg {i} {code_type} {code}') for i in id_l]
    )

    start_game = t('start_command.start_game', message.from_user.language_code)
    await bot.send_photo(message.chat.id, img, start_game, reply_markup=markup_inline)

@bot.message_handler(pass_bot=True, commands=['start'], is_authorized=False)
async def start_game_message(message: types.Message):
    langue_code = message.from_user.language_code
    username = user_name(message.from_user)

    content = str(message.text).split()
    add_referal = False
    markup = None
    referal = ''

    if len(content) > 1: 
        referal = str(content[1])
        if await referals.find_one({'code': referal}): add_referal = True
        await add_track(content[1])

    if not add_referal:
        buttons_list = [get_data('commands_name.start_game', locale=langue_code)]
        markup = list_to_keyboard(buttons_list)

    image = await async_open('images/remain/start/placeholder.png', True)
    text = t('start_command.first_message', langue_code, username=username)

    await bot.send_photo(message.chat.id, image, text, reply_markup=markup, parse_mode='HTML')

    if add_referal:
        text = t('start_command.referal', langue_code, username=username)
        await bot.send_message(message.chat.id, text)

        await start_game(message, referal, 'referal') 


@bot.callback_query_handler(pass_bot=True, is_authorized=False, 
                            func=lambda call: call.data.startswith('start_egg'), private=True)
async def egg_answer_callback(callback: types.CallbackQuery):
    egg_id = int(callback.data.split()[1])
    lang = callback.from_user.language_code
    userid = callback.from_user.id

    # Сообщение
    edited_text = t('start_command.end_answer.edited_text', lang)
    send_text = t('start_command.end_answer.send_text', lang, inc_time=
                  seconds_to_str(GAME_SETTINGS['first_dino_time_incub'], lang))

    await bot.edit_message_caption(edited_text, callback.message.chat.id, callback.message.message_id)
    await bot.send_message(callback.message.chat.id, send_text, parse_mode='Markdown', 
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

@bot.callback_query_handler(pass_bot=True, is_authorized=True, 
                            func=lambda call: call.data.startswith('start_cmd'), private=True)
async def start_inl(callback: types.CallbackQuery):
    """ start_cmd promo/  
    """
    lang = await get_lang(callback.from_user.id)
    userid = callback.from_user.id
    content = ''

    spl = callback.data.split()
    if len(spl) > 1: content = spl[1]

    stickers = await bot.get_sticker_set('Stickers_by_DinoGochi_bot')
    sticker = choice(list(stickers.stickers)).file_id

    lang = await get_lang(userid)
    await bot.send_sticker(callback.message.chat.id, sticker, 
                           reply_markup=await m(userid, language_code=lang))

    if content:
        lang = await get_lang(userid)
        st, text = await use_promo(content, userid, lang)

        if st == 'ok':
            await bot.send_message(callback.message.chat.id, text)