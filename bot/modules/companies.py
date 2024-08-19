"""

Размещение рекламных сообщений партнёров

"""


import json
from time import time
from bson import ObjectId
from bot.config import mongo_client
from bot.exec import bot

from bot.modules.localization import get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
companies = DBconstructor(mongo_client.other.companies)
message_log = DBconstructor(mongo_client.other.message_log)


async def create_company(owner: int, message: dict, time_end: int, 
                        count: int, coin_price: int, priority: bool, 
                        one_message: bool, pin_message: bool, min_timeout: int,
                        delete_after: bool, ignore_system_timeout: bool):
    """
    owner: int

    message: {
        "ru": {
            "text": str,
            "markup": [{"name": "url"}],
            "parse_mode": str, # Mardown | HTML
            "image": str (url отправленного файла)
        }
    }

    time_end: int секунд | 'inf' Время завершения компании

    max_count: int | 'inf' Количество показов

    show_chount: int Показано раз

    priority: bool Имеет ли компания приоритетный над gramads

    one_message: bool Отправить одно сообщение одному юзеру

    pin_message: bool Закреплять ли сообщение

    coin_price: int Определяет награду за просмотр рекламы, если 0 - не отправлять сообщение

    min_timeout: int Минимальное время между показами для 1 пользователя

    delete_after: bool Удаление ли всех сообщений после завершения компании

    status: bool Статус активности компании

    ignore_system_timeout: bool Игнорировать ли таймаут пользователя

    """

    data = {
        'owner': owner,
        'message': message,

        'time_end': time_end + int(time()),
        'time_start': int(time()),

        'max_count': count, 'show_chount': 0,
        'coin_price': coin_price,

        'priority': priority,
        'one_message': one_message,
        'pin_message': pin_message,
        'delete_after': delete_after,
        'ignore_system_timeout': ignore_system_timeout,

        'min_timeout': min_timeout,

        'status': False
    }

    await companies.insert_one(data)

async def save_message(advert_id: ObjectId, userid: int, 
                     message_id: int):

    """
    advert_id: ObjectId - id Companie
    userid: int - id пользователя
    message_id - id сообщения 

    """

    data = {
        'advert_id': advert_id,
        'userid': userid,
        'message_id': message_id
    }

    await message_log.insert_one(data)

async def end_company(advert_id: ObjectId):
    companie = await companies.find_one({'_id': advert_id})

    if companie:
        if companie['delete_after']:
            messages = await message_log.find({'advert_id': advert_id})

            for mes in messages:
                if companie['pin_message']:
                    try:
                        await bot.unpin_chat_message(mes['userid'],
                                                     mes['message_id'])
                    except:
                        pass

                try:
                    await bot.delete_message(mes['userid'],
                                             mes['message_id'])
                except:
                    pass

                await message_log.delete_one({'_id': mes['_id']})

        else:
            await message_log.delete_one({'advert_id': advert_id})

        lang = await get_lang(companie['owner'])
        await bot.send_message(
            t('companies.end_company', lang)
        )

async def generate_message(userid: int, company_id: ObjectId):
    """ Собирает сообщение и публикует его у пользователя
    """

async def nextinqueue(userid: int):
    """ Создаёт словарь с количеством показов каждой компании, после выбирает первую компанию какую компанию активировать
    """
    count_dct = {}
    # id_dct = {}
    messages = await message_log.find(
        {'userid': userid})

    # a = -1
    # for mes in messages:
    #     if mes['_id'] not in id_dct:
    #         a += 1
    #         id_dct[str(a)] = mes['_id']
    #         id_str = a
    #     else:
    #         for key, value in id_dct.items():
    #             if value == mes['_id']:
    #                 id_str = key

        # count_dct[id_str] = count_dct.get(
        #     id_str, 0) + 1

    for mes in messages:
        js_id = json.dumps(
            mes['_id']
        )

        count_dct[
            js_id
        ] = count_dct.get(js_id, 0) + 1