
from bot.models.user import User, Subscription
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

from bot.dbmanager import mongo_client

import time



from bot.models.other import Donation

products = GAME_SETTINGS['products']

async def save_donation(userid: int, user_first_name: str, amount: int, product: Optional[str], time_data: int, col: int | str, donation_id) -> str:
    code = f"{random_code(5)}_{userid}"

    data = Donation(
        code=code,
        userid=userid,
        user_first_name=user_first_name,
        amount=amount,
        product=product,
        issued_reward=False,
        send_notification=False,
        time=time_data,
        col=col,
        donation_id=str(donation_id) if donation_id is not None else None,
        status="done"
    )
    await data.insert()
    return code

async def send_donat_notification(userid: int, message_key: str, info_code: str):
    try:
        chat_user = await bot.get_chat_member(userid, userid)
        user = chat_user.user
        lang = await get_lang(user.id)
    except Exception as e:
        log(prefix='send_donat_notification', message=f'Error {e}', lvl=3)
        lang = 'en'

    await user_notification(userid, 'donation', lang, add_way=message_key)

    donat = await Donation.find_one(Donation.code == info_code)
    if donat:
        donat.send_notification = True
        await donat.save()

async def give_reward(userid: int, product_key: str, col: int | str, info_code: str):
    product = products[product_key]

    if product['type'] == 'subscription':
        if col == 'inf':
            await Subscription.award_premium(userid, 'inf')
        else:
            await Subscription.award_premium(userid, product['time'] * col)

    elif product['type'] == 'super_coins':
        if col == 'inf': 
            col = 1
            log(f'Ошибка количества {userid} {product_key} inf {info_code}', 4)

        user = await User.find_one(User.userid == userid)
        if user:
            await user.add_super_coins(col)

    if col != 'inf': 
        for item_id in product['items'] * col:
            await AddItemToUser(userid, item_id)

    donat = await Donation.find_one(Donation.code == info_code)
    if donat:
        donat.issued_reward = True
        await donat.save()

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
    
    if col == 'inf':
        dp_text = ' (∞)'
    else:
        dp_text = f' (x{col})'

    await bot.send_invoice(
        user_id, name, short + dp_text, f"{product_id}#{col}", 'XTR', [product_label],
        photo_url=photo_url, photo_size=512, photo_height=360, photo_width=720, 
    )

async def get_history(timeline: int = 0):
    """Получает историю донатов за timeline дней
    """
    current_time = time.time()
    if timeline > 0:
        cutoff = int(current_time - timeline * 86400)
        donations = await Donation.find(Donation.time >= cutoff).to_list()
    else:
        donations = await Donation.find_all().to_list()

    result = []
    for donat in donations:
        donation_dict = donat.model_dump()
        donation_dict['usename'] = donation_dict.pop('user_first_name', '')
        result.append(donation_dict)
    return result