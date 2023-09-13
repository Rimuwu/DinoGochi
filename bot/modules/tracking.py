from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, InputMedia)

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.localization import get_data, t, get_lang
from bot.modules.currency import get_all_currency, get_products
from bot.modules.item import counts_items
from bot.modules.data_format import seconds_to_str
from bot.modules.data_format import list_to_inline
from time import time

management = mongo_client.other.management

async def creat_track(name: str):
    """Создаёт ссылку отслеживания 
        0 - не найден документ
        -1 - не получается повторно получить имя
        -2 - уже отслеживается
        1 - всё супер!
    """
    res = await management.find_one({'_id': 'tracking_links'})
    if res:
        links = res['links']
        if name not in res['links'].keys():
            data = {
                'col': 0,
                'start': int(time())
            }
            await management.update_one({'_id': 'tracking_links'}, 
                                {'$set': {f'links.{name}': data}})

            res = await management.find_one({'_id': 'tracking_links'})
            if res:
                if name in links.keys(): return 1
                else: return -1
        else: return -2
    return 0

async def get_track_pages() -> dict:
    res = await management.find_one({'_id': 'tracking_links'})
    data = {}
    if res:
        links = list(res['links'])
        for i in links: data[i] = i

    return data

async def track_info(code: str, lang: str):
    res = await management.find_one({'_id': 'tracking_links'})
    text, markup = 'not found', None

    if res:
        if code in res['links'].keys():
            data = res['links'][code]
            text_data = get_data('track', lang)

            iambot = await bot.get_me()
            bot_name = iambot.username

            tt = seconds_to_str(int(time()) - data['start'], lang)

            url = f'https://t.me/{bot_name}/?promo={code}'
            text = text_data['text'].format(
                url=url, code=code, t=tt, use=data['col']
            )

            markup = list_to_inline(
                [{
                    text_data['delete']: f'track delete {code}',
                    text_data['clear']: f'track clear {code}'
                }]
            )

    return text, markup

async def add_track(name:str):
    res = await management.find_one({'_id': 'tracking_links'})
    if res:
        if name in res['links'].keys():
            await management.update_one({'_id': 'tracking_links'}, 
                                {'$inc': {f'links.{name}.col': 1}})
            return True
    return False