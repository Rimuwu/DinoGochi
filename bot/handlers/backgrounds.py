
from bot.dbmanager import mongo_client
from bot.const import BACKGROUNDS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, list_to_keyboard
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino
from bot.modules.images import async_open
from bot.modules.inline import list_to_inline
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import confirm_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import (ChooseConfirmState, ChooseDinoState, ChooseImageState,
                                      ChooseIntState, ChooseStringState)
from bot.modules.user.user import premium, take_coins
from telebot.types import CallbackQuery, InputMedia, Message

users = DBconstructor(mongo_client.user.users)

async def back_edit(content, transmitted_data: dict):
    dino = transmitted_data['dino']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    if content == 'no_image':
        content = 1
        tt = 'saved'
    else:
        tt = 'custom'
        file_info = await bot.get_file(content)
        downloaded_file = await bot.download_file(file_info.file_path)
        if downloaded_file:
            content = content
        else:
            content = 0

    if content:
        await dino.update({
            '$set': {
                "profile.background_type": tt,
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
    await ChooseImageState(back_edit, userid, chatid, lang, True, transmitted_data=data)
    await bot.send_message(userid, text, reply_markup=markup)

@bot.message_handler(pass_bot=True, text='commands_name.backgrounds.custom_profile', 
                     is_authorized=True, private=True)
@HDMessage
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
                     is_authorized=True, private=True)
@HDMessage
async def standart(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await ChooseDinoState(standart_end, userid, chatid, lang, False)

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

def near_back(key: int, step: int, storage: list[int] = []):
    if BACKGROUNDS[str(key)]['show']:
        return key
    else:
        return key

async def back_page(userid: int, page: int, lang: str):
    user = await users.find_one({"userid": userid}, comment='back_page_user')
    text_data = get_data('backgrounds', lang)
    storage = user['saved']['backgrounds']
    back = BACKGROUNDS[str(page)]

    if 'author' in back:
        add_text = '\n' + text_data['author'] + escape_markdown(back['author'])
    else: add_text = ' '

    if page - 1 < 1:
        left = near_back(int(list(BACKGROUNDS.keys())[-1]), 
                         -1, storage)
    else:
        left = near_back(page - 1, -1, storage)

    if str(page + 1) not in list(BACKGROUNDS.keys()):
        right = near_back(1, 1, storage)
    else:
        right = near_back(page + 1, 1, storage)

    if page in storage:
        buttons = {
            f"◀ {left}": f"back_m page {left}",
            text_data['buttons']['page_n']: f"back_m page_n {page}",
            f"{right} ▶": f"back_m page {right}",
            text_data['buttons']['set']: f"back_m set {page}",
        }

        text = t('backgrounds.description_set', lang, add_text=add_text)

    else:
        buttons = {
            f"◀ {left}": f"back_m page {left}",
            text_data['buttons']['page_n']: f"back_m page_n {page}",
            f"{right} ▶": f"back_m page {right}",
        }

        if back['show']:
            buttons[ f"{back['price']['coins']} 🪙" ] = f'back_m buy_coins {page}'
            buttons[ f"{back['price']['super_coins']} 👑" ] = f'back_m buy_super_coins {page}'

        text = t('backgrounds.description_buy', lang, add_text=add_text)

    text += f'\n\n*№ {page}*'

    markup = list_to_inline([buttons])
    image = await async_open(f'images/backgrounds/{page}.png', True)
    return text, markup, image

@bot.message_handler(pass_bot=True, text='commands_name.backgrounds.backgrounds', 
                     is_authorized=True, private=True)
@HDMessage
async def backgrounds(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    text, markup, image = await back_page(userid, 1, lang)
    await bot.send_photo(chatid, image, text,
                parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('back_m '), private=True)
@HDCallback
async def kindergarten(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    b_id = int(split_d[2])

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    back = BACKGROUNDS[str(b_id)]

    if action == 'page':

        text, markup, image = await back_page(userid, b_id, lang)
        await bot.edit_message_media(
            chat_id=chatid,
            message_id=call.message.id,
            media=InputMedia(
                type='photo', media=image, 
                parse_mode='Markdown', caption=text),
            reply_markup=markup
        )

    elif action == 'page_n':
        max_int = int(list(BACKGROUNDS.keys())[-1])
        mes = await bot.send_message(chatid, t('backgrounds.page', lang),
                                     reply_markup=count_markup(max_int, lang)
                                     )

        data = { 'message_id': call.message.id, 'delete_id': mes.id }
        await ChooseIntState(page_n, userid, chatid, lang,
                             max_int=max_int, 
                             transmitted_data=data)


    elif action in ['buy_coins', 'buy_super_coins']:
        user = await users.find_one({"userid": userid}, comment='kindergarten_user')
        storage = user['saved']['backgrounds']

        if int(b_id) not in storage:
            data = {
                'price': back['price'],
                'buy_type': action,
                'page': b_id,
                'message_id': call.message.id
            }
            mes = await bot.send_message(chatid, t('backgrounds.confirm', lang),
                                        reply_markup=confirm_markup(lang)
                                        )
            data['delete_id'] = mes.id
            await ChooseConfirmState(buy, userid, chatid, lang, transmitted_data=data)
    
    elif action == 'set':
        # mes = await bot.send_message(chatid, t('backgrounds.choose_dino', lang),
        #                                 reply_markup=confirm_markup(lang)
        #                                 )
        data = { 'page': b_id } # 'delete_id': mes.id,
        await ChooseDinoState(set_back, userid, chatid, lang, False, True, data)
        
async def set_back(dino: Dino, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    page = transmitted_data['page']

    await dino.update({'$set': {
        'profile.background_type': 'saved',
        'profile.background_id': page 
        }})

    await bot.send_message(chatid, t('backgrounds.set', lang), 
                        reply_markup= await m(userid, 'last_menu', lang))
    if 'umessageid' in transmitted_data:
        await bot.delete_message(chatid, transmitted_data['umessageid'])

    # await bot.delete_message(chatid, transmitted_data['delete_id'])

async def buy(_: bool, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    price = transmitted_data['price']
    buy_type = transmitted_data['buy_type']
    message_id = transmitted_data['message_id']
    page = transmitted_data['page']

    res = False

    if buy_type == 'buy_super_coins':
        user = await users.find_one({"userid": userid}, comment='buy_user')
        if price['super_coins'] <= user['super_coins']:
            res = True

            await users.update_one({'userid': userid}, {'$inc': {
            'super_coins': -price['super_coins']}}, comment='buy_await')

    else:
        res = await take_coins(userid, -price['coins'], True)

    if res:
        await bot.send_message(chatid, t('backgrounds.buy', lang), 
                        reply_markup= await m(userid, 'last_menu', lang))

        await users.update_one({'userid': userid}, {'$push': {
            'saved.backgrounds': int(page)
        }}, comment='buy_res')

        text, markup, image = await back_page(userid, int(page), lang)
        await bot.edit_message_media(
            chat_id=chatid,
            message_id=message_id,
            media=InputMedia(
                type='photo', media=image, 
                parse_mode='Markdown', caption=text),
            reply_markup=markup
        )

    else:
        await bot.send_message(chatid, t('backgrounds.no_coins', lang), 
                        reply_markup= await m(userid, 'last_menu', lang))

    await bot.delete_message(chatid, transmitted_data['delete_id'])
    await bot.delete_message(chatid, transmitted_data['umessageid'])

async def page_n(number: int, transmitted_data: dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    message_id = transmitted_data['message_id']

    user = await users.find_one({"userid": userid}, comment='page_n_user')
    storage = user['saved']['backgrounds']

    page = near_back(number, -1, storage)
    text, markup, image = await back_page(userid, page, lang)
    await bot.edit_message_media(
        chat_id=chatid,
        message_id=message_id,
        media=InputMedia(
            type='photo', media=image, 
            parse_mode='Markdown', caption=text),
        reply_markup=markup
    )

    await bot.send_message(chatid, t('backgrounds.page_set', lang), 
                            reply_markup= await m(userid, 'last_menu', lang))

    await bot.delete_message(chatid, transmitted_data['delete_id'])
    await bot.delete_message(chatid, transmitted_data['umessageid'])