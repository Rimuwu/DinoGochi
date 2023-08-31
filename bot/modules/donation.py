import json
import os
from time import time

import aiohttp

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.currency import get_products, get_all_currency
from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.modules.item import AddItemToUser
from bot.modules.user import award_premium
from bot.modules.localization import get_lang

users = mongo_client.user.users

directory = 'bot/data/donations.json'
processed_donations = {}
headers = {
    'Authorization': 'Bearer {token}'.format(token=conf.donation_token),
}

def save(data):
    """Сохраняет данные в json
    """
    with open(directory, 'w', encoding='utf-8') as file:
        json.dump(data, file, sort_keys=True, indent=4, ensure_ascii=False)

def OpenDonatData() -> dict:
    """Загружает данные обработанных донатов
    """
    processed_donations = {}
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

async def get_donations() -> list:
    """ Получает донаты
    """
    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.donationalerts.com/api/v1/alerts/donations', headers=headers) as response:
            data = dict(await response.json())
            try: return data['data']
            except: return []

def save_donation(userid, amount, status, product, 
            issued_reward, time_data, col):
    """
    id: {
        'userid': int, 
        'amount': int,
        'status': str,
        'product': str | None,
        'issued_reward': bool,
        'time': int,
        'col': int
    }
    """
    data = {
        'userid': userid, 
        'amount': amount,
        'status': status,
        'product': product,
        'issued_reward': issued_reward,
        'time': time_data,
        'col': col
    }
    return data

async def send_donat_notification(userid:int, message_key:str, **kwargs):
    try:
        chat_user = await bot.get_chat_member(userid, userid)
        user = chat_user.user
        lang = get_lang(user.id)
    except Exception as e:
        log(prefix='send_donat_notification', message=f'Error {e}', lvl=3)
        lang = 'en'

    await user_notification(userid, f'donation', lang, add_way=message_key, **kwargs)

async def give_reward(userid:int, product_key:str, col:int):
    products = get_products()
    product = products[product_key]

    if product['type'] == 'subscription':
        award_premium(userid, product['time'] * col)

    for item_id in product['items']:
        AddItemToUser(userid, item_id)

    await send_donat_notification(userid, 'reward')

async def check_donations():
    processed_donations = OpenDonatData()
    all_donations = await get_donations()
    products = get_products()

    for donat in all_donations:
        donation_data = {}
        product_col = "1"

        if str(donat['id']) not in processed_donations.keys():
            #Донат не был ранее обработан
            if int(time()) - donat['created_at_ts'] <= 3024000:
                if donat['username'].isdigit():
                    userid = int(donat['username'])
                    user = users.find_one({'userid': userid})
                    if user:
                        message_split = donat['message'].split('#$#')
                        product_key = message_split[0]
                        if product_key in products:
                            product = products[product_key]

                            if product['type'] == 'subscription':
                                if len(message_split) > 1:
                                    col = message_split[1]
                                    if col.isdigit():
                                        if col in product['cost'].keys():
                                            product_col = col

                            if donat['currency'] in get_all_currency():
                                cost = product['cost'][product_col][donat['currency']]
                                rub_cost = product['cost'][product_col]['RUB']

                                if donat['amount'] >= cost:
                                    await give_reward(userid, product_key, int(product_col))

                                    donation_data = save_donation(
                                        donat['username'], 
                                        donat['amount'], 'done', 
                                        product_key, True, donat['created_at_ts'],
                                        product_col
                                    )

                                elif donat['amount_in_user_currency'] >= rub_cost:
                                    await give_reward(userid, product_key, int(product_col))

                                    donation_data = save_donation(
                                        donat['username'], 
                                        donat['amount'], 'done', 
                                        product_key, True, donat['created_at_ts'],
                                        product_col
                                    )

                                else:
                                    #Сумма доната меньше, чем стоимость продукта
                                    error = 'amount_error'
                                    donation_data = save_donation(
                                        donat['username'], 
                                        donat['amount'], error, 
                                        product_key, False, donat['created_at_ts'],
                                        product_col
                                    )

                                    donation_data['difference'] = [
                                        cost - donat['amount'], 
                                        rub_cost - donat['amount_in_user_currency']
                                        ]

                                    await send_donat_notification(userid, error, 
                                                                difference=donation_data['difference'][0],
                                                                currency=donat['currency'],
                                                                col=product_col
                                                                )
                            else:
                                #Валюта доната не найдена в возможных
                                error = 'currency_key_error'
                                donation_data = save_donation(donat['username'], 
                                    donat['amount'], error, 
                                    product_key, False, donat['created_at_ts'],
                                    product_col
                                    )
                                donation_data['error_key'] = donat['currency']
                                await send_donat_notification(userid, error, 
                                                            currency=donat['currency'])
                        else:
                            #неправильно указан ключ товара
                            error = 'product_key_error'
                            donation_data = save_donation(donat['username'], 
                                donat['amount'], error, None, False, donat['created_at_ts'],
                                product_col
                                )
                            donation_data['error_key'] = product_key[:12]
                            await send_donat_notification(userid, error, 
                                                        product_key=product_key[:12])

                    else:
                        #id юзера не найдено в базе
                        error = 'userid_not_in_base'
                        donation_data = save_donation(donat['username'], 
                            donat['amount'], error, None, False, donat['created_at_ts'],
                            product_col
                            )
                else:
                    #id юзера может быть только число
                    error = 'userid_error'
                    donation_data = save_donation(donat['username'], 
                            donat['amount'], error, None, False, donat['created_at_ts'],
                            product_col
                            )
            processed_donations[str(donat['id'])] = donation_data

        else:
            if int(time()) - donat['created_at_ts'] >= 3024001:
                del processed_donations[str(donat['id'])]

    save(processed_donations)
