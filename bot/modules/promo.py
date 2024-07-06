
from bot.config import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.item import counts_items, AddItemToUser
from bot.modules.localization import get_data, t
from bot.modules.market import generate_items_pages
from bot.modules.markup import answer_markup, cancel_markup, count_markup
from bot.modules.states_tools import ChooseStepState, prepare_steps
from bot.modules.markup import markups_menu as m
from bot.modules.market import generate_items_pages
from time import time
import json
 
from bot.modules.overwriting.DataCalsses import DBconstructor
promo = DBconstructor(mongo_client.other.promo)
users = DBconstructor(mongo_client.user.users)


async def create_promo_start(userid: int, chatid: int, lang: str):

    steps = [
        {
            "type": 'str', "name": 'code', "data": {"max_len": 0, "min_len": 1},
            "translate_message": True,
            'message': {'text': 'promo.code', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'int', "name": 'coins', "data": {"max_int": 100_000, 'min_int': 0},
            "translate_message": True,
            'message': {'text': 'promo.coins', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'int', "name": 'count', "data": {"max_int": 1_000_000, 'min_int': 0},
            "translate_message": True,
            'message': {'text': 'promo.count', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'time', "name": 'time_end', "data": {"max_int": 0, "min_int": 0},
            "translate_message": True,
            'message': {'text': 'promo.time_end', 
                        'reply_markup': cancel_markup(lang)}
        }
    ]

    await ChooseStepState(start_items, userid, chatid, lang, steps)

async def start_items(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    
    code = return_data['code']
    coins = return_data['coins']
    count = return_data['count']
    time_end = return_data['time_end']

    items, exclude = generate_items_pages(ignore_cant=True)
    steps = circle_data(userid, chatid, lang, items)
    await ChooseStepState(end, userid, chatid, lang, steps,
                          transmitted_data={'code': code, 'coins': coins,
                                            'count': count, 'time_end': time_end}
                          )

""" Создаёт данные для круга получения данных для типа coins_items
"""
def circle_data(userid, chatid, lang, items, prepare: bool = True):
    not_p_steps = [
        {
            "type": 'inv', "name": 'items', "data": {'inventory': items}, 
            "translate_message": True,
            'message': {'text': f'promo.chose_item'}
        },
        {
            "type": 'str', "name": 'abilities', "data": {"max_len": 0, "min_len": 1},
            "translate_message": True,
            'message': {'text': 'promo.abilities', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'update_data', "name": None, "data": {}, 
            'function': update_col
        },
        {
            "type": 'int', "name": 'col', "data": {"max_int": 10},
            "translate_message": True,
            'message': {'text': 'css.wait_count', 
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

""" Функция выставляет максимальное количетсво предмета
"""
def update_col(transmitted_data):
    lang = transmitted_data['lang']
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['items']) == list:
        item_data = transmitted_data['return_data']['items'][-1]
    else:
        item_data = transmitted_data['return_data']['items']
    
    abil = transmitted_data['return_data']['abilities'].replace("'", '"')
    if abil != '0':
        item_data.update(
            abilities=json.loads(abil)
        )

    # Добавление данных для выбора количества
    transmitted_data['steps'][step+1]['data']['max_int'] = 1000
    transmitted_data['steps'][step+1]['message']['reply_markup'] = count_markup(100, lang)
    if 'exclude' not in transmitted_data: 
        transmitted_data['exclude'] = []
    transmitted_data['exclude'].append(item_data['item_id'])

    # Очистка лишних данных
    transmitted_data['steps'][step-1] = {}

    return transmitted_data, True

def check_items(transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

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

""" Функция создаёт ещё 1 круг добавления предмета для типа
"""
def new_circle(transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    add_res = transmitted_data['return_data']['add_item']
    exclude_ids = transmitted_data['exclude']

    if add_res:
        items, exclude = generate_items_pages(exclude_ids, ignore_cant=True)
        steps = circle_data(userid, chatid, lang, items)

        transmitted_data['exclude'] = exclude

        transmitted_data['steps'].clear()
        transmitted_data['steps'] = steps
        del transmitted_data['return_data']['add_item']

        transmitted_data['process'] = -1

        return transmitted_data, True
    return transmitted_data, False

async def end(return_data, transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    code = transmitted_data['code']
    coins = transmitted_data['coins']
    count = transmitted_data['count']
    time_end = transmitted_data['time_end']

    if type(return_data['items']) != list:
        return_data['items']['count'] = return_data['col']
        add_items = [return_data['items']]
    else:
        add_items, a = [], 0
        for item in return_data['items']:
            item['count'] = return_data['col'][a]
            add_items.append(item)
            a += 1

    if time_end == 0: time_end = 'inf'
    if count == 0: count = 'inf'

    await create_promo(code, count, time_end, coins, add_items)

    text, markup = await promo_ui(code, lang)
    try:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)
    except:
        await bot.send_message(chatid, text, reply_markup=markup)
    await bot.send_message(chatid, '✅', reply_markup= await m(userid, 'last_menu', lang))

async def create_promo(code: str, col, seconds, coins: int, items: list, active: bool = False):

    promo_check = await promo.find_one({'code': code}, comment='create_promo_promo_check')

    if not promo_check:
        data = {
            "code": code,
            "users": [],
            "col": col,
            "time_end": seconds,
            "time": seconds,
            "coins": coins,
            "items": items,
            "active": active
        }

        await promo.insert_one(data, comment='create_promo')
        return True
    return False

async def promo_ui(code: str, lang: str):
    data = await promo.find_one({"code": code}, comment='promo_ui')
    text, markup = '', None

    if data:
        status = ''
        if data['active']: status = '✅'
        else: status = '❌'

        id_list = []
        for i in list(data['items']): id_list.append(i['item_id'])

        if data['time_end'] == 'inf':
            txt_time = '♾'
        else: txt_time = seconds_to_str(data['time_end'] - int(time()), lang)

        text = t('promo_commands.ui.text', lang,
                 code=code, status=status,
                 col=data['col'], coins=data['coins'],
                 items=counts_items(id_list, lang),
                 txt_time=txt_time)

        but = get_data('promo_commands.ui.buttons', lang)
        inl_l = {
            but[0]: f'promo {code} activ',
            but[1]: f'promo {code} delete',
            but[2]: f'promo {code} use'
        }

        markup = list_to_inline([inl_l], 2)
    return text, markup

async def get_promo_pages() -> dict:
    res = await promo.find({}, comment='get_promo_pages')
    data = {}
    if res: 
        for i in res: data[i['code']] = i['code']
    return data

async def use_promo(code: str, userid: int, lang: str):
    data = await promo.find_one({"code": code}, comment='use_promo')
    user = await users.find_one({'userid': userid}, {'userid': 1}, comment='use_promo_user')
    text = ''

    if user:
        if data:
            col = data['col']
            if col == 'inf': col = 1

            seconds = data['time_end']
            if seconds == 'inf': seconds = int(time()) + 100

            if data['active']:
                if col:
                    if seconds - int(time()) > 0:
                        if userid not in data['users']:

                            await promo.update_one({'_id': data['_id']},
                                             {"$push": {f'users': userid}
                                              }, comment='use_promo_1')

                            if data['col'] != 'inf':
                                await promo.update_one({'_id': data['_id']},
                                                 {"$inc": {f'col': -1}}, comment='use_promo_2')

                            text = t('promo_commands.activate', lang)
                            if data['coins']:
                                await users.update_one({'userid': userid}, {'$inc': {'coins': data['coins']}}, comment='use_promo_3')

                                text += t('promo_commands.coins', lang,
                                          coins=data['coins']
                                          )
                            if data['items']:
                                id_list = []
                                for item in data['items']:
                                    count = 1
                                    if 'count' in item: count = item['count']

                                    abil = {}
                                    if 'abilities' in item: abil = item['abilities']

                                    item_id = item['item_id']
 
                                    await AddItemToUser(userid, item_id, count, abil)
                                    id_list.append(item_id)

                                text += t('promo_commands.items', lang,
                                          items=counts_items(id_list, lang)
                                          )

                            return 'ok', text
                        else:
                            text = t('promo_commands.already_use', lang)
                            return 'already_use', text
                    else:
                        text = t('promo_commands.time_end', lang)
                        return 'time_end', text
                else:
                    text = t('promo_commands.max_col', lang)
                    return 'max_col_use', text
            else:
                text = t('promo_commands.deactivated', lang)
                return 'deactivated', text
        else:
            text = t('promo_commands.not_found', lang)
            return 'not_found', text
    text = t('promo_commands.no_user', lang)
    return 'no_user', text