from bot.config import mongo_client
from bot.modules.localization import t

from bot.exec import bot

from bot.modules.markup import answer_markup, cancel_markup, count_markup
 
from bot.modules.states_tools import (ChooseIntState, ChooseStepState, prepare_steps)

from bot.modules.market import generate_items_pages, generate_sell_pages
from bot.modules.add_product.general import end

MAX_PRICE = 10_000_000

from bot.modules.overwriting.DataCalsses import DBconstructor
items = DBconstructor(mongo_client.items.items)


def trade_circle(userid, chatid, lang, items, option, prepare: bool = True):
    """ Создаёт данные для круга получения данных предметов ПОЛЬЗОВАТЕЛЯ
    """
    not_p_steps = [
        {
            "type": 'inv', "name": 'items', "data": {'inventory': items}, 
            "translate_message": True,
            'message': {'text': f'add_product.chose_item.{option}'}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': trade_update_col
        },
        {
            "type": 'int', "name": 'col', "data": {"max_int": 20},
            "translate_message": True,
            'message': {'text': 'add_product.wait_count', 
                        'reply_markup': count_markup(20, lang)}
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

async def trade_update_col(transmitted_data):
    """ Функция выставляет максимальное количетсво предмета, а так же очищает некоторые данные
    """ 
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['items']) == list:
        item_data = transmitted_data['return_data']['items'][-1]
    else:
        item_data = transmitted_data['return_data']['items']

    items_res = await items.find({'items_data': item_data, 
                                  "owner_id": userid}, comment='trade_update_col_items_res')
    if items_res:
        max_count = 0
        for i in items_res: max_count += i['count']
        if max_count > 20: max_count = 20

        # Добавление данных для выбора количества
        transmitted_data['steps'][step+1]['data']['max_int'] = max_count
        transmitted_data['steps'][step+1]['message']['reply_markup'] = count_markup(max_count, lang)
        transmitted_data['exclude'].append(item_data['item_id'])

        # Очистка лишних данных
        transmitted_data['steps'][step-1] = {}

        return transmitted_data, True
    else: return transmitted_data, False

def check_items_for_items(transmitted_data):
    """ Функция создаёт проверку на дополнительные предметы, 
    если предметов меньше чем 3
    """

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

async def new_circle(transmitted_data):
    """ Функция создаёт круг запроса (активируется когда человек хочет добавить 2-ой и 3-ий товар в продукт)
    """
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    add_res = transmitted_data['return_data']['add_item']
    exclude_ids = transmitted_data['exclude']
    option = transmitted_data['option']

    if add_res:
        items, exclude = await generate_sell_pages(userid, exclude_ids)
        steps = trade_circle(userid, chatid, lang, items, option)

        transmitted_data['exclude'] = exclude

        transmitted_data['steps'].clear()
        transmitted_data['steps'] = steps
        del transmitted_data['return_data']['add_item']

        transmitted_data['process'] = -1

        return transmitted_data, True
    return transmitted_data, False

async def items_items(return_data, transmitted_data):
    """ Функция для получения предметов на обмен
    """
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    if type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    for key, item in return_data.items(): transmitted_data[key] = item

    inv_items, exclude = generate_items_pages()
    steps = received_circle(userid, chatid, lang, inv_items, "trade_items", False)
    transmitted_data['exclude'] = exclude

    await ChooseStepState(stock, userid, chatid, 
                          lang, steps, 
                          transmitted_data=transmitted_data)

def received_circle(userid, chatid, lang, items, option, prepare: bool = True):
    """ Создаёт данные для круга получения данных ЗАПРАШИВАЕМЫХ предметов
    """
    not_p_steps = [
        {
            "type": 'inv', "name": 'trade_items', "data": {'inventory': items}, 
            "translate_message": True,
            'message': {'text': f'add_product.chose_item.{option}'}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': received_upd
        },
        {
            "type": 'int', "name": 'trade_col', "data": {"max_int": 20},
            "translate_message": True,
            'message': {'text': 'add_product.wait_count', 
                        'reply_markup': count_markup(20, lang)}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': chect_items_received
        }
    ]
    if prepare:
        steps = prepare_steps(not_p_steps, userid, chatid, lang)
        return steps
    else: return not_p_steps

async def received_upd(transmitted_data):
    """ Функция добавляет предмет в игнор страницы, а так же очищает некоторые данные
    """
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['trade_items']) == list:
        item_data = transmitted_data['return_data']['trade_items'][-1]
    else:
        item_data = transmitted_data['return_data']['trade_items']

    # Добавление данных для выбора количества
    transmitted_data['exclude'].append(item_data['item_id'])
    # Очистка лишних данных
    transmitted_data['steps'][step-1] = {}

    return transmitted_data, True

def chect_items_received(transmitted_data):
    """ Функция создаёт проверку на дополнительные предметы, 
    если предметов меньше чем 3
    """
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
                "type": 'update_data', "name": None, "data": {}, 
                'function': new_received_circle
            }
        ]
        steps = prepare_steps(not_p_steps, userid, chatid, lang)
        transmitted_data['steps'] += steps

    return transmitted_data, True

async def new_received_circle(transmitted_data):
    """ Функция создаёт круг запроса (активируется когда человек хочет добавить 2-ой и 3-ий товар в продукт)
    """
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    add_res = transmitted_data['return_data']['add_item']
    exclude_ids = transmitted_data['exclude']
    option = transmitted_data['option']

    if add_res:
        items, exclude = generate_items_pages(exclude_ids)
        steps = received_circle(userid, chatid, lang, items, option)

        transmitted_data['exclude'] = exclude

        transmitted_data['steps'].clear()
        transmitted_data['steps'] = steps
        del transmitted_data['return_data']['add_item']

        transmitted_data['process'] = -1

        return transmitted_data, True
    return transmitted_data, False

async def stock(return_data, transmitted_data):
    """ Запращивает запас у пользователя
    """
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    option = transmitted_data['option']

    if type(return_data['trade_items']) != list:
        return_data['trade_items'] = [return_data['trade_items']]
        return_data['trade_col'] = [return_data['trade_col']]

    for key, item in return_data.items(): transmitted_data[key] = item

    await ChooseIntState(stock_adapter, userid, chatid, lang, 1, 20, transmitted_data=transmitted_data)

    await bot.send_message(chatid, t(f'add_product.stock.{option}', lang), reply_markup=cancel_markup(lang), parse_mode='Markdown')

async def stock_adapter(in_stock:int, transmitted_data:dict):
    """ Запращивает запас у пользователя (конец)
    """

    price, a = [], 0
    for item in transmitted_data['trade_items']:
        price += [item] * transmitted_data['trade_col'][a]
        a += 1

    del transmitted_data['trade_items']
    del transmitted_data['trade_col']
    
    return_data = {
        'price': price,
        'in_stock': in_stock
    }

    await end(return_data, transmitted_data)