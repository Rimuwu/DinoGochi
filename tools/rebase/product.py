import json
import random
import string
import threading
import time
from pprint import pprint

import pymongo
from time import time, sleep
# import sys

from bson.objectid import ObjectId

client = pymongo.MongoClient('localhost', 27017)

referals = client.user.referals
users = client.user.users
langs = client.user.lang
dinosaurs = client.dinosaur.dinosaurs
old = client.bot.users
friends = client.user.friends
items = client.items.items
dino_owners = client.dinosaur.dino_owners
incubations = client.dinosaur.incubation

managment = client.bot.managment


with open('../../bot/json/items.json', encoding='utf-8') as f: 
    ITEMS = json.load(f)
    
with open('../../bot/json/old_ids.json', encoding='utf-8') as f: 
    ids = json.load(f)

with open('products.json', encoding='utf-8') as f: 
    products_d = json.load(f)

def random_dict(data: dict) -> int:
    """ Предоставляет общий формат данных, подерживающий 
       случайные и статичные элементы.

    Типы словаря:
    { "min": 1, "max": 2, "type": "random" }
    >>> Случайное число от 1 до 2
    { "act": [12, 42, 1], "type": "choice" } 
    >>> Случайный элемент
    { "act": 1, "type": "static" }
    >>> Статичное число 1
    """

    if type(data) == dict:
        if data["type"] == "static": return data['act']

        elif data["type"] == "random":
            if data['min'] < data['max']:
                return random.randint(data['min'], data['max'])
            else: return data['min']
        
        elif data["type"] == "choice":
            if data['act']: return random.choice(data['act'])
            else: return 0
    elif type(data) == int: return data
    return 0

def random_code(length: int=10):
    """ Генерирует случайный код из букв и цыфр
    """
    alphabet = string.ascii_letters + string.digits
    code = ''.join(random.choice(alphabet) for i in range(length))
    return code

def get_item_dict(itemid: str, preabil: dict = {}) -> dict:
    ''' Создание словаря, хранящийся в инвентаре пользователя.\n

        Примеры: 
            Просто предмет
                >>> f(12)
                >>> {'item_id': "12"}

            Предмет с предустоновленными данными
                >>> f(30, {'uses': 10})
                >>> {'item_id': "30", 'abilities': {'uses': 10}}
    '''
    d_it = {'item_id': itemid}
    data = get_data(itemid)

    if 'abilities' in data.keys():
        abl = {}
        for k in data['abilities'].keys():

            if type(data['abilities'][k]) == int:
                abl[k] = data['abilities'][k]

            elif type(data['abilities'][k]) == dict:
                abl[k] = random_dict(data['abilities'][k])

        d_it['abilities'] = abl 

    if preabil != {}:
        if 'abilities' in d_it.keys():
            for ak in d_it['abilities']:
                if ak in preabil.keys():

                    if type(preabil[ak]) == int:
                        d_it['abilities'][ak] = preabil[ak] 

                    elif type(preabil[ak]) == dict:
                        d_it['abilities'][ak] = random_dict(preabil[ak]) 
        else: 
            d_it['abilities'] = preabil 

    return d_it

def get_data(itemid: str) -> dict:
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if itemid in ITEMS.keys():
        return ITEMS[itemid]
    else: return {}

def AddItemToUser(userid: int, itemid: str, count: int = 1, preabil: dict = {}):
    """Добавление стандартного предмета в инвентарь
    """
    assert count >= 0, f'AddItemToUser, count == {count}'
    

    item = get_item_dict(itemid, preabil)
    find_res = items.find_one({'owner_id': userid, 'items_data': item}, {'_id': 1})

    if find_res: action = 'plus_count'
    elif 'abilities' in item or preabil: action = 'new_edited_item'
    else: action = 'new_item'

    if action == 'plus_count' and find_res:
        items.update_one({'_id': find_res['_id']}, {'$inc': {'count': count}})
    elif action == 'new_edited_item':
        for _ in range(count):
            item_dict = {
                'owner_id': userid,
                'items_data': item,
                'count': 1
            }
            items.insert_one(item_dict, True)
    else:
        item_dict = {
            'owner_id': userid,
            'items_data': item,
            'count': count
        }
        items.insert_one(item_dict)

    return action

def save(data):
    with open(f'products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_product(userid: int, user_products):
    
    if userid not in products_d['users']:
    
        for key, value in user_products['products'].items():
            
            col = value['col'][1] - value['col'][0]
            item = value['item']

            new_id = ids[ str(item['item_id']) ]
            preabil = {}
            if 'abilities' in item:
                for key, value in item['abilities'].items():
                    if value <= 0:
                        item['abilities'][key] = 1
                    if 'abilities' in ITEMS[new_id]:
                        if value > ITEMS[new_id]['abilities'][key]:
                            item['abilities'][key] = ITEMS[new_id]['abilities'][key]
                preabil = item['abilities']
            
            AddItemToUser(int(userid), new_id, col, preabil)
            
        products_d['users'].append(userid)
        save(products_d)

prd = managment.find_one({'_id': 'products'})
lenl = len(prd['products'])
a = 0
for key, value in prd['products'].items():
    a += 1
    print(key)
    print(a, lenl)
    add_product(key, value)

# itms = list(items.find({}))
# lenl = len(itms)
# a = 0

# for i in itms:
#     a += 1
#     if type(i['owner_id']) == str:
#         items.update_one({'_id': i['_id']}, {'$set': {'owner_id': int(i['owner_id'])}})
    
#     print(a, lenl)