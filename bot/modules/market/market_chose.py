from aiogram.types import Message, InputMedia

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import (list_to_keyboard, escape_markdown, transform)
from bot.modules.dinosaur.skills import max_skill
from bot.modules.items.item import (CheckCountItemFromUser,
                              RemoveItemFromUser)
from bot.modules.localization import t
from bot.modules.market.market import buy_product, check_preferential, create_preferential, delete_product, generate_items_pages, preview_product, product_ui, seller_ui

from bot.modules.markup import cancel_markup, count_markup, confirm_markup
from bot.modules.states_tools import (ChooseImageState, ChooseIntState, ChooseStringState,
                                      ChooseStepState, ChooseConfirmState, ChoosePagesState)
from bot.modules.markup import markups_menu as m
from bot.modules.user.user import take_coins
from random import choice
 
from bot.const import GAME_SETTINGS

MAX_PRICE = 10_000_000

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
sellers = DBconstructor(mongo_client.market.sellers)
products = DBconstructor(mongo_client.market.products)


async def edit_price(new_price: int, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    productid = transmitted_data['productid']

    product = await products.find_one({'alt_id': productid}, comment='edit_price_product')
    if product:
        res, price = True, 1
        if product['type'] == 'coins_items':
            stock = product['in_stock']
            price = (product['price'] * stock) - (new_price * stock)
            res = await take_coins(userid, price, True)

        if res:
            await products.update_one({'alt_id': productid}, 
                                {'$set': {'price': new_price}}, comment='edit_price_pres')
            text = t('product_info.update_price', lang)
        else: text = t('product_info.not_coins', lang)
    else: text = t('product_info.error', lang)

    await bot.send_message(chatid, text, reply_markup= await m(userid, 'last_menu', lang), parse_mode='Markdown')

async def prepare_edit_price(userid: int, chatid: int, lang: str, productid: str):
    transmitted_data = {
        'productid': productid,
    }

    await bot.send_message(chatid, t('product_info.new_price', lang), 
                           reply_markup=cancel_markup(lang))
    await ChooseIntState(edit_price, userid, chatid, lang, 1, MAX_PRICE, transmitted_data=transmitted_data)

async def add_stock(in_stock: int, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    productid = transmitted_data['productid']

    product = await products.find_one({'alt_id': productid}, comment='add_stock_product')
    text = '-'

    if product:
        if product['type'] in ['items_coins', 'items_items']:
            # Проверить предметы
            items = list(product['items'])
            items_status, n = [], 0

            for item in items:
                item_id = item['item_id']
                count = item['count']
                if 'abilities' in item: abil = item['abilities']
                else: abil = {}

                status = await CheckCountItemFromUser(userid, in_stock * count, item_id, abil)
                items_status.append(status)
                n += 1

            if not all(items_status):
                text = t('product_info.no_items', lang)
            else:
                n = 0
                for item in items:
                    item_id = item['item_id']
                    count = item['count']
                    if 'abilities' in item: abil = item['abilities']
                    else: abil = {}

                    await RemoveItemFromUser(userid, item_id, in_stock * count, abil)
                    n += 1

                text = t('product_info.stock', lang)
                await products.update_one({'alt_id': productid}, 
                                    {'$inc': {'in_stock': in_stock}}, comment='add_stock_1')

        elif product['type'] == 'coins_items':
            res = await take_coins(userid, -product['price'] * in_stock, True)
            if res:
                await products.update_one({'alt_id': productid}, 
                                    {'$inc': {'in_stock': in_stock}}, comment='add_stock_2')
                text = t('product_info.stock', lang)
            else:
                text = t('product_info.not_coins', lang)
    else:
        text = t('product_info.error', lang)

    await bot.send_message(chatid, text, reply_markup= await m(userid, 'last_menu', lang), parse_mode='Markdown')

async def prepare_add(userid: int, chatid: int, lang: str, productid: str):

    transmitted_data = {
        'productid': productid,
    }

    await bot.send_message(chatid, t('product_info.add_stock', lang), 
                           reply_markup=cancel_markup(lang))
    await ChooseIntState(add_stock, userid, chatid, lang, 1, MAX_PRICE, transmitted_data=transmitted_data)

async def delete_all(_: bool, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    message_id = transmitted_data['message_id']

    products_del = await products.find(
        {'owner_id': userid}, comment='delete_all')
    if products_del:
        for i in products_del:
            await delete_product(i['_id'])

    await bot.send_message(chatid, t('seller.delete_all', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))

    text, markup, image = await seller_ui(userid, lang, True)
    await bot.edit_message_caption(None, caption=text, chat_id=chatid, message_id=message_id, parse_mode='Markdown', reply_markup=markup)

async def prepare_delete_all(userid: int, chatid: int, lang: str, message_id: int):
    transmitted_data = {
        'message_id': message_id,
    }

    await bot.send_message(chatid, t('seller.confirm_delete_all', lang), 
                           reply_markup=confirm_markup(lang))
    await ChooseConfirmState(delete_all, userid, chatid, lang, True, transmitted_data=transmitted_data)

async def edit_name(name: str, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    message_id = transmitted_data['message_id']
    name = escape_markdown(name)

    if not await sellers.find_one({'name': name}, comment='edit_name_check'):
        await sellers.update_one({'owner_id': userid}, 
                            {'$set': {'name': name}}, comment='edit_name')
        await bot.send_message(chatid, t('seller.new_name', lang), 
                            reply_markup= await m(userid, 'last_menu', lang))

        text, markup, image = await seller_ui(userid, lang, True)
        try:
            await bot.edit_message_caption(None, caption=text, chat_id=chatid, message_id=message_id, parse_mode='Markdown', reply_markup=markup)
        except: pass
    else:
        text =  t('market_create.name_error', lang)
        await bot.send_message(chatid, t('seller.confirm_delete_all', lang), 
                               reply_markup= await m(userid, 'last_menu', lang))

async def pr_edit_name(userid: int, chatid: int, lang: str, message_id: int):
    transmitted_data = {
        'message_id': message_id
    }

    await bot.send_message(chatid, t('seller.edit_name', lang), 
                           reply_markup=cancel_markup(lang))
    await ChooseStringState(edit_name, userid, chatid, lang, min_len=3, max_len=50, transmitted_data=transmitted_data)

async def edit_description(description: str, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    message_id = transmitted_data['message_id']

    description = escape_markdown(description)
    await sellers.update_one({'owner_id': userid}, 
                        {'$set': {'description': description}}, comment='edit_description_1')
    await bot.send_message(chatid, t('seller.new_description', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))

    text, markup, image = await seller_ui(userid, lang, True)
    try:
        await bot.edit_message_caption(None, caption=text, chat_id=chatid, message_id=message_id, parse_mode='Markdown', reply_markup=markup)
    except: pass

async def pr_edit_description(userid: int, chatid: int, lang: str, message_id: int, state):
    transmitted_data = {
        'message_id': message_id
    }

    await bot.send_message(chatid, t('seller.edit_description', lang), 
                           reply_markup=cancel_markup(lang))
    await ChooseStringState(edit_description, state, userid, chatid, lang, max_len=500, transmitted_data=transmitted_data)

async def edit_image(new_image: str, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    message_id = transmitted_data['message_id']
    if new_image == 'no_image': 
        new_image = ''
    else:
        file_info = await bot.get_file(new_image)
        downloaded_file = await bot.download_file(file_info.file_path)
        if downloaded_file:
            new_image = new_image
        else:
            new_image = ''

    await sellers.update_one({'owner_id': userid}, 
                        {'$set': {'custom_image': new_image}}, comment='edit_image_1')

    if new_image: text = t('seller.new_image', lang)
    else: text = t('seller.delete_image', lang)

    await bot.send_message(chatid, text, 
                           reply_markup= await m(userid, 'last_menu', lang))

    text, markup, image = await seller_ui(userid, lang, True)
    try:
        await bot.edit_message_media(chat_id=chatid, message_id=message_id, reply_markup=markup,
                    media=InputMedia(
                        type='photo', media=image, 
                        caption=text, parse_mode='Markdown'))
    except: pass

async def pr_edit_image(userid: int, chatid: int, lang: str, message_id: int):
    transmitted_data = {
        'message_id': message_id
    }

    await bot.send_message(chatid, t('seller.edit_image', lang), 
                           reply_markup=cancel_markup(lang))
    await ChooseImageState(edit_image, userid, chatid, lang, True, transmitted_data=transmitted_data)


async def end_buy(unit: int, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    pid = transmitted_data['id']
    name = transmitted_data['name']
    messageid = transmitted_data['messageid']

    status, code = await buy_product(pid, unit, userid, name, lang)
    await bot.send_message(chatid, t(f'buy.{code}', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))

    if status:
        text, markup = await product_ui(lang, pid, False)
        try:
            await bot.edit_message_text(text, None, chatid, messageid, reply_markup=markup, parse_mode='Markdown')
        except:
            await bot.delete_message(chatid, messageid)

async def buy_item(userid: int, chatid: int, lang: str, product: dict, name: str, 
                   messageid: int):
    """ Покупка предмета
    """
    user = await users.find_one({'userid': userid}, comment='buy_item_user')
    if user:
        transmitted_data = {
            'id': product['_id'],
            'name': name,
            'messageid': messageid
        }

        # Указать ставку
        if product['type'] == 'auction':
            min_int = product['price'] + product['min_add']
            max_int = user['coins']
            text = t('buy.auction', lang, unit=min_int)

        # Указать количество покупок
        else:
            min_int = 1
            max_int = product['in_stock'] - product['bought']
            text = t('buy.common_buy', lang)

        if max_int > min_int or max_int == min_int:
            status, _ = await ChooseIntState(end_buy, userid, chatid, lang, min_int=min_int, max_int=max_int, transmitted_data=transmitted_data, autoanswer=False)
            if status:
                if product['type'] != 'auction':
                    await bot.send_message(chatid, text, 
                                    reply_markup=count_markup(max_int, lang))
                else:
                    await bot.send_message(chatid, text, 
                                    reply_markup=cancel_markup(lang))
        else:
            await bot.send_message(chatid, t('buy.max_min', lang), 
                                reply_markup=cancel_markup(lang))

async def promotion(_: bool, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    pid = transmitted_data['id']
    message_id = transmitted_data['message_id']
    price = transmitted_data['price']

    st, cd = await check_preferential(userid, pid)
    stat = True

    if cd == 1: text = t('promotion.max', lang)
    elif cd == 2: text = t('promotion.already', lang)
    elif not await take_coins(userid, -price, True):
        text = t('promotion.no_coins', lang)
        stat = False
    else: 
        text = t('promotion.ok', lang)
        await create_preferential(pid, 43_200, userid)

    await bot.send_message(chatid, text, 
                    reply_markup= await m(userid, 'last_menu', lang))
    if stat:
        m_text, markup = await product_ui(lang, pid, True)
        await bot.edit_message_reply_markup(None, chatid, message_id, 
                                            reply_markup=markup)

async def promotion_prepare(userid: int, chatid: int, lang: str, product_id, message_id: int):
    """ Включение promotion
    """
    user = await users.find_one({'userid': userid}, comment='promotion_prepare_user')
    if user:
        coins = GAME_SETTINGS['promotion_price']
        max_charisma = await max_skill(userid, 'charisma')
        discount = transform(max_charisma, 20, 60)

        if discount >= 1:
            coins -= (coins // 100) * discount
            text_price = t('promotion.price_discount', 
                           coins=coins, discount=discount, lang=lang)
        else:
            text_price = t('promotion.price', coins=coins)

        transmitted_data = {
            'id': product_id,
            'message_id': message_id,
            'price': coins
        }

        await bot.send_message(chatid, t('promotion.buy', lang) + text_price, 
                                reply_markup=confirm_markup(lang))
        await ChooseConfirmState(promotion, userid, chatid, lang, True, transmitted_data)

async def send_info_pr(option, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']

    product = await products.find_one({'_id': option}, {'owner_id': 1}, comment='send_info_pr')
    if product:
        my = product['owner_id'] == userid
        m_text, markup = await product_ui(lang, option, my)
        try:
            await bot.send_message(chatid, m_text, reply_markup=markup, parse_mode='Markdown')
        except:
            await bot.send_message(userid, m_text, reply_markup=markup)
    else:
        await bot.send_message(chatid,  t('product_info.error', lang))

async def find_prepare(userid: int, chatid: int, lang: str):

    options = {
        "🍕 ➡ 🪙": 'items_coins',
        "🪙 ➡ 🍕": 'coins_items',
        "🍕 ➡ 🍕": 'items_items',
        "🍕 ➡ ⏳": 'auction',
        "❌": None
    }

    markup = list_to_keyboard([list(options.keys()), t('buttons_name.cancel', lang)], 2)
    items, exc = generate_items_pages()
    steps = [
        {
            "type": 'inv', "name": 'item', "data": {'inventory': items}, 
            "translate_message": True,
            'message': {'text': f'find_product.choose'}
        },
        {
            "type": 'option', "name": 'option', 
            "data": {"options": options}, 
            "translate_message": True,
            'message': {'text': 'find_product.info', 'reply_markup': markup}
        }
    ]
    
    await ChooseStepState(find_end, userid, chatid, lang, steps)

async def find_end(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']

    item = return_data['item']
    filt = return_data['option']


    if filt:
        products_all = await products.find(
            {"type": filt, "items_id": {'$in': [item['item_id']]}
                        }, comment='find_end_1')
    else:
        products_all = await products.find(
            {"items_id": {'$in': [item['item_id']]}
                        }, comment='find_end_2')

    if products_all:
        prd = {}
        for _ in range(18):
            if products_all:
                rand_pro = choice(products_all)
                products_all.remove(rand_pro)

                product = await products.find_one({'_id': rand_pro['_id']}, comment='find_end_product')
                if product:
                    prd[
                        preview_product(product['items'], product['price'], 
                                        product['type'], lang)
                    ] = product['_id']
            else: break

        await bot.send_message(chatid, t('products.search', lang))
        await ChoosePagesState(send_info_pr, userid, chatid, lang, prd, 1, 3, 
                               None, False, False)
    else:
        await bot.send_message(chatid, t('find_product.not_found', lang), 
                               reply_markup= await m(userid, 'last_menu', lang))

async def complain_market(userid: int, chatid: int, lang: str):

    ...