import datetime
from datetime import datetime, timedelta, timezone
from random import choice, randint, uniform
from time import time

from bson.objectid import ObjectId

from bot.dbmanager import mongo_client
from bot.const import DINOS, GAME_SETTINGS as GS
from bot.modules.data_format import random_code, random_quality
from bot.modules.dinosaur.dino_status import check_status, end_collecting, end_game, end_journey, end_skill_activity, end_sleep, start_collecting, start_game, start_journey, start_sleep
from bot.modules.images import create_dino_image
from bot.modules.items.item import AddItemToUser, ItemData
from bot.modules.localization import get_lang
from bot.modules.logs import log
from bot.modules.notifications import (dino_notification, notification_manager,
                                       user_notification)

from typing import Union
from bot.modules.egg import *

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.dinocollection import add_to_collection_dino

users = DBconstructor(mongo_client.user.users)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
incubations = DBconstructor(mongo_client.dinosaur.incubation)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)
states = DBconstructor(mongo_client.dinosaur.state)

kindergarten = DBconstructor(mongo_client.dino_activity.kindergarten)
kd_activity = DBconstructor(mongo_client.dino_activity.kd_activity)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
item_craft = DBconstructor(mongo_client.items.item_craft)

class Dino:

    def __init__(self):
        """Создание объекта динозавра."""
        self._id: ObjectId = ObjectId()

        self.data_id = 0
        self.alt_id = 'alt_id' #альтернативный id
        self.age: int = 0 # Время рождения дино в секундах

        self.name = 'name'
        self.quality = 'com'

        self.notifications = {}

        self.stats = {
                'heal': 10, 'eat': 10,
                'game': 10, 'mood': 10,
                'energy': 10,

                'power': 0.0, 'dexterity': 0.0,
                'intelligence': 0.0, 'charisma': 0.0
        }

        # self.activ_items = [
        #     # {'item_id': ..., 'abilities': ...}
        # ] # Запрос активных предметов через инвентарь с типом аксессуар

        self.mood = {
            'breakdown': 0, # очки срыва
            'inspiration': 0 # очки воодушевления
        }

        self.memory = {
            'games': [],
            'eat': [],
            'action': []
        }

        self.profile = {
            'background_type': 'standart',
            'background_id': 0
        }

        self.location = {
            'island': 'default_island',
            'x': 0, 'y': 0,
            'percent': 50 # 0-100
        }

    async def create(self, baseid: Union[ObjectId, str, None] = None):
        find_result = await dinosaurs.find_one({"_id": baseid}, comment='create_find_result')
        if not find_result:
            find_result = await dinosaurs.find_one({"alt_id": baseid}, comment='create_find_result1')
        if find_result:
            self.UpdateData(find_result)
        else:
            await dino_owners.delete_one({"dino_id": baseid}, comment='delete_because_not_found')
            return None
        return self

    def UpdateData(self, data):
        if data: self.__dict__ = data

    def __str__(self) -> str:
        return self.name

    async def update(self, update_data: dict):
        """
        {"$set": {'stats.eat': 12}} - установить
        {"$inc": {'stats.eat': 12}} - добавить
        """
        data = await dinosaurs.update_one({"_id": self._id}, update_data, comment='Dino_update_data')
        # self.UpdateData(data) #Не получается конвертировать в словарь возвращаемый объект
        self.UpdateData(await dinosaurs.find_one({"alt_id": self._id}, comment='Dino_update'))
        if self.stats['heal'] <= 0: await self.dead()

        return data

    async def delete(self):
        """ Удаление всего, что связано с дино
        """
        await dinosaurs.delete_one({'_id': self._id}, comment='Dino_delete')
        for collection in [kd_activity, long_activity, dino_owners, dino_mood, kindergarten, states]:
            await collection.delete_many({'dino_id': self._id}, comment='delete_213')

    async def dead(self):
        """ Это очень грустно, но необходимо...
            Удаляем объект динозавра, отсылает уведомление и сохраняет динозавра в мёртвых
        """
        owner = await self.get_owner()

        if owner:
            user = await users.find_one({"userid": owner['owner_id']}, comment='dead_find_user')
            await users.update_one({"userid": owner['owner_id']}, {'$set': {'settings.last_dino': None}}, comment='dead_last_dino_none')

            save_data = {
                'data_id': self.data_id,
                'quality': self.quality,
                'name': self.name,
                'owner_id': owner['owner_id'],
                'stats': {
                    'charisma': self.stats['charisma'],
                    'intelligence': self.stats['intelligence'],
                    'dexterity': self.stats['dexterity'],
                    'power': self.stats['power'],
                }
            }
            await dead_dinos.insert_one(save_data, comment='dead')

            # for item in self.activ_items:
            #     if item: 
            #         await AddItemToUser(owner['owner_id'], item['item_id'], 1, item.get('abilities', {}))

            if user:
                if await dead_check(owner['owner_id']):
                    way = 'not_independent_dead'
                else: 
                    way = 'independent_dead'
                    item = ItemData(GS['dead_dialog_item'], {'interact': False})
                    await AddItemToUser(user['userid'], 
                                        item, 1)

                await user_notification(owner['owner_id'], way, 
                            dino_name=self.name)

        await self.delete()

    async def image(self, profile_view: int=1, custom_url: str=''):
        """Сгенерировать изображение объекта
        """
        age = await self.get_age()
        return await create_dino_image(self.data_id, self.stats, self.quality, profile_view, age.days, custom_url)

    async def collecting(self, owner_id: int, coll_type: str, max_count: int):
        return await start_collecting(self._id, owner_id, coll_type, max_count)

    async def game(self, duration: int=1800, percent: float=1.0):
        return await start_game(self._id, duration, percent)

    async def journey(self, owner_id: int, duration: int=1800):
        return await start_journey(self._id, owner_id, duration)

    async def sleep(self, s_type: str='long', duration: int=1):
        return await start_sleep(self._id, s_type, duration)

    async def memory_percent(self, memory_type: str, obj: str, update: bool = True):
        """memory_type - games / eat
        
           Сохраняет в памяти объект и выдаёт процент.
           Сохраняет только при update = True
        """
        repeat = self.memory[memory_type].count(obj)
        percent = GS['penalties'][memory_type][str(repeat)]

        if update:
            max_repeat = {'games': 3, 'eat': 5, 'action': 8}
            # При повторении активностей добавлять -1 к настроению 
            # "Занимаюсь одним и тем же"
            # Записывать активность как = путешествие.локация

            if len(self.memory[memory_type]) < max_repeat[memory_type]:
                await self.update({'$push': {f'memory.{memory_type}': obj}})
            else:
                self.memory[memory_type].pop()
                self.memory[memory_type].insert(0, obj)
                await self.update({'$set': 
                    {f'memory.{memory_type}': self.memory[memory_type]}}
                            )

        return percent, repeat

    @property
    def data(self): return get_dino_data(self.data_id)

    @property
    async def status(self): return await check_status(self) #type: ignore

    async def get_age(self): return await get_age(self._id)

    async def get_owner(self): return await get_owner(self._id)

    async def is_free(self): return await self.status == 'pass'

def get_dino_data(data_id: int):
    data = {}
    try:
        data = DINOS['elements'][str(data_id)]
    except Exception as e:
        log(f'Ошибка в получении данных динозавра -> {e}', 3)
    return data

def random_dino(quality: str='com') -> int:
    """Рандомизация динозавра по редкости
    """
    return choice(DINOS[quality])

async def create_dino_connection(dino_baseid: ObjectId, owner_id: int, con_type: str='owner'):
    """ Создаёт связь в базе между пользователем и динозавром
        con_type = owner / add_owner
    """

    assert con_type in ['owner', 'add_owner'], f'Неподходящий аргумент {con_type}'

    con = {
        'dino_id': dino_baseid,
        'owner_id': owner_id,
        'type': con_type
    }

    log(prefix='CreateConnection', 
        message=f'Dino - Owner Data: {con}', 
        lvl=0)
    return await dino_owners.insert_one(con, comment='create_dino_connection')

async def generation_code(owner_id: int):
    code = f'{owner_id}_{random_code(8)}'
    if await dinosaurs.find_one({'alt_id': code}, comment='generation_code for dino'):
        code = generation_code(owner_id)
    return code

async def insert_dino(owner_id: int=0, dino_id: int=0, quality: str='random'):
    """Создания динозавра в базе
       + связь с владельцем если передан owner_id 
    """

    if quality in ['random', 'ran']: quality = random_quality()
    if not dino_id: dino_id = random_dino(quality)

    dino_data = get_dino_data(dino_id)
    dino = Dino()

    dino.data_id = dino_id
    dino.alt_id = await generation_code(owner_id)

    dino.name = dino_data['name']
    dino.quality = quality or dino_data['quality']

    power, dexterity, intelligence, charisma = set_standart_specifications(dino_data['class'], dino.quality)

    dino.stats = {
        'heal': 100, 'eat': randint(70, 100),
        'game': randint(30, 90), 'mood': randint(30, 100),
        'energy': randint(80, 100),

        'power': power, 'dexterity': dexterity,
        'intelligence': intelligence, 'charisma': charisma
        }

    log(prefix='InsertDino', 
        message=f'owner_id: {owner_id} dino_id: {dino_id} name: {dino.name} quality: {dino.quality}', 
        lvl=0)
    result = await dinosaurs.insert_one(dino.__dict__, comment='insert_dino_result')
    if owner_id != 0:
        # Создание связи, если передан id владельца
        await create_dino_connection(result.inserted_id, owner_id)
    
    await add_to_collection_dino(owner_id, dino_id)
    return result, dino.alt_id

def edited_stats(before: int, unit: int):
    """ Лёгкая функция проверки на 
        0 <= unit <= 100 
    """
    after = 0
    if before + unit > 100: after = 100
    elif before + unit < 0: after = 0
    else: after = before + unit

    return after

async def get_age(dinoid: ObjectId | str) -> timedelta:
    """.seconds .days
    """
    if isinstance(dinoid, str):
        dino = await dinosaurs.find_one({'alt_id': dinoid}, comment='get_age')
        if not dino: return timedelta(days=0)

    elif isinstance(dinoid, ObjectId):
        dino = await dinosaurs.find_one({'_id': dinoid}, comment='get_age')
        if not dino: return timedelta(days=0)

    time_born: int = dino['age']
    time_now: int = int(datetime.now().timestamp())
    return timedelta(seconds=(time_now - time_born))

async def mutate_dino_stat(dino: dict, key: str, value: int):
    st = dino['stats'][key]
    now = st + value
    if now > 100: value = 100 - st
    elif now < 0: value = -st

    if key == 'heal' and now <= 0:
        dino_d = await Dino().create(dino['_id'])
        if dino_d:
            await dino_d.dead()
    else:
        r = await notification_manager(dino['_id'], key, now)
        await dinosaurs.update_one({'_id': dino['_id']}, 
                            {'$inc': {f'stats.{key}': value}}, comment='mutate_dino_stat')
        return r
    return 0

async def get_owner(dino_id: ObjectId):
    return await dino_owners.find_one({'dino_id': dino_id, 'type': 'owner'}, comment='get_owner')

async def get_dino_language(dino_id: ObjectId) -> str:
    lang = 'en'

    owner = await dino_owners.find_one({'dino_id': dino_id}, comment='get_dino_language')
    if owner: lang = await get_lang(owner['owner_id'])
    return lang

async def dead_check(userid: int):
    """ False - не соответствует условиям выдачи диалога
        True - отправить диалог
    """
    user = await users.find_one({"userid": userid}, comment='dead_check')
    if user:
        col_dinos = await dino_owners.find_one(
                        {'onwer_id': userid, 'type': 'owner'}, comment='dead_check')
        col_eggs = await incubations.find_one({'onwer_id': userid}, comment='dead_check_1')
        lvl = user['lvl'] <= GS['dead_dialog_max_lvl']

        if all([not col_dinos, not col_eggs, lvl]): return True
    return False

quality_spec = {
    'com': [0, 1],
    'unc': [0, 2],
    'rar': [0, 3],
    'mys': [0, 4], 
    'leg': [0, 5]
}

def set_standart_specifications(dino_type: str, dino_quality: str):

    """
    return power, dexterity, intelligence, charisma
    """

    power = 0
    dexterity = 0 # Ловкость
    intelligence = 0
    charisma = 0

    power = round(uniform( *quality_spec[dino_quality] ), 4)
    dexterity = round(uniform( *quality_spec[dino_quality] ), 4)
    intelligence = round(uniform( *quality_spec[dino_quality] ), 4)
    charisma = round(uniform( *quality_spec[dino_quality] ), 4)

    if dino_type == 'Herbivore':
        charisma += round(uniform( *quality_spec[dino_quality] ), 4)

    elif dino_type == 'Carnivore':
        power += round(uniform( *quality_spec[dino_quality] ), 4)

    elif dino_type == 'Flying':
        dexterity += round(uniform( *quality_spec[dino_quality] ), 4)

    return round(power, 4), round(dexterity, 4), round(intelligence, 4), round(charisma, 4)