from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.other import Promo
from bot.models.user import User

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.get_state import get_state
from bot.modules.items.item import counts_items, AddItemToUser
from bot.modules.localization import get_data, t
from bot.modules.market.market import generate_items_pages
from bot.modules.markup import answer_markup, cancel_markup, count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.market.market import generate_items_pages
from time import time
import json

from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import BaseUpdateType, ConfirmStepData, IntStepData, InventoryStepData, StepMessage, StringStepData, TimeStepData
 

promo = LazyCollection(Promo)
users = LazyCollection(User)


async def create_promo_start(userid: int, chatid: int, lang: str):

    steps = [
        StringStepData('code', StepMessage(
            text='promo.code',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_len=0, min_len=1
        ),
        IntStepData('coins', StepMessage(
            text='promo.coins',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_int=100_000, min_int=0
        ),
        IntStepData('count', StepMessage(
            text='promo.count',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_int=1_000_000, min_int=0
        ),
        TimeStepData('time_end', StepMessage(
            text='promo.time_end',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_int=0, min_int=0
        )
    ]

    # await ChooseStepState(start_items, userid, chatid, lang, steps)
    await ChooseStepHandler(start_items, userid, chatid, 
                            lang, steps).start()


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

    await ChooseStepHandler(end, userid, chatid, lang, steps,
                          transmitted_data={'code': code, 'coins': coins,
                                            'count': count, 'time_end': time_end}
                          ).start()

""" Создаёт данные для круга получения данных для типа coins_items
"""
def circle_data(userid, chatid, lang, items, prepare: bool = True):
    steps = [
        InventoryStepData('items', StepMessage(
            text='promo.chose_item',
            translate_message=True,
            ),
            inventory=items
        ),
        StringStepData('abilities', StepMessage(
            text='promo.abilities',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_len=0, min_len=1
        ),
        BaseUpdateType(update_col),
        IntStepData('col', StepMessage(
            text='css.wait_count',
            translate_message=True,
            markup=None),
            max_int=10
        ),
        BaseUpdateType(check_items)
    ]

    return steps


""" Функция выставляет максимальное количетсво предмета
"""
def update_col(transmitted_data):
    lang = transmitted_data['lang']
    step = transmitted_data['process']

    if type(transmitted_data['return_data']['items']) == list:
        item_data = transmitted_data['return_data']['items'][-1]
    else:
        item_data = transmitted_data['return_data']['items']

    if type(transmitted_data['return_data']['items']) == list:
        abil = transmitted_data['return_data']['abilities'][-1].replace("'", '"')
    else:
        abil = transmitted_data['return_data']['abilities'].replace("'", '"')

    if abil != '0':
        item_data.update(
            abilities=json.loads(abil)
        )

    # Добавление данных для выбора количества
    transmitted_data['steps'][step+1]['data']['max_int'] = 1000
    transmitted_data['steps'][step+1]['message']['markup'] = count_markup(100, lang).model_dump()
    if 'exclude' not in transmitted_data: 
        transmitted_data['exclude'] = []
    transmitted_data['exclude'].append(item_data['item_id'])

    # # Очистка лишних данных
    # transmitted_data['steps'][step-1] = {}

    return transmitted_data, True

def check_items(transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

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
    return await Promo.create_promo(code, col, seconds, coins, items, active)

async def promo_ui(code: str, lang: str):
    return await Promo.promo_ui(code, lang)

async def get_promo_pages() -> dict:
    return await Promo.get_promo_pages()

async def use_promo(code: str, userid: int, lang: str):
    return await Promo.use_promo(code, userid, lang)