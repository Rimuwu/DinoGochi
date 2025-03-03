from random import choice

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.add_product.add_product import prepare_data_option
from bot.modules.data_format import (escape_markdown, list_to_inline,
                                     list_to_keyboard)
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.item import item_info
from bot.modules.localization import get_lang, t
from bot.modules.market.market import (create_push, create_seller, delete_product,
                                preview_product, product_ui, seller_ui)
from bot.modules.market.market_chose import (buy_item, find_prepare,
                                      pr_edit_description, pr_edit_image,
                                      pr_edit_name, prepare_add,
                                      prepare_delete_all, prepare_edit_price,
                                      promotion_prepare, send_info_pr)
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import (ChooseOptionState, ChoosePagesState,
                                      ChooseStepState)
from bot.modules.user.user import premium, user_name
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

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

users = DBconstructor(mongo_client.user.users)
sellers = DBconstructor(mongo_client.market.sellers)
products = DBconstructor(mongo_client.market.products)
puhs = DBconstructor(mongo_client.market.puhs)

async def create_adapter(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    name = return_data['name']
    description = return_data['description']
    description = escape_markdown(description)
    await create_seller(userid, name, description)

    await bot.send_message(chatid, t('market_create.create', lang), 
                           reply_markup= await m(userid, 'seller_menu', lang), parse_mode='Markdown')

async def custom_name(message: Message, transmitted_data):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    max_len = 50
    min_len = 3

    content = str(message.text)
    content_len = len(content)
    name = escape_markdown(content)

    if content_len > max_len:
        await bot.send_message(message.chat.id, 
                t('states.ChooseString.error_max_len', lang,
                number = content_len, max = max_len))
    elif content_len < min_len:
        await bot.send_message(message.chat.id, 
                t('states.ChooseString.error_min_len', lang,
                number = content_len, min = min_len))
    elif await sellers.find_one({'name': name}, comment='custom_name'):
        await bot.send_message(message.chat.id, 
                t('market_create.name_error', lang))
    else: 
        return True, name
    return False, None

@HDMessage
@main_router.message(Text('commands_name.seller_profile.create_market'), IsAuthorizedUser(), IsPrivateChat())
async def create_market(message: Message, state: FSMContext):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    res = await sellers.find_one({'owner_id': userid}, comment='create_market_res')
    user = await users.find_one({'userid': userid}, comment='create_market_user')

    if res or not user:
        await bot.send_message(message.chat.id, t('menu_text.seller', lang), 
                           reply_markup= await m(userid, 'market_menu', lang))
    elif user['lvl'] < 2:
        await bot.send_message(message.chat.id, t('market_create.lvl', lang))
    else:
        transmitted_data = {}
        steps = [
            {
             "type": 'custom', "name": 'name',
                "data": {'custom_handler': custom_name},
             "translate_message": True,
             'message': {
                'text': "market_create.name",
                'reply_markup': cancel_markup(lang)}
            },
            {
             "type": 'str', "name": 'description', "data": {'max_len': 500}, 
             "translate_message": True,
             'message': {
                'text': "market_create.description",
                'reply_markup': cancel_markup(lang)}
            }
        ]

        await ChooseStepState(create_adapter, userid, chatid, 
                              lang, steps, 
                              transmitted_data=transmitted_data)

@HDMessage
@main_router.message(Text('commands_name.seller_profile.my_market'), IsAuthorizedUser(), IsPrivateChat())
async def my_market(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    res = await sellers.find_one({'owner_id': userid}, comment='my_market_res')
    if res:
        text, markup, image = await seller_ui(userid, lang, True)
        try:
            await bot.send_photo(chatid, image, caption=text, parse_mode="Markdown", reply_markup=markup)
        except:
            await bot.send_photo(chatid, image, caption=text, reply_markup=markup, parse_mode=None)

@HDMessage
@main_router.message(Text('commands_name.seller_profile.add_product'), IsAuthorizedUser(), IsPrivateChat())
async def add_product_com(message: Message, state):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    options = {
        "🍕 ➞ 🪙": 'items_coins',
        "🪙 ➞ 🍕": 'coins_items',
        "🍕 ➞ 🍕": 'items_items',
        "🍕 ➞ ⏳": 'auction'
    }

    b_list = list(options.keys())
    markup = list_to_keyboard(
        [b_list, t('buttons_name.cancel', lang)], 2
    )

    await bot.send_message(chatid, t('add_product.options_info', lang), reply_markup=markup)
    await ChooseOptionState(prepare_data_option, userid, chatid, lang, options)

@HDMessage
@main_router.message(Text('commands_name.seller_profile.my_products'), IsAuthorizedUser(), IsPrivateChat())
async def my_products(message: Message, state):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user_prd = await products.find({'owner_id': userid}, comment='my_products_user_prd')
    rand_p = {}

    if user_prd:
        for product in user_prd:
            rand_p[
                preview_product(product['items'], product['price'], 
                                product['type'], lang)
            ] = product['_id']

        await bot.send_message(chatid, t('products.search', lang))
        await ChoosePagesState(send_info_pr, userid, chatid, lang, rand_p, 1, 3, 
                               None, False, False)
    else:
        text = t('no_products', lang)
        await bot.send_message(chatid, text,  parse_mode='Markdown')

@HDCallback
@main_router.callback_query(F.data.startswith('product_info'))
async def product_info(call: CallbackQuery, state):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    call_type = call_data[1]
    alt_id = call_data[2]
    product = await products.find_one({'alt_id': alt_id}, comment='product_info_product')
    if product:
        if call_type == 'delete':
            if product['owner_id'] == userid:

                await bot.edit_message_reply_markup(None, chatid, call.message.message_id, reply_markup=list_to_inline([]))

                status = await delete_product(None, alt_id)

                if status: text = t('product_info.delete', lang)
                else: text = t('product_info.error', lang)

                markup = list_to_inline([])
                await bot.edit_message_text(text, None, chatid, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        else:
            if call_type == 'edit_price' and product['owner_id'] == userid:
                await prepare_edit_price(userid, chatid, lang, alt_id, state)

            elif call_type == 'add' and product['owner_id'] == userid:
                await prepare_add(userid, chatid, lang, alt_id, state)

            elif call_type == 'items':
                itm = []
                for item in product['items']:
                    if item not in itm:
                        itm.append(item)
                        text, image = await item_info(item, lang)

                        if image:
                            await send_SmartPhoto(chatid, image, text, 'Markdown')

            elif call_type == 'buy' and product['owner_id'] != userid:
                if product['owner_id'] != userid:
                    await buy_item(userid, chatid, lang, product, 
                                   await user_name(userid), call.message.message_id, state)

            elif call_type == 'info':
                text, markup = await product_ui(lang, product['_id'], 
                                          product['owner_id'] == userid)
                await bot.send_message(userid, text, reply_markup=markup, parse_mode='Markdown')

            elif call_type == 'promotion' and product['owner_id'] == userid:
                await promotion_prepare(userid, chatid, lang, product['_id'], 
                                        call.message.message_id, state)

@HDCallback
@main_router.callback_query(F.data.startswith('seller'), IsPrivateChat())
async def seller(call: CallbackQuery, state):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    call_type = call_data[1]
    owner_id = int(call_data[2])

    # Кнопки вызываемые владельцем
    if call_type == 'cancel_all':
        await prepare_delete_all(userid, chatid, lang, call.message.message_id, state)
    elif call_type == 'edit_text':
        await pr_edit_description(userid, chatid, lang, call.message.message_id, state)
    elif call_type == 'edit_name':
        await pr_edit_name(userid, chatid, lang, call.message.message_id, state)
    elif call_type == 'edit_image':
        if await premium(userid):
            await pr_edit_image(userid, chatid, lang, call.message.message_id, state)
        else:
            await bot.send_message(chatid, t('no_premium', lang))

    # Кнопки вызываемые не владельцем
    elif call_type == 'info':
        my_status = owner_id == userid

        seller = await sellers.find_one({'owner_id': owner_id}, comment='seller_seller')
        if seller:
            seller_user = await users.find_one({'_id': owner_id}, comment='seller_user')
            if seller_user: 
                name = seller_user['name']
            else: name = 'NoName'

            text, markup, image = await seller_ui(owner_id, lang, my_status, name)
            try:
                await bot.send_photo(chatid, image, caption=text, parse_mode='Markdown', reply_markup=markup)
            except:
                await bot.send_photo(chatid, image, caption=text, reply_markup=markup)

    elif call_type == 'all':
        user_prd = await products.find({'owner_id': owner_id}, comment='seller_user_prd_all')

        rand_p = {}
        for product in user_prd:
            rand_p[
                preview_product(product['items'], product['price'], 
                                product['type'], lang)
            ] = product['_id']

        await bot.send_message(chatid, t('products.search', lang))
        await ChoosePagesState(send_info_pr, userid, chatid, lang, rand_p, 1, 3, 
                               None, False, False)

@HDMessage
@main_router.message(Text('commands_name.market.random'), IsAuthorizedUser(), IsPrivateChat())
async def random_products(message: Message, state):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    products_all = await products.find({"owner_id": {"$ne": userid}}, 
                                       comment='random_products_products_all', max_col=62)
    rand_p = {}

    if products_all:
        for _ in range(18):
            if products_all:
                prd = choice(products_all)
                products_all.remove(prd)

                product = await products.find_one({'_id': prd['_id']}, comment='random_products_product')
                if product:
                    rand_p[
                        preview_product(product['items'], product['price'], 
                                        product['type'], lang)
                    ] = product['_id']
            else: break

        await bot.send_message(chatid, t('products.search', lang))
        await ChoosePagesState(send_info_pr, userid, chatid, lang, rand_p, 1, 3, 
                               None, False, False)
    else:
        await bot.send_message(chatid, t('products.null', lang))

@main_router.message(Text('commands_name.market.find'), IsAuthorizedUser(), IsPrivateChat())
@HDMessage
async def find_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await find_prepare(userid, chatid, lang)

@main_router.callback_query(F.data.startswith('create_push'), IsPrivateChat())
@HDCallback
async def push(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    channel_id = int(call_data[1])

    res = await puhs.find_one({'owner_id': userid}, comment='push_res')
    if res:
        await puhs.update_one({'owner_id': userid}, 
                        {"$set": {'channel_id': channel_id, 'lang': lang}},
                        comment='push_res2')
        text = t('push.update', lang)
    else: 
        await create_push(userid, channel_id, lang)
        text = t('push.new', lang)

    await bot.send_message(userid, text)
    await bot.edit_message_reply_markup(None, chatid, call.message.message_id, 
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    