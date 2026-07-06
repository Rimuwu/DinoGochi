
from bot.models.user import User
from bot.models.market import Product, Puhs, Seller
from random import choice

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.add_product.add_product import prepare_data_option
from bot.modules.data_format import (escape_markdown, list_to_inline,
                                     list_to_keyboard)
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.item import item_info
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.modules.market.market import (create_push, create_seller, delete_product,
                                preview_product, product_ui, seller_ui)
from bot.modules.market.market_chose import (buy_item, find_prepare,
                                      pr_edit_description, pr_edit_image,
                                      pr_edit_name, prepare_add,
                                      prepare_delete_all, prepare_edit_price,
                                      promotion_prepare, send_info_pr)
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChoosePagesStateHandler, ChooseOptionHandler, ChooseStepHandler, ChooseStringHandler
from bot.modules.states_fabric.steps_datatype import CustomStepData, StepMessage, StringStepData

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
from fuzzywuzzy import fuzz

from aiogram.fsm.context import FSMContext
import random




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
    elif await Seller.find_one(Seller.name == name):
        await bot.send_message(message.chat.id, 
                t('market_create.name_error', lang))
    else: 
        return True, name
    return False, None

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.create_market'), IsAuthorizedUser())
async def create_market(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    res = await Seller.find_one(Seller.owner.id == user.id) if user else None

    if res or not user:
        await bot.send_message(message.chat.id, t('menu_text.seller', lang), 
                            reply_markup= await m(userid, 'market_menu', lang))
    elif user.lvl < 2:
        await bot.send_message(message.chat.id, t('market_create.lvl', lang))
    else:

        steps = [
            CustomStepData('name', StepMessage(
                'market_create.name',
                markup=cancel_markup(lang), 
                translate_message=True),
                custom_handler=custom_name, 
            ),
            StringStepData('description', StepMessage(
                'market_create.description',
                markup=cancel_markup(lang), 
                translate_message=True),
                max_len=500, 
            )
        ]
        
        await ChooseStepHandler(
            create_adapter, userid, chatid, lang, steps
        ).start()

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.my_market'), IsAuthorizedUser())
async def my_market(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    res = await Seller.find_one(Seller.owner.id == user.id) if user else None
    if res:
        text, markup, image = await seller_ui(userid, lang, True)
        try:
            await bot.send_photo(chatid, image, caption=text, parse_mode="Markdown", reply_markup=markup)
        except:
            await bot.send_photo(chatid, image, caption=text, reply_markup=markup, parse_mode=None)

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.add_product'), IsAuthorizedUser())
async def add_product_com(message: Message):
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
    # await ChooseOptionState(prepare_data_option, userid, chatid, lang, options)
    await ChooseOptionHandler(
        prepare_data_option, userid, chatid, lang, options).start()

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.my_products'), IsAuthorizedUser())
async def my_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user_obj = await User.find_one(User.userid == userid)
    user_prd = await Product.find(Product.owner.id == user_obj.id).to_list() if user_obj else []
    rand_p = {}

    if user_prd:
        for product in user_prd:
            p_dict = product.dict()
            rand_p[
                preview_product(p_dict['items'], p_dict['price'], 
                                p_dict['type'], lang)
            ] = p_dict['_id']

        await bot.send_message(chatid, t('products.search', lang))

        await ChoosePagesStateHandler(
            send_info_pr, userid, chatid, lang, rand_p, 1, 3, None, False, False).start()
    else:
        text = t('no_products', lang)
        await bot.send_message(chatid, text,  parse_mode='Markdown')

@main_router.callback_query(F.data.startswith('product_info'))
async def product_info(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    call_type = call_data[1]
    alt_id = call_data[2]
    product = await Product.find_one(Product.alt_id == alt_id, fetch_links=True)
    if product:
        prd_dict = product.dict()
        if call_type == 'delete':
            if product.owner.userid == userid:

                await bot.edit_message_reply_markup(None, chatid, call.message.message_id, reply_markup=list_to_inline([]))

                status = await delete_product(None, alt_id)

                if status: text = t('product_info.delete', lang)
                else: text = t('product_info.error', lang)

                markup = list_to_inline([])
                await bot.edit_message_text(text, None, chatid, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        else:
            if call_type == 'edit_price' and product.owner.userid == userid:
                await prepare_edit_price(userid, chatid, lang, alt_id)

            elif call_type == 'add' and product.owner.userid == userid:
                await prepare_add(userid, chatid, lang, alt_id)

            elif call_type == 'items':
                itm = []
                for item in product.items:
                    if item not in itm:
                        itm.append(item)
                        text, image = await item_info(item, lang)

                        if image:
                            await send_SmartPhoto(chatid, image, text, 'Markdown')
                        else:
                            await bot.send_message(chatid, text, parse_mode='Markdown')

            elif call_type == 'buy' and product.owner.userid != userid:
                if product.owner.userid != userid:
                    await buy_item(userid, chatid, lang, prd_dict, 
                                   await User.get_user_name(userid), call.message.message_id)

            elif call_type == 'info':
                text, markup = await product_ui(lang, product.id, 
                                          product.owner.userid == userid)
                await bot.send_message(userid, text, reply_markup=markup, parse_mode='Markdown')
                
                if userid != call.message.chat.id:

                    await call.answer(
                        t('product_info.call_channel', lang),
                        show_alert=True
                    )

            elif call_type == 'promotion' and product.owner.userid == userid:
                await promotion_prepare(userid, chatid, lang, product.id, 
                                        call.message.message_id)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('seller'))
async def seller(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    call_type = call_data[1]
    owner_id = int(call_data[2])

    # Кнопки вызываемые владельцем
    if call_type == 'cancel_all':
        await prepare_delete_all(userid, chatid, lang, call.message.message_id)
    elif call_type == 'edit_text':
        await pr_edit_description(userid, chatid, lang, call.message.message_id)
    elif call_type == 'edit_name':
        await pr_edit_name(userid, chatid, lang, call.message.message_id)
    elif call_type == 'edit_image':
        user = await User.find_one(User.userid == userid)
        is_premium = await user.premium if user else False
        if is_premium:
            await pr_edit_image(userid, chatid, lang, call.message.message_id)
        else:
            await bot.send_message(chatid, t('no_premium', lang))

    # Кнопки вызываемые не владельцем
    elif call_type == 'info':
        my_status = owner_id == userid
        user_owner = await User.find_one(User.userid == owner_id)
        seller = await Seller.find_one(Seller.owner.id == user_owner.id) if user_owner else None

        if seller:
            text, markup, image = await seller_ui(owner_id, lang, my_status)
            try:
                await bot.send_photo(chatid, image, caption=text, parse_mode='Markdown', reply_markup=markup)
            except:
                await bot.send_photo(chatid, image, caption=text, reply_markup=markup)

    elif call_type == 'all':
        user_owner = await User.find_one(User.userid == owner_id)
        user_prd = await Product.find(Product.owner.id == user_owner.id).to_list() if user_owner else []

        rand_p = {}
        for product in user_prd:
            p_dict = product.dict()
            rand_p[
                preview_product(p_dict['items'], p_dict['price'], 
                                p_dict['type'], lang)
            ] = p_dict['_id']

        await bot.send_message(chatid, t('products.search', lang))
        # await ChoosePagesState(send_info_pr, userid, chatid, lang, rand_p, 1, 3, 
        #                        None, False, False)
        await ChoosePagesStateHandler(
            send_info_pr, userid, chatid, lang, rand_p, 1, 3, None, False, False).start()

@main_router.message(IsPrivateChat(), Text('commands_name.market.random'), IsAuthorizedUser())
async def random_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user_obj = await User.find_one(User.userid == userid)
    if user_obj:
        products_all = await Product.find(Product.owner.id != user_obj.id).to_list()
    else:
        products_all = await Product.find_all().to_list()
    rand_p = {}

    if products_all:
        for _ in range(18):
            if products_all:
                prd = choice(products_all)
                products_all.remove(prd)

                prd_dict = prd.dict()
                rand_p[
                    preview_product(prd_dict['items'], prd_dict['price'], 
                                    prd_dict['type'], lang)
                ] = prd_dict['_id']
            else: break

        await bot.send_message(chatid, t('products.search', lang))
        # await ChoosePagesState(send_info_pr, userid, chatid, lang, rand_p, 1, 3, 
        #                        None, False, False)
        await ChoosePagesStateHandler(
            send_info_pr, userid, chatid, lang, rand_p, 1, 3, None, False, False).start()
    else:
        await bot.send_message(chatid, t('products.null', lang))

@main_router.message(IsPrivateChat(), Text('commands_name.market.find'), IsAuthorizedUser())
async def find_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await find_prepare(userid, chatid, lang)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('create_push'))
async def push(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    channel_id = int(call_data[1])

    res = await Puhs.find_one(Puhs.owner_id == userid)
    if res:
        res.channel_id = channel_id
        res.lang = lang
        await res.save()
        text = t('push.update', lang)
    else: 
        await create_push(userid, channel_id, lang)
        text = t('push.new', lang)

    await bot.send_message(userid, text)
    await bot.edit_message_reply_markup(None, chatid, call.message.message_id, 
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))

@main_router.message(IsPrivateChat(), Text('commands_name.market.search_markets'), IsAuthorizedUser())
async def search_markets(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    mrk = list_to_inline([
        {
            t('search_markets.random', lang): 'random_markets',
            t('search_markets.find', lang): 'find_markets'
        }
    ])

    await bot.send_message(chatid, t('search_markets.text', lang),
                          reply_markup=mrk)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('random_markets'))
async def random_markets(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    lang = await get_lang(userid)

    # Получаем случайные магазины
    user_obj = await User.find_one(User.userid == userid)
    if user_obj:
        all_markets = await Seller.find(Seller.owner.id != user_obj.id, fetch_links=True).to_list()
    else:
        all_markets = await Seller.find(fetch_links=True).to_list()
    markets = random.sample(all_markets, min(15, len(all_markets))) if all_markets else []

    if not markets:
        await bot.edit_message_text(
            t('search_markets.no_markets', lang),
            chat_id=chatid,
            message_id=call.message.message_id
        )
        return

    # Формируем список магазинов для отображения
    market_list = {}
    for market in markets: 
        if market.owner:
            market_list[market.name] = market.owner.userid

    await ChoosePagesStateHandler(
            send_seller_info, userid, chatid, lang, market_list, 1, 3, None, False, False).start()

async def send_seller_info(option, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']

    text, markup, image = await seller_ui(option, lang, False)
    try:
        await bot.send_photo(chatid, image, caption=text, parse_mode="Markdown", reply_markup=markup)
    except:
        await bot.send_photo(chatid, image, caption=text, reply_markup=markup, parse_mode=None)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('find_markets'))
async def find_markets(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    lang = await get_lang(userid)
    
    await bot.send_message(
        chatid,
        t('search_markets.find_market', lang),
        reply_markup=cancel_markup(lang)
    )

    # await ChooseStringState(find_prepare_mk, userid, chatid, lang, 3, 50)
    await ChooseStringHandler(
        find_prepare_mk, userid, chatid, lang, 3, 50).start()

async def find_prepare_mk(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    name = return_data.lower()

    # Получаем все магазины кроме своего
    user_obj = await User.find_one(User.userid == userid)
    if user_obj:
        markets = await Seller.find(Seller.owner.id != user_obj.id, fetch_links=True).to_list()
    else:
        markets = await Seller.find(fetch_links=True).to_list()

    if not markets:
        await bot.send_message(chatid, t('search_markets.no_markets', lang))
        return

    # Ищем совпадения имен
    market_list = {}
    for market in markets:
        market_name = market.name.lower()

        # Считаем процент совпадения через fuzzywuzzy
        similarity = fuzz.ratio(name, market_name)

        # Если совпадение больше 60%
        if similarity >= 60:
            if market.owner:
                market_list[market.name] = market.owner.userid

    if market_list:
        await ChoosePagesStateHandler(
            send_seller_info, userid, chatid, lang, market_list, 1, 3, None, False, False).start()
    else:
        await bot.send_message(chatid, t('search_markets.no_markets', lang),
                               reply_markup=await m(userid, 'last_menu', lang))
