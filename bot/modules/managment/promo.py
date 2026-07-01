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
    from bot.modules.states_fabric.steps_datatype import MultiInventoryStepData
    from bot.modules.market.market import generate_items_pages

    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    code = return_data['code']
    coins = return_data['coins']
    count = return_data['count']
    time_end = return_data['time_end']

    all_items_data, _ = generate_items_pages(ignore_cant=True)
    inventory = []
    for it in all_items_data:
        inventory.append({
            'items_data': it['item'],
            'count': 1000
        })

    steps = [
        MultiInventoryStepData('items', StepMessage(
            text=t('promo.chose_item', lang, default='🎁 Выберите предметы для промокода:'),
            translate_message=False,
        ), inventory=inventory)
    ]

    promo_transmitted = {
        'code': code,
        'coins': coins,
        'count': count,
        'time_end': time_end,
        'username': transmitted_data.get('username', 'Admin')
    }

    await ChooseStepHandler(end_promo_creation, userid, chatid, lang, steps,
                            transmitted_data=promo_transmitted).start()


async def end_promo_creation(return_data, transmitted_data):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    code = transmitted_data['code']
    coins = transmitted_data['coins']
    count = transmitted_data['count']
    time_end = transmitted_data['time_end']

    chosen_items = return_data['items']
    
    add_items = []
    for item in chosen_items:
        abilities = item.get('abilities', {})
        add_items.append({
            'item_id': item['item_id'],
            'abilities': abilities,
            'count': item['count']
        })

    if time_end == 0: time_end = 'inf'
    if count == 0: count = 'inf'

    await create_promo(code, count, time_end, coins, add_items)

    text, markup = await promo_ui(code, lang)
    try:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)
    except:
        await bot.send_message(chatid, text, reply_markup=markup)
    
    await bot.send_message(chatid, '✅', reply_markup=await m(userid, 'last_menu', lang))

async def create_promo(code: str, col, seconds, coins: int, items: list, active: bool = False):
    return await Promo.create_promo(code, col, seconds, coins, items, active)

async def promo_ui(code: str, lang: str):
    return await Promo.promo_ui(code, lang)

async def get_promo_pages() -> dict:
    return await Promo.get_promo_pages()

async def use_promo(code: str, userid: int, lang: str):
    return await Promo.use_promo(code, userid, lang)