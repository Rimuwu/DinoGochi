import json
import os
from typing import Any, Optional
from bot.exec import bot
from aiogram.types import LabeledPrice
from bot.modules.data_format import random_code

from bot.const import GAME_SETTINGS
from bot.modules.items.item import AddItemToUser
from bot.modules.localization import get_data, get_lang
from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.modules.user.user import award_premium
from bot.dbmanager import mongo_client

from bot.modules.overwriting.DataCalsses import DBconstructor
import time

users = DBconstructor(mongo_client.user.users)

directory = 'bot/data/donations.json'
products = GAME_SETTINGS['products']

def save(donat_data):
    """Сохраняет данные в json
    """
    with open(directory, 'w', encoding='utf-8') as file:
        json.dump(donat_data, file, sort_keys=True, indent=4, ensure_ascii=False)

def OpenDonatData():
    """Загружает данные обработанных донатов
    """
    processed_donations: dict[str, dict[str, Any]] = {}
    try:
        with open(directory, encoding='utf-8') as f: 
            processed_donations = json.load(f)
    except Exception as error:
        if not os.path.exists(directory):
            with open(directory, 'w', encoding='utf-8') as f:
                f.write('{}')
        else:
            log(prefix='OpenDonatData', message=f'Error: {error}', lvl=4)
    return processed_donations

def save_donation(userid: int, user_first_name: str, amount: int, product: Optional[str], time_data: int, col: int, donation_id) -> str:
    code = f"{random_code(5)}_{userid}"

    data = {
        'userid': userid, 
        'user_first_name': user_first_name,
        'amount': amount,
        'product': product,
        'issued_reward': False,
        'send_notification': False,
        'time': time_data,
        'col': col,
    }
    
    try:
        data['donation_id'] = str(donation_id)
    except Exception as e: pass

    donat_data = OpenDonatData()
    donat_data[code] = data
    save(donat_data)

    return code

async def send_donat_notification(userid:int, message_key:str, info_code:str):
    try:
        chat_user = await bot.get_chat_member(userid, userid)
        user = chat_user.user
        lang = await get_lang(user.id)
    except Exception as e:
        log(prefix='send_donat_notification', message=f'Error {e}', lvl=3)
        lang = 'en'

    await user_notification(userid, f'donation', lang, add_way=message_key)

    donat_data = OpenDonatData()
    if info_code in donat_data:
        donat_data[info_code]['send_notification'] = True
        save(donat_data)

async def give_reward(userid:int, product_key:str, col:int, info_code: str):
    product = products[product_key]

    if product['type'] == 'subscription':
        await award_premium(userid, product['time'] * col)
    
    elif product['type'] == 'super_coins':
        await users.update_one({'userid': userid}, 
            {'$inc': {'super_coins': col}}, comment='give_reward')

    for item_id in product['items'] * col:
        await AddItemToUser(userid, item_id)

    donat_data = OpenDonatData()
    if info_code in donat_data:
        donat_data[info_code]['issued_reward'] = True
        save(donat_data)

    await send_donat_notification(userid, 'reward', info_code)

async def send_inv(user_id: int, product_id: str, col: str, lang: str, cost: int = 0):
    products = GAME_SETTINGS['products']
    if product_id != 'non_repayable':
        product = products[product_id]
    else:
        product = {
            "cost": {f"{col}": {
                "XTR": cost
            } }
        }

    product_t_data = get_data(f'support_command.products_bio.{product_id}', lang)

    name = product_t_data['name']
    short = product_t_data['short']
    photo_url = product_t_data['photo_url']

    product_label = LabeledPrice(label=name, amount=product['cost'][str(col)]['XTR'])

    await bot.send_invoice(
        user_id, name, short + f' (x{col})', f"{product_id}#{col}", 'XTR', [product_label],
        photo_url=photo_url, photo_size=512, photo_height=360, photo_width=720, 
    )

async def get_history(timeline: int = 0):
    """Получает историю донатов за timeline дней
    """
    donations = OpenDonatData()
    result = []
    current_time = time.time()
    if donations:
        for key, donation in donations.items():
            if timeline == 0 or (current_time - donation['time'] <= timeline * 86400):

                if 'user_first_name' in donation:
                    # Новая структура данных
                    donation['usename'] = donation.pop('user_first_name')
                else:
                    # Старая структура данных
                    user_id = int(key.split('_')[1])  # Извлекаем user_id из ключа
                    donation['username'] = donation.pop('userid')  # Заменяем userid на username
                    donation['userid'] = int(user_id)  # Добавляем user_id в элемент

                result.append(donation)
    return result