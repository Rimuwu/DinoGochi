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
# sys.path.append('../../')

# from bot.modules.friends import insert_friend_connect
# from bot.modules.item import AddItemToUser
# from bot.modules.dinosaur import generation_code, create_dino_connection, incubation_egg
# from bot.const import GAME_SETTINGS as GS
# from bot.modules.localization import available_locales
available_locales = ['ru', 'en']

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

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

with open('../../bot/json/items.json', encoding='utf-8') as f: 
    ITEMS = json.load(f)
    
with open('../../bot/json/old_ids.json', encoding='utf-8') as f: 
    ids = json.load(f)

def item_code(item: dict, v_id: bool = True) -> str:
    """Создаёт код-строку предмета, основываясь на его
       харрактеристиках.
       
       v_id - определяет добавлять ли буквенный индефикатор
    """
    text = ''

    if v_id: text = f"id{item['item_id']}"

    if 'abilities' in item.keys():
        for key, item in item['abilities'].items():
            if v_id:
                text += f".{key[:2]}{item}"
            else:
                if type(item) == bool:
                    text += str(int(item))
                else: text += str(item)
    return text
def decode_item(code: str) -> dict:
    """Превращает код в словарь
    """
    split = code.split('.')
    ids = {
        'us': 'uses', 'en': 'endurance',
        'ma': 'mana', 'st': 'stack',
        'in': 'interact'
    }
    data = {}

    for part in split:
        scode = part[:2]
        value = part[2:]

        if scode == 'id': data['item_id'] = value
        else:
            if 'abilities' not in data.keys(): data['abilities'] = {}
            if value in ['True', 'False']:
                if value == 'True': value = True
                else: value = False
                data['abilities'][ ids[scode] ] = value
            else: data['abilities'][ ids[scode] ] = int(value)
    return data

class Egg:

    def __init__(self, baseid: ObjectId):
        """Создание объекта яйца."""
        
        self._id = baseid
        self.incubation_time = 0
        self.egg_id = 0
        self.owner_id = 0
        self.quality = 'random'
        self.dino_id = 0

        self.UpdateData(incubations.find_one({"_id": self._id}))

    def UpdateData(self, data):
        if data:
            self.__dict__ = data

    def __str__(self) -> str:
        return f'{self._id} {self.quality}'

    def update(self, update_data: dict):
        """
        {"$set": {'stats.eat': 12}} - установить
        {"$inc": {'stats.eat': 12}} - добавить
        """
        data = incubations.update_one({"_id": self._id}, update_data)

def incubation_egg(egg_id: int, owner_id: int, inc_time: int=0, quality: str='random', dino_id: int=0):
    """Создание инкубируемого динозавра
    """
    egg = Egg(ObjectId())
    
    if quality == 'myt': quality = 'mys'

    egg.incubation_time = inc_time + int(time())
    egg.egg_id = egg_id
    egg.owner_id = owner_id
    egg.quality = quality
    egg.dino_id = dino_id

    # if inc_time == 0: #Стандартное время инкцбации 
    #     egg.incubation_time = int(time()) + GS['first_dino_time_incub']

    return incubations.insert_one(egg.__dict__)


def create_dino_connection(dino_baseid: ObjectId, owner_id: int, con_type: str='owner'):
    """ Создаёт связь в базе между пользователем и динозавром
        con_type = owner / add_owner
    """

    assert con_type in ['owner', 'add_owner'], f'Неподходящий аргумент {con_type}'

    con = {
        'dino_id': dino_baseid,
        'owner_id': owner_id,
        'type': con_type
    }

    return dino_owners.insert_one(con)

def random_code(length: int=10):
    """ Генерирует случайный код из букв и цыфр
    """
    alphabet = string.ascii_letters + string.digits
    code = ''.join(random.choice(alphabet) for i in range(length))
    return code
    
def generation_code(owner_id: int):
    code = f'{owner_id}_{random_code(8)}'
    if dinosaurs.find_one({'alt_id': code}):
        code = generation_code(owner_id)
    return code
    
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

def insert_friend_connect(userid: int, friendid: int, action: str):
    """ Создаёт связь между пользователями
        friends, request
    """
    assert action in ['friends', 'request'], f'Неподходящий аргумент {action}'
    
    res = friends.find_one({
        'userid': userid,
        'friendid': friendid,
        'type': action
    })

    res2 = friends.find_one({
        'userid': friendid,
        'friendid': userid,
        'type': action
    })

    if not res and not res2:
        data = {
            'userid': userid,
            'friendid': friendid,
            'type': action
        }
        return friends.insert_one(data)
    return False


def new_dino(userid, d_d):
    
    d_d['stats']['energy'] = d_d['stats']['unv']
    del d_d['stats']['unv']
    
    if d_d['quality'] == 'myt':
        d_d['quality'] = 'mys'
    
    if d_d['activ_status'] == 'pass_active':
        d_d['activ_status'] = 'pass'
    
    data = {
        'data_id': d_d['dino_id'],
        'alt_id': generation_code(userid),

        'status': 'pass',
        'name': d_d['name'],
        'quality': d_d['quality'],

        'notifications': {},
        'stats': d_d['stats'],
        
        'activ_items': {
                'game': None, 'collecting': None,
                'journey': None, 'sleep': None,
                
                'armor': None,  'weapon': None,
                'backpack': None
        },

        'mood': {
            'breakdown': 0, # очки срыва
            'inspiration': 0 # очки воодушевления
        },

        "memory": {
            'games': [],
            'eat': []
        }
    }
    
    if 'dungeon' in d_d:
        for key, value in d_d['dungeon']['equipment'].items():
            if value:
                data['activ_items'][key] = value
    
    dinosaurs.insert_one(data)
    
    dino = dinosaurs.find_one({'alt_id': data['alt_id']})
    if dino: create_dino_connection(dino['_id'], userid)

def new_user(user_data):
    userid = user_data['userid']
    coins = user_data['coins']
    lvl = user_data['lvl']
    quest_ended = 0
    
    if 'user_dungeon' in user_data:
        if 'quests' in user_data['user_dungeon']:
            quest_ended = user_data['user_dungeon']['quests']['ended']

    if not users.find_one({'userid': userid}):
        data = {
            'userid': int(userid),
            
            'last_message_time': user_data['last_m'],
            'last_markup': 'main_menu',

            'settings': {
                'notifications': True,
                'last_dino': None, 
                'profile_view': 1,
                'inv_view': [2, 3],
                'my_name': ''
            },
            
            'notifications': [],
            'coins': coins,
            'lvl': lvl[0],
            'xp': lvl[1],
            
            'dungeon': { 
                'quest_ended': quest_ended,
                'dungeon_ended': 0
            }
        }
        users.insert_one(data)

        # stfriend = time()
        if user_data['language_code'] not in available_locales: lang = 'en'
        else: lang = user_data['language_code']
        langs.insert_one({'userid': userid, 'lang': lang})

        # Друзья
        for i in user_data['friends']['friends_list']:
            insert_friend_connect(userid, i, 'friends')
        
        for i in user_data['friends']['requests']:
            insert_friend_connect(i, userid, 'request')

            # ПРОВЕРИТЬ ЧТО ПРАВИЛЬНО ПЕРЕНЕСЁТСЯ ЗАПРОС
        
        # print('friends-time', time() - stfriend)
        
        stinv = time()
        for key, value in user_data['activ_items'].items():
            for key1, value1 in value.items():
                if value1:
                    user_data['inventory'].append(value1)
        
        if 'user_dungeon' in user_data:
            for key, value in user_data['user_dungeon']['equipment'].items():
                if value:
                    user_data['inventory'].append(value)

        # Инвентарь
        # for item_data in user_data['inventory']:
        #     new_id = ids[ str(item_data['item_id']) ]
        #     preabil = {}

        #     if 'abilities' in item_data:
        #         for key, value in item_data['abilities'].items():
        #             if value <= 0:
        #                 item_data['abilities'][key] = 1
        #             if 'abilities' in ITEMS[new_id]:
        #                 if value > ITEMS[new_id]['abilities'][key]:
        #                     item_data['abilities'][key] = ITEMS[new_id]['abilities'][key]
        #         preabil = item_data['abilities']

        #     AddItemToUser(userid, new_id, 1, preabil)
            
        
        items_dict = {}
        for item in user_data['inventory']:
            i_qr = item_code(item)

            if i_qr in items_dict.keys():
                items_dict[i_qr]['count'] += 1

            else:
                items_dict[i_qr] = {
                    'owner_id': userid, 
                    'items_data': item, 
                    'count': 1
                    }
        
        for ikey in items_dict:
            item = items_dict[ikey]['items_data']
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
            AddItemToUser(userid, new_id, items_dict[ikey]['count'], preabil)
        
        print('inv-time', time() - stinv)

        # stdino = time()
        # Dino
        for key, dino in user_data['dinos'].items():
            if 'quality' not in dino:
                dino['quality'] = 'com'
            
            if 'status' in dino:
                if dino['status'] == 'dino':
                    new_dino(userid, dino)
                else:
                    incubation_egg(int(dino['egg_id']), userid, 
                        int(dino['incubation_time']),
                        dino['quality']
                        )
        # print('dino-time', time() - stdino)

uss_zero = list(old.find({}))
len_l, a = len(uss_zero), 0

for user in uss_zero:
    a += 1
    print(user['userid'], f'len {a} / {len_l}')
    if 'last_m' in user and int(time()) - int(user['last_m']) >= 4_838_400 and len(user['dinos']) == 0:
        print('-')
    else:
        new_user(user)

