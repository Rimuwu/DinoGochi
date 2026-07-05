from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.items import Item
from bot.dbmanager import mongo_client
from bot.modules.localization import t

from bot.exec import main_router, bot

from bot.modules.markup import answer_markup, cancel_markup, count_markup
 
from bot.modules.states_fabric.state_handlers import ChooseIntHandler, ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import BaseUpdateType, ConfirmStepData, IntStepData, InventoryStepData, StepMessage, TimeStepData

from bot.modules.market.market import generate_items_pages, generate_sell_pages
from bot.modules.add_product.general import end

MAX_PRICE = 10_000_000

items = LazyCollection(Item)


def trade_circle(lang, items, option):
    """ Создаёт данные для круга получения данных предметов ПОЛЬЗОВАТЕЛЯ
    """

    steps = [
        InventoryStepData('items', StepMessage(
            text=f'add_product.chose_item.{option}',
            translate_message=True,
            ),
            inventory=items
        ),
        BaseUpdateType(trade_update_col),
        IntStepData('col', StepMessage(
            text='add_product.wait_count',
            translate_message=True,
            markup=count_markup(20, lang)
        )),
        BaseUpdateType(check_items_for_items)
    ]

    return steps


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
        from bot.const import GAME_SETTINGS
        limit_items = GAME_SETTINGS.get('market_max_product_items_items', 20)
        if max_count > limit_items: max_count = limit_items

        # Добавление данных для выбора количества
        transmitted_data['steps'][step+1]['data']['max_int'] = max_count
        transmitted_data['steps'][step+1]['message']['markup'] = count_markup(max_count, lang).model_dump()
        transmitted_data['exclude'].append(item_data['item_id'])

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
        steps = [
            ConfirmStepData('add_item', StepMessage(
                text='add_product.add_item',
                translate_message=True,
                markup=answer_markup(lang)
            )),
            BaseUpdateType(new_circle)
        ]
        
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
        steps = trade_circle(lang, items, option)

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
    

    if 'col' not in return_data:
        items_list = return_data['items']
        return_data['items'] = [{'item_id': i['item_id'], 'abilities': i.get('abilities', {})} for i in items_list]
        return_data['col'] = [i['count'] for i in items_list]
    elif type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    for key, item in return_data.items(): transmitted_data[key] = item

    from bot.const import GAME_SETTINGS
    limit = GAME_SETTINGS.get('market_max_product_items_items', 20)
    inv_items, exclude = generate_items_pages()
    steps = received_circle(lang, inv_items, "trade_items", limit=limit)
    transmitted_data['exclude'] = exclude

    await ChooseStepHandler(stock, userid, chatid, lang, steps,
                            transmitted_data=transmitted_data).start()

def received_circle(lang, items, option, limit: int = None):
    """ Создаёт данные для круга получения данных ЗАПРАШИВАЕМЫХ предметов
    """
    steps = [
        MultiInventoryStepData('trade_items', StepMessage(
            text=f'add_product.chose_item.{option}',
            translate_message=True,
            ),
            inventory=items,
            data={'cancel_text_key': 'confirm_slot_creation'},
            limit=limit
        )
    ]

    return steps


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
    # # Очистка лишних данных
    # transmitted_data['steps'][step-1] = {}

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
        steps = [
            ConfirmStepData('add_item', StepMessage(
                text='add_product.add_item',
                translate_message=True,
                markup=answer_markup(lang)
            )),
            BaseUpdateType(new_received_circle)
        ]
        
        
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
        from bot.const import GAME_SETTINGS
        limit = GAME_SETTINGS.get('market_max_product_items_items', 20)
        steps = received_circle(lang, items, option, limit=limit)

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


    await ChooseIntHandler(
        stock_adapter, userid, chatid, lang, 1, 20, 
        transmitted_data=transmitted_data).start()

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