from telebot.types import Message, InputMedia

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.data_format import (list_to_inline, list_to_keyboard,
                                     seconds_to_str, user_name, escape_markdown)
from bot.modules.item import (AddItemToUser, CheckCountItemFromUser,
                              RemoveItemFromUser, counts_items, get_name)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.market import (add_product, preview_product,
                                generate_items_pages, generate_sell_pages,
                                product_ui, seller_ui, delete_product, buy_product, create_preferential, check_preferential)
from bot.modules.markup import answer_markup, cancel_markup, count_markup, confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_tools import (ChooseIntState, ChooseStringState,
                                      ChooseStepState, prepare_steps, ChooseConfirmState, ChoosePagesState)
from bot.modules.markup import markups_menu as m
from bot.modules.user import take_coins
from random import choice

MAX_PRICE = 10_000_000

users = mongo_client.user.users
management = mongo_client.other.management
tavern = mongo_client.tavern.tavern
sellers = mongo_client.market.sellers
items = mongo_client.items.items
products = mongo_client.market.products

""" Последняя функция, создаёт продукт и проверяте монеты / предметы
"""
async def end(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    option = transmitted_data['option']
    price = return_data['price']
    items = transmitted_data['items']
    col = transmitted_data['col']

    product_status, add_arg = True, {}
    text = t('add_product.all_good', lang)

    if 'in_stock' in return_data:
        in_stock = return_data['in_stock']
    else: in_stock = transmitted_data['in_stock']

    add_items, a = [], 0
    for item in transmitted_data['items']:
        add_items += [item] * transmitted_data['col'][a]
        a += 1

    if option == 'coins_items':  
        # Проверить количество монет 
        res = take_coins(userid, -price*in_stock, True)
        if not res:
            product_status = False
            text = t('add_product.few_coins', lang, coins=price*in_stock)

    elif option in ['items_coins', 'items_items', 'auction']:  
        # Проверить предметы
        items_status, n = [], 0
        for item in items:
            item_id = item['item_id']
            if 'abillities' in item: abil = item['abillities']
            else: abil = {}

            status = CheckCountItemFromUser(userid, col[n] * in_stock, item_id, abil)

            items_status.append(status)
            n += 1

        if not all(items_status):
            product_status = False
            text = t('add_product.no_items', lang)
        else:
            n = 0
            for item in items:
                item_id = item['item_id']
                if 'abillities' in item: abil = item['abillities']
                else: abil = {}

                RemoveItemFromUser(userid, item_id, col[n] * in_stock, abil)
                n += 1

    if option == 'auction':
        add_arg['min_add'] = return_data['min_add']
        add_arg['end'] = return_data['time_end']

    if product_status:
        pr_id = await add_product(userid, option, add_items, 
                                  price, in_stock, add_arg)
        m_text, markup = product_ui(lang, pr_id, True)

        try:
            await bot.send_message(chatid, m_text, reply_markup=markup,
                                   parse_mode='Markdown')
        except Exception as e:
            print(e)
            await bot.send_message(chatid, m_text, reply_markup=markup)

    await bot.send_message(chatid, text, reply_markup=m(userid, 'last_menu', lang), parse_mode='Markdown')

""" Функция для получения цены и запаса для типов coins_items / items_coins
"""
async def coins_stock(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    option = transmitted_data['option']

    if type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    steps = [
        {
            "type": 'int', "name": 'price', "data": {"max_int": MAX_PRICE},
            "translate_message": True,
            'message': {'text': f'add_product.coins.{option}', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'int', "name": 'in_stock', "data": {"max_int": 100},
            "translate_message": True,
            'message': {'text': f'add_product.stock.{option}', 
                        'reply_markup': cancel_markup(lang)}
        }
    ]

    transmitted_data = {
        'items': return_data['items'],
        'col': return_data['col'],
        'option': transmitted_data['option']
    }

    await ChooseStepState(end, userid, chatid, 
                              lang, steps, 
                              transmitted_data=transmitted_data)

""" Функция для получения нач. цены, запаса, времени для типа auction
"""
async def auction(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    if type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    steps = [
        {
            "type": 'int', "name": 'price', "data": {"max_int": MAX_PRICE},
            "translate_message": True,
            'message': {'text': 'add_product.coins.auction', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'int', "name": 'min_add', "data": {"max_int": 1_000_000},
            "translate_message": True,
            'message': {'text': 'add_product.min_add', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'time', "name": 'time_end', "data": {"max_int": 2_592_000},
            "translate_message": True,
            'message': {'text': 'add_product.time_end', 
                        'reply_markup': cancel_markup(lang)}
        }
    ]

    transmitted_data = {
        'items': return_data['items'],
        'col': return_data['col'],
        'option': transmitted_data['option'],
        'in_stock': transmitted_data['in_stock']
    }

    await ChooseStepState(end, userid, chatid, 
                          lang, steps, 
                          transmitted_data=transmitted_data)

""" Запращивает запас у пользователя (конец)
"""
async def stock_adapter(in_stock:int, transmitted_data):
    price, a = [], 0
    for item in transmitted_data['trade_items']:
        price += [item] * transmitted_data['col_trade'][a]
        a += 1

    del transmitted_data['trade_items']
    del transmitted_data['col_trade']
    
    return_data = {
        'price': price,
        'in_stock': in_stock
    }
    await end(return_data, transmitted_data)

""" Запращивает запас у пользователя для items_items
"""
async def stock(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    option = transmitted_data['option']

    if type(return_data['trade_items']) != list:
        return_data['trade_items'] = [return_data['trade_items']]
        return_data['col_trade'] = [return_data['col_trade']]

    for key, item in return_data.items(): transmitted_data[key] = item

    await ChooseIntState(stock_adapter, userid, chatid, lang, 1, 20, transmitted_data=transmitted_data)
    await bot.send_message(chatid, t(f'add_product.stock.{option}', lang), reply_markup=cancel_markup(lang), parse_mode='Markdown')

""" Функция для получения предметов на обмен (items_items)
"""
async def items_items(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    if type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    for key, item in return_data.items(): transmitted_data[key] = item

    inv_items, exclude = generate_items_pages()
    steps = trade_circle(userid, chatid, lang, inv_items, False)
    transmitted_data['exclude'] = exclude

    await ChooseStepState(stock, userid, chatid, 
                          lang, steps, 
                          transmitted_data=transmitted_data)

""" Функция создаёт проверку на дополнительные предметы, если предметов меньше чем 3
"""
def check_items(transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    res = True
    if type(transmitted_data['return_data']['items']) == list and len(transmitted_data['return_data']['items']) >= 3: res = False

    if res:
        not_p_steps = [
            {
                "type": 'bool', "name": 'add_item', "data": {},
                "translate_message": True,
                'message': {'text': 'add_product.add_item',
                             'reply_markup': answer_markup(lang)}
            },
            {
                "type": 'update_data', "name": None, "data": {}, 
                'function': new_circle
            }
        ]
        steps = prepare_steps(not_p_steps, userid, chatid, lang)
        transmitted_data['steps'] += steps

    return transmitted_data, True

""" Функция создаёт проверку на дополнительные предметы, если предметов меньше чем 3
    Для типа itme_items
"""
def check_items_for_items(transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    res = True
    if type(transmitted_data['return_data']['trade_items']) == list and len(transmitted_data['return_data']['trade_items']) >= 3: res = False

    if res:
        not_p_steps = [
            {
                "type": 'bool', "name": 'add_item', "data": {},
                "translate_message": True,
                'message': {'text': 'add_product.add_item',
                             'reply_markup': answer_markup(lang)}
            },
            {
                "type": 'update_data', "name": None, "data": {'trade': True}, 
                'function': new_circle
            }
        ]
        steps = prepare_steps(not_p_steps, userid, chatid, lang)
        transmitted_data['steps'] += steps

    return transmitted_data, True

""" Функция выставляет максимальное количетсво предмета для типа coins_items
"""
def update_col(transmitted_data):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['items']) == list:
        item_data = transmitted_data['return_data']['items'][-1]
    else:
        item_data = transmitted_data['return_data']['items']

    items_res = items.find({'items_data': item_data, "owner_id": userid})
    if items_res:
        max_count = 0
        for i in items_res: max_count += i['count']

        # Добавление данных для выбора количества
        transmitted_data['steps'][step+1]['data']['max_int'] = max_count
        transmitted_data['steps'][step+1]['message']['reply_markup'] = count_markup(max_count, lang)
        transmitted_data['exclude'].append(item_data['item_id'])

        # Очистка лишних данных
        transmitted_data['steps'][step-1] = {}

        return transmitted_data, True
    else: return transmitted_data, False

""" Функция выставляет максимальное количетсво предмета для типа items_coins
    а так же очищает некоторые данные
""" 
def order_update_col(transmitted_data):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['items']) == list:
        item_data = transmitted_data['return_data']['items'][-1]
    else:
        item_data = transmitted_data['return_data']['items']

    items_res = items.find({'items_data': item_data, "owner_id": userid})
    if items_res:
        max_count = 20

        # Добавление данных для выбора количества
        transmitted_data['steps'][step+1]['data']['max_int'] = max_count
        transmitted_data['steps'][step+1]['message']['reply_markup'] = count_markup(max_count, lang)
        transmitted_data['exclude'].append(item_data['item_id'])

        # Очистка лишних данных
        transmitted_data['steps'][step-1] = {}

        return transmitted_data, True
    else: return transmitted_data, False

""" Функция выставляет максимальное количетсво предмета для типа items_items.2
    а так же очищает некоторые данные
""" 
def trade_update_col(transmitted_data):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['trade_items']) == list:
        item_data = transmitted_data['return_data']['trade_items'][-1]
    else:
        item_data = transmitted_data['return_data']['trade_items']

    items_res = items.find({'items_data': item_data, "owner_id": userid})
    if items_res:
        max_count = 20

        # Добавление данных для выбора количества
        transmitted_data['steps'][step+1]['data']['max_int'] = max_count
        transmitted_data['steps'][step+1]['message']['reply_markup'] = count_markup(max_count, lang)
        transmitted_data['exclude'].append(item_data['item_id'])

        # Очистка лишних данных
        transmitted_data['steps'][step-1] = {}

        return transmitted_data, True
    else: return transmitted_data, False

""" Создаёт данные для круга получения данных для типа coins_items
"""
def circle_data(userid, chatid, lang, items, option, prepare: bool = True):
    update_function = update_col

    if option == 'coins_items': 
        update_function = order_update_col

    not_p_steps = [
        {
            "type": 'inv', "name": 'items', "data": {'inventory': items}, 
            "translate_message": True,
            'message': {'text': f'add_product.chose_item.{option}'}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': update_function
        },
        {
            "type": 'int', "name": 'col', "data": {"max_int": 10},
            "translate_message": True,
            'message': {'text': 'add_product.wait_count', 
                        'reply_markup': None}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': check_items
        }
    ]
    if prepare:
        steps = prepare_steps(not_p_steps, userid, chatid, lang)
        return steps
    else: return not_p_steps

""" Создаёт данные для круга получения данных для типа items_items
"""
def trade_circle(userid, chatid, lang, items, prepare: bool = True):

    not_p_steps = [
        {
            "type": 'inv', "name": 'trade_items', "data": {'inventory': items,
                                                    # 'changing_filters': False
                                                    }, 
            "translate_message": True,
            'message': {'text': f'add_product.trade_items'}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': trade_update_col
        },
        {
            "type": 'int', "name": 'col_trade', "data": {"max_int": 10},
            "translate_message": True,
            'message': {'text': 'css.wait_count', 
                        'reply_markup': None}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': check_items_for_items
        }
    ]
    if prepare:
        steps = prepare_steps(not_p_steps, userid, chatid, lang)
        return steps
    else: return not_p_steps

""" Функция создаёт ещё 1 круг добавления предмета для типа coins_items, items_items (trade True)
"""
def new_circle(transmitted_data, trade: bool = False):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    add_res = transmitted_data['return_data']['add_item']
    exclude_ids = transmitted_data['exclude']
    option = transmitted_data['option']

    if add_res:
        if trade:
            items, exclude = generate_items_pages(exclude_ids)
            steps = trade_circle(userid, chatid, lang, items)
        else:
            items, exclude = generate_sell_pages(userid, exclude_ids)
            steps = circle_data(userid, chatid, lang, items, option)

        transmitted_data['exclude'] = exclude

        transmitted_data['steps'].clear()
        transmitted_data['steps'] = steps
        del transmitted_data['return_data']['add_item']

        transmitted_data['process'] = -1

        return transmitted_data, True
    return transmitted_data, False

""" Старт всех проверок
"""
async def prepare_data_option(option, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    ret_function = coins_stock
    items, exclude = generate_sell_pages(userid)
    transmitted_data = {
        'exclude': exclude, 'option': option
    }

    if option == 'items_coins': pass
    elif option == 'coins_items':
        items, exclude = generate_items_pages()

    elif option == 'items_items':
        ret_function = items_items

    else: # auction
        ret_function = auction
        transmitted_data['in_stock'] = 1

    steps = circle_data(userid, chatid, lang, items, option, False)
    await ChooseStepState(ret_function, userid, chatid, 
                          lang, steps, 
                          transmitted_data=transmitted_data)


async def edit_price(new_price: int, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    productid = transmitted_data['productid']

    product = products.find_one({'alt_id': productid})
    if product:
        res, price = True, 1
        if product['type'] == 'coins_items':
            stock = product['in_stock']
            price = (product['price'] * stock) - (new_price * stock)
            res = take_coins(userid, price, True)

        if res:
            products.update_one({'alt_id': productid}, 
                                {'$set': {'price': new_price}})
            text = t('product_info.update_price', lang)
        else:
            text = t('product_info.not_coins', lang)
    else:
        text = t('product_info.error', lang)

    await bot.send_message(chatid, text, reply_markup=m(userid, 'last_menu', lang), parse_mode='Markdown')

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

    product = products.find_one({'alt_id': productid})
    text = '-'

    if product:
        if product['type'] in ['items_coins', 'items_items']:
            # Проверить предметы
            items = product['items']
            items_status, n = [], 0

            for item in items:
                item_id = item['item_id']
                if 'abillities' in item: abil = item['abillities']
                else: abil = {}

                status = CheckCountItemFromUser(userid, in_stock, item_id, abil)
                items_status.append(status)
                n += 1

            if not all(items_status):
                text = t('product_info.no_items', lang)
            else:
                n = 0
                for item in items:
                    item_id = item['item_id']
                    if 'abillities' in item: abil = item['abillities']
                    else: abil = {}

                    RemoveItemFromUser(userid, item_id, in_stock, abil)
                    n += 1

                text = t('product_info.stock', lang)
                products.update_one({'alt_id': productid}, 
                                    {'$inc': {'in_stock': in_stock}})

        elif product['type'] == 'coins_items':
            res = take_coins(userid, product['price'] * in_stock, True)
            if res:
                products.update_one({'alt_id': productid}, 
                                    {'$inc': {'in_stock': in_stock}})
                text = t('product_info.stock', lang)
            else:
                text = t('product_info.not_coins', lang)
    else:
        text = t('product_info.error', lang)

    await bot.send_message(chatid, text, reply_markup=m(userid, 'last_menu', lang), parse_mode='Markdown')

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

    products_del = list(products.find({'owner_id': userid}))
    if products_del:
        for i in products_del:
            await delete_product(i['_id'])

    await bot.send_message(chatid, t('seller.delete_all', lang), 
                           reply_markup=m(userid, 'last_menu', lang))

    text, markup, image = seller_ui(userid, lang, True)
    await bot.edit_message_caption(text, chatid, message_id, parse_mode='Markdown', reply_markup=markup)

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

    if not sellers.find_one({'name': name}):
        sellers.update_one({'owner_id': userid}, 
                            {'$set': {'name': name}})
        await bot.send_message(chatid, t('seller.new_name', lang), 
                            reply_markup=m(userid, 'last_menu', lang))

        text, markup, image = seller_ui(userid, lang, True)
        try:
            await bot.edit_message_caption(text, chatid, message_id, parse_mode='Markdown', reply_markup=markup)
        except: pass
    else:
        text =  t('market_create.name_error', lang)
        await bot.send_message(chatid, t('seller.confirm_delete_all', lang), 
                               reply_markup=m(userid, 'last_menu', lang))

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
    sellers.update_one({'owner_id': userid}, 
                        {'$set': {'description': description}})
    await bot.send_message(chatid, t('seller.new_description', lang), 
                           reply_markup=m(userid, 'last_menu', lang))

    text, markup, image = seller_ui(userid, lang, True)
    try:
        await bot.edit_message_caption(text, chatid, message_id, parse_mode='Markdown', reply_markup=markup)
    except: pass

async def pr_edit_description(userid: int, chatid: int, lang: str, message_id: int):
    transmitted_data = {
        'message_id': message_id
    }

    await bot.send_message(chatid, t('seller.edit_description', lang), 
                           reply_markup=cancel_markup(lang))
    await ChooseStringState(edit_description, userid, chatid, lang, max_len=500, transmitted_data=transmitted_data)

async def edit_image(new_image: str, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    message_id = transmitted_data['message_id']
    if new_image == '-': new_image = ''

    sellers.update_one({'owner_id': userid}, 
                        {'$set': {'custom_image': new_image}})

    if new_image: text = t('seller.new_image', lang)
    else: text = t('seller.delete_image', lang)

    await bot.send_message(chatid, text, 
                           reply_markup=m(userid, 'last_menu', lang))

    text, markup, image = seller_ui(userid, lang, True)
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
    await ChooseStringState(edit_image, userid, chatid, lang, max_len=200, transmitted_data=transmitted_data)


async def end_buy(unit: int, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    pid = transmitted_data['id']
    name = transmitted_data['name']
    messageid = transmitted_data['messageid']

    status, code = await buy_product(pid, unit, userid, name, lang)
    await bot.send_message(chatid, t(f'buy.{code}', lang), 
                           reply_markup=m(userid, 'last_menu', lang))

    if status:
        text, markup = product_ui(lang, pid, False)
        await bot.edit_message_text(text, chatid, messageid, reply_markup=markup, parse_mode='Markdown')

async def buy_item(userid: int, chatid: int, lang: str, product: dict, name: str, 
                   messageid: int):
    """ Покупка предмета
    """
    user = users.find_one({'userid': userid})
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

    st, cd = check_preferential(userid, pid)
    stat = True

    if cd == 1: text = t('promotion.max', lang)
    elif cd == 2: text = t('promotion.already', lang)
    elif not take_coins(userid, -1_890, True):
        text = t('promotion.no_coins', lang)
        stat = False
    else: 
        text = t('promotion.ok', lang)
        create_preferential(pid, 43_200, userid)

    await bot.send_message(chatid, text, 
                    reply_markup=m(userid, 'last_menu', lang))
    if stat:
        m_text, markup = product_ui(lang, pid, True)
        await bot.edit_message_reply_markup(chatid, message_id, 
                                            reply_markup=markup)

async def promotion_prepare(userid: int, chatid: int, lang: str, product_id, message_id: int):
    """ Включение promotion
    """
    user = users.find_one({'userid': userid})
    if user:
        transmitted_data = {
            'id': product_id,
            'message_id': message_id
        }

        await bot.send_message(chatid, t('promotion.buy', lang), 
                                reply_markup=confirm_markup(lang))
        await ChooseConfirmState(promotion, userid, chatid, lang, True, transmitted_data)

async def send_info_pr(option, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']

    product = products.find_one({'_id': option}, {'owner_id': 1})
    if product:
        my = product['owner_id'] == userid
        m_text, markup = product_ui(lang, option, my)
        await bot.send_message(chatid, m_text, reply_markup=markup, parse_mode='Markdown')
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
        products_all = list(products.find(
            {"type": filt, "items_id": {'$in': [item['item_id']]}
                        })).copy()
    else:
        products_all = list(products.find(
            {"items_id": {'$in': [item['item_id']]}
                        })).copy()

    if products_all:
        prd = {}
        for _ in range(18):
            if products_all:
                rand_pro = choice(products_all)
                products_all.remove(rand_pro)

                product = products.find_one({'_id': rand_pro['_id']})
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
                               reply_markup=m(userid, 'last_menu', lang))

async def complain_market(userid: int, chatid: int, lang: str):

    ...