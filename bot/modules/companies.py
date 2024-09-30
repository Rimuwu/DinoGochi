"""

Размещение рекламных сообщений партнёров

"""


from datetime import datetime, timezone
import json
import random
from time import time
from typing import Union
from bson import ObjectId
from bot.dbmanager import mongo_client, conf
from bot.exec import bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.modules.data_format import list_to_inline, random_code, seconds_to_str
from bot.modules.localization import get_lang, t, get_data

from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import DBconstructor

companies = DBconstructor(mongo_client.other.companies)
message_log = DBconstructor(mongo_client.other.message_log)
users = DBconstructor(mongo_client.user.users)
ads = DBconstructor(mongo_client.user.ads)

async def generation_code(owner_id):
    code = f'{owner_id}_{random_code(4)}'
    if await companies.find_one({'alt_id': code}, comment='generation_code_companies'):
        code = await generation_code(owner_id)
    return code

async def create_company(owner: int, message: dict, time_end: int, 
                        count: int, coin_price: int, priority: bool, 
                        one_message: bool, pin_message: bool, min_timeout: int,
                        delete_after: bool, ignore_system_timeout: bool, name: str):
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

    if time_end == 0: end = 0
    else: end = time_end + int(time())

    data = {
        'owner': owner,
        'message': message,

        'langs': list(message.keys()),

        'time_end': end,
        'time_start': int(time()),

        'max_count': count, 'show_count': 0,
        'coin_price': coin_price,

        'priority': priority,
        'one_message': one_message,
        'pin_message': pin_message,
        'delete_after': delete_after,
        'ignore_system_timeout': ignore_system_timeout,

        'min_timeout': min_timeout,

        'status': False,
        'name': name,
        'alt_id': await generation_code(owner)
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
    await companies.update_one({'_id': advert_id}, {'$inc': {'show_count': 1}})

    ads_cabinet = await ads.find_one({'userid': userid}, comment='save_message')
    if ads_cabinet:
        await ads.update_one({'_id': ads_cabinet['_id']}, 
                         {"$set": {'last_ads': int(time())}}, comment='save_message')

async def end_company(advert_id: ObjectId):
    companie = await companies.find_one({'_id': advert_id})

    if companie:
        await companies.delete_one({'_id': advert_id})
        
        for i in set([companie['owner']] + conf.bot_devs):
            lang = await get_lang(i)
            try:
                await botworker.send_message(i,
                    t('companies.end_company', lang, 
                    time_work = seconds_to_str(int(time()) - companie['time_start'], lang),
                    show_count = companie['show_count'],
                    max_count = companie['max_count'],
                    name = companie['name'])
                    )
            except Exception as e:
                log(f'except in end_company {e}', 3)

        if companie['delete_after']:
            messages = await message_log.find({'advert_id': advert_id})

            for mes in messages:
                if companie['pin_message']:
                    try:
                        await bot.unpin_chat_message(mes['userid'],
                                                     mes['message_id'])
                    except: pass
                try:
                    await botworker.delete_message(mes['userid'],
                                             mes['message_id'])
                except: pass
                await message_log.delete_one({'_id': mes['_id']})

        else:
            await message_log.delete_one({'advert_id': advert_id})

async def generate_message(userid: int, company_id: ObjectId, lang = None, 
                           save = True):
    """ Собирает сообщение и публикует его у пользователя

        message: {
            "ru": {
                "text": str,
                "markup": [{"name": "url"}],
                "parse_mode": str, # Mardown | HTML
                "image": str (url отправленного файла)
            }
        }

    """
    if not lang: lang = await get_lang(userid)

    companie = await companies.find_one({'_id': company_id})
    if companie and lang in companie['message'].keys():
        message = companie['message'][lang]

        text = message['text']
        parse_mode = message['parse_mode']
        image = message['image']

        inline = InlineKeyboardMarkup()
        for i in message['markup']:
            for key, value in i.items():
                inline.add(
                    InlineKeyboardButton(
                        text=key, 
                        url=value
                ))

        if image != 'no_image':
            try:
                m = await botworker.send_photo(userid, image, text, parse_mode, 
                                     reply_markup=inline)
            except Exception as e:
                log(f'generate_comp_message image error - {e}', 2)
                m = await botworker.send_photo(userid, image, text, 
                                     reply_markup=inline)
        else:
            try:
                m = await botworker.send_message(userid, text, 
                                       parse_mode=parse_mode, reply_markup=inline)
            except Exception as e:
                log(f'generate_comp_message error - {e}', 2)
                m = await botworker.send_message(userid, text, 
                                     reply_markup=inline)

        # Сохраняем
        if m and save:
            await save_message(company_id, userid, m.id)

        # Закрепляем
        if companie['pin_message'] and save:
            s = await bot.pin_chat_message(m.chat.id, m.id)
            try:
                if s: await botworker.delete_message(m.chat.id, m.id + 1)
            except: pass

        # Награда
        if companie['coin_price'] > 0 and m and save:
            await users.update_one({"userid": userid}, 
                                {'$inc':
                                    {"super_coins": companie['coin_price']}},
                            comment='generate_message')
            try:
                await botworker.send_message(userid, 
                                    t('super_coins.moder_reward', lang, coin=companie['coin_price']), parse_mode="Markdown")
            except:
                await botworker.send_message(userid, 
                                    t('super_coins.moder_reward', lang, coin=companie['coin_price']))
        return m.id
    return None

async def nextinqueue(userid: int, lang = None) -> Union[ObjectId, None]:
    """ Создаёт словарь с количеством показов каждой компании, после выбирает первую компанию какую компанию активировать
    """
    if not lang: lang = await get_lang(userid)

    count_dct, permissions = {}, {}
    # Смотрим на сообщения по этой компании уже отправленные пользователю
    messages = await message_log.find({'userid': userid})
    # Получаем активные компании
    comps = await companies.find(
        {'status': True, 'langs': {'$in': [lang]} }, 
        {'_id': 1, 'one_message': 1, 'min_timeout': 1,
         'time_end': 1, 'show_count': 1, 'max_count': 1})

    # Создаём структуру 
    for i in comps:
        if i['show_count'] >= i['max_count'] and i['max_count'] != 0:
            await end_company(i['_id'])

        elif int(time()) > i['time_end'] and i['time_end'] != 0:
            await end_company(i['_id'])

        else:
            count_dct[i['_id']] = 0
            permissions[i['_id']] = {'one_message': i['one_message'],
                                    'min_timeout': i['min_timeout'],
                                    'last_send': -1
                                    }

    # Проверяем, есть ли активные компании
    if count_dct:
        # Считаем сколько показов было для человека по этой рекламе
        for mes in messages:
            # Проверка на включена ли компания
            if mes['advert_id'] in count_dct:
                count_dct[mes['advert_id']] += 1

                send_time = mes['_id'].generation_time
                now = datetime.now(timezone.utc)
                delta = now - send_time # Сколько секунд назад было отправлено сообщение

                # Сохраняем время последней отправки (последнее = наименьшее)
                if delta.seconds < permissions[mes['advert_id']]['last_send'] or \
                    permissions[mes['advert_id']]['last_send'] == -1:
                    permissions[mes['advert_id']]['last_send'] = delta.seconds

        result_dct = count_dct.copy()
        for key, value in count_dct.items():
            if value > 0:
                # Если уже отправлено 1 сообщение по этой рассылке, то не выдаём его в очереди
                if permissions[key]['one_message']: del result_dct[key]
                # Если компания ещё не отдохнула от прошлого оповещения, то удаляем
                if permissions[key]['last_send'] < permissions[key]['min_timeout']:
                    if key in result_dct:
                        del result_dct[key]

        if result_dct.values():
            # Показы распределяются равномерно 
            min_value = min(count_dct.values())
            min_keys = list(filter(lambda k: count_dct[k] == min_value, count_dct))
            r_key = random.choice(min_keys)

            return r_key
    return None

async def priority_and_timeout(companie_id: ObjectId):
    f = await companies.find_one({'_id': companie_id})
    if f: return f['priority'], f['ignore_system_timeout']
    return False, False

async def info(companie_id: ObjectId, lang = None):
    c = await companies.find_one({'_id': companie_id})
    text = ''
    mrk = InlineKeyboardMarkup()

    if c:
        if not lang: lang = await get_lang(c['owner'])
        text = t('companies.info', lang,
                 name=c['name'],
                 end=seconds_to_str(c['time_end']-int(time()), lang),
                 delta=seconds_to_str(time()-c['time_start'], lang),
                 show=c['show_count'],
                 max_c=c['max_count'],
                 coin=c['coin_price'],
                 priority=c['priority'],
                 pin=c['pin_message'],
                 timeout=c['min_timeout'],
                 sys_timeout=c['ignore_system_timeout'],
                 dlete_after=c['delete_after'],
                 status=c['status'])

        btn = get_data('companies.buttons', lang)
        new_btn = {}
        for key, value in btn.items():
            new_btn[
                value
            ] = f'company_info {key} {c["alt_id"]}'

        mrk = list_to_inline([new_btn])

    return text, mrk