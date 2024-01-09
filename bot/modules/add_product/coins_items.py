from bot.config import mongo_client

from bot.modules.markup import answer_markup, count_markup
from bot.modules.states_tools import prepare_steps

from bot.modules.market import generate_items_pages

MAX_PRICE = 10_000_000
items = mongo_client.items.items

def circle_data(userid, chatid, lang, items, option, prepare: bool = True):
    """ Создай данные для запроса: предмета, количества, надо ли повторить
    """
    not_p_steps = [
        {
            "type": 'inv', "name": 'items', "data": {'inventory': items}, 
            "translate_message": True,
            'message': {'text': f'add_product.chose_item.{option}'}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': order_update_col
        },
        {
            "type": 'int', "name": 'col', "data": {"max_int": 20},
            "translate_message": True,
            'message': {'text': 'add_product.wait_count', 
                        'reply_markup': count_markup(20, lang)}
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

async def order_update_col(transmitted_data):
    """ Функция добавляет предмет в игнор страницы, а так же очищает некоторые данные
    """
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['items']) == list:
        item_data = transmitted_data['return_data']['items'][-1]
    else:
        item_data = transmitted_data['return_data']['items']

    # Добавление данных для выбора количества
    transmitted_data['exclude'].append(item_data['item_id'])
    # Очистка лишних данных
    transmitted_data['steps'][step-1] = {}

    return transmitted_data, True

def check_items(transmitted_data):
    """ Функция создаёт проверку на дополнительные предметы, 
        если предметов меньше чем 3 то спрашивает - добавить ли ещё предмет
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
        items, exclude = generate_items_pages(exclude_ids)
        steps = circle_data(userid, chatid, lang, items, option)

        transmitted_data['exclude'] = exclude

        transmitted_data['steps'].clear()
        transmitted_data['steps'] = steps
        del transmitted_data['return_data']['add_item']

        transmitted_data['process'] = -1

        return transmitted_data, True
    return transmitted_data, False