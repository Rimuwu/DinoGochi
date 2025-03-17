import datetime
from datetime import datetime, timezone
from random import choice, randint, uniform
from time import time

from bson.objectid import ObjectId

from bot.dbmanager import mongo_client
from bot.const import DINOS
from bot.const import GAME_SETTINGS as GS
from bot.modules.data_format import random_code, random_quality
from bot.modules.dinosaur.dino_status import check_status, end_skill_activity
from bot.modules.images import create_dino_image, create_egg_image
from bot.modules.items.item import AddItemToUser
from bot.modules.localization import log, get_lang
from bot.modules.notifications import (dino_notification, notification_manager,
                                       user_notification)

from typing import Union

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
incubations = DBconstructor(mongo_client.dinosaur.incubation)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)
states = DBconstructor(mongo_client.dinosaur.states)

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

        self.activ_items = {
                'game': None, 'collecting': None,
                'journey': None, 'sleep': None,

                'armor': None,  'weapon': None,
                'backpack': None
        }

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

    async def create(self, baseid: Union[ObjectId, str, None] = None):
        find_result = await dinosaurs.find_one({"_id": baseid}, comment='create_find_result')
        if not find_result:
            find_result = await dinosaurs.find_one({"alt_id": baseid}, comment='create_find_result1')
        if find_result:
            self.UpdateData(find_result)
        else:
            await dino_owners.delete_one({"dino_id": baseid}, comment='delete_because_not_found')
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

            for key, item in self.activ_items.items():
                if item: await AddItemToUser(owner['owner_id'], item['item_id'], 1)

            if user:
                if await dead_check(owner['owner_id']):
                    way = 'not_independent_dead'
                else: 
                    way = 'independent_dead'
                    await AddItemToUser(user['userid'], 
                                        GS['dead_dino_item'], 1, {'interact': False})

                await user_notification(owner['owner_id'], way, 
                            dino_name=self.name)

        await self.delete()

    async def image(self, profile_view: int=1, custom_url: str=''):
        """Сгенерировать изображение объекта
        """
        age = await self.age()
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

    async def age(self): return await get_age(self._id)

    async def get_owner(self): return await get_owner(self._id)

    async def is_free(self): return await self.status == 'pass'


class Egg:

    def __init__(self):
        """Создание объекта яйца."""

        self._id = ObjectId()
        self.incubation_time = 0
        self.egg_id = 0
        self.owner_id = 0
        self.quality = 'random'
        self.dino_id = 0

    async def create(self, baseid: ObjectId):
        self.UpdateData(await incubations.find_one({"_id": baseid}, comment='Egg_create'))
        return self

    def UpdateData(self, data):
        if data: self.__dict__ = data

    def __str__(self) -> str:
        return f'{self._id} {self.quality}'

    async def update(self, update_data: dict):
        """
        {"$set": {'stats.eat': 12}} - установить
        {"$inc": {'stats.eat': 12}} - добавить
        """
        data = await incubations.update_one({"_id": self._id}, update_data, comment='Egg_update')
        # self.UpdateData(data) #Не получается конвертировать в словарь возвращаемый объект
        return data

    async def delete(self):
        await incubations.delete_one({'_id': self._id}, comment='Egg_delete')

    async def image(self, lang: str='en'):
        """Сгенерировать изображение объекта.
        """
        t_inc = self.remaining_incubation_time()
        return await create_egg_image(egg_id=self.egg_id, rare=self.quality, seconds=t_inc, lang=lang)

    def remaining_incubation_time(self):
        return self.incubation_time - int(time())


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
    
async def incubation_egg(egg_id: int, owner_id: int, inc_time: int=0, quality: str='random', dino_id: int=0):
    """Создание инкубируемого динозавра
    """
    egg = await Egg().create(ObjectId())

    egg.incubation_time = inc_time + int(time())
    egg.egg_id = egg_id
    egg.owner_id = owner_id
    egg.quality = quality
    egg.dino_id = dino_id

    if inc_time == 0: #Стандартное время инкцбации 
        egg.incubation_time = int(time()) + GS['first_dino_time_incub']

    log(prefix='InsertEgg', message=f'owner_id: {owner_id} data: {egg.__dict__}', lvl=0)
    return await incubations.insert_one(egg.__dict__, comment='incubation_egg')

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
    dino = await Dino().create()

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

    return result, dino.alt_id


async def start_game(dino_baseid: ObjectId, duration: int=1800, 
               percent: float=1):
    """Запуск активности "игра". 
       + Изменение статуса динозавра 
    """

    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'game'}, comment='start_game'):
        game = {
            'dino_id': dino_baseid,
            'game_start': int(time()),
            'game_end': int(time()) + duration,
            'game_percent': percent,
            'activity_type': 'game'
        }
        result = await long_activity.insert_one(game, comment='game_task_result')

    return result

async def end_game(dino_id: ObjectId, send_notif: bool=True):
    """Заканчивает игру и отсылает уведомление.
    """
    await long_activity.delete_many({'dino_id': dino_id}, comment='end_game') 

    if send_notif: await dino_notification(dino_id, 'game_end')


async def start_sleep(dino_baseid: ObjectId, s_type: str='long', 
                duration: int=1):
    """Запуск активности "сон". 
       + Изменение статуса динозавра 
    """

    assert s_type in ['long', 'short'], f'Неподходящий аргумент {s_type}'

    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'sleep'}, comment='start_sleep_1'):
        sleep = {
            'dino_id': dino_baseid,
            'sleep_start': int(time()),
            'sleep_type': s_type,
            'activity_type': 'sleep'
        }
        if s_type == 'short':
            sleep['sleep_end'] = int(time()) + duration

        result = await long_activity.insert_one(sleep, comment='start_sleep_2')
    return result

async def end_sleep(dino_id: ObjectId,
                    sec_time: int=0, send_notif: bool=True):
    """Заканчивает сон и отсылает уведомление.
       sec_time - время в секундах, сколько спал дино.
    """
    await long_activity.delete_many({'dino_id': dino_id}, comment='end_sleep_1')
    if send_notif:
        await dino_notification(dino_id, 'sleep_end', 
                            add_time_end=True,
                            secs=sec_time)


async def start_journey(dino_baseid: ObjectId, owner_id: int, 
                  duration: int=1800, location: str = 'forest'):
    """Запуск активности "путешествие". 
       + Изменение статуса динозавра 
    """
    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'journey'}, comment='start_journey'):
        game = {
            'sended': owner_id, # Так как у нас может быть несколько владельцев
            'dino_id': dino_baseid,
            'journey_start': int(time()),
            'journey_end': int(time()) + duration,

            'location': location,
            'journey_log': [], 'items': [],
            'coins': 0,

            'activity_type': 'journey'
        }
        result = await long_activity.insert_one(game, comment='start_journey_result')

    return result

async def end_journey(dino_id: ObjectId):
    data = await long_activity.find_one({'dino_id': dino_id,
            'activity_type': 'journey'}, comment='end_journey_data')
    if data:
        for i in data['items']: 
            await AddItemToUser(data['sended'], i)
        await users.update_one({'userid': data['sended']}, {'$inc': {'coins': data['coins']}}, comment='end_journey')
        log(f"Edit coins: user: {data['sended']} col: {data['coins']}", 0, "take_coins")

        await long_activity.delete_many({'dino_id': dino_id}, comment='end_journey')

async def start_collecting(dino_baseid: ObjectId, owner_id: int, coll_type: str, max_count: int):
    """Запуск активности "сбор пищи". 
       + Изменение статуса динозавра 
    """

    assert coll_type in ['collecting', 'hunt', 'fishing', 'all'], f'Неподходящий аргумент {coll_type}'

    result = False
    if not await long_activity.find_one({'dino_id': dino_baseid,
            'activity_type': 'collecting'}, comment='start_collecting'):
        collecting = {
            'sended': owner_id, # Так как у нас может быть несколько владельцев
            'dino_id': dino_baseid,
            'collecting_type': coll_type,
            'max_count': max_count,
            'now_count': 0,
            'items': {},

            'activity_type': 'collecting'
        }
        result = await long_activity.insert_one(collecting, comment='start_collecting_result')
    return result

async def end_collecting(dino_id: ObjectId, items: dict, recipient: int,
                         items_names: str,
                         send_notif: bool = True):
    """Конец сбора пищи,
       items_name - сгенерированное сообщение для уведолмения
       items - словарь типа {'id': count: int} с предметами для добавления
       recipient - тот кто получит собранные предметы
    """
    await long_activity.delete_many({'dino_id': dino_id}, comment='end_collecting_1')

    for key_id, count in items.items():
        await AddItemToUser(recipient, key_id, count)

    if send_notif:
        await dino_notification(dino_id, 'end_collecting', items_names=items_names)

def edited_stats(before: int, unit: int):
    """ Лёгкая функция проверки на 
        0 <= unit <= 100 
    """
    after = 0
    if before + unit > 100: after = 100
    elif before + unit < 0: after = 0
    else: after = before + unit

    return after

async def get_age(dinoid: ObjectId):
    """.seconds .days
    """
    if type(dinoid) != str:
        dino = await dinosaurs.find_one({'alt_id': dinoid}, comment='get_age')
        if dino: dinoid = dino['_id']

    dino_create = dinoid.generation_time
    now = datetime.now(timezone.utc)
    delta = now - dino_create
    return delta

async def mutate_dino_stat(dino: dict, key: str, value: int):
    st = dino['stats'][key]
    now = st + value
    if now > 100: value = 100 - st
    elif now < 0: value = -st

    if key == 'heal' and now <= 0:
        dino_d = await Dino().create(dino['_id'])
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

async def set_status(dino_id: ObjectId, new_status: str, now_status: str = ''):
    """ НЕ вводит в состояние, лишь отменяет старое. Делает это грубо.
    """

    assert new_status in ['sleep', 'game', 'journey', 'collecting', 'dungeon', 'kindergarten', 'hysteria', 'farm', 'mine', 'bank', 'sawmill', 'gym', 'library', 'park', 'swimming_pool', 'craft', 'unrestrained_play', 'pass'], f'Состояние {new_status} не найдено!'

    if not now_status:
        now_status = await check_status(dino_id)

    if now_status == 'sleep':
        sleeper = await long_activity.find_one({'dino_id': dino_id,
            'activity_type': 'sleep'}, comment='set_status_sleeper')
        if sleeper:
            sleep_time = int(time()) - sleeper['sleep_start']
            await end_sleep(dino_id, sleeper['_id'], sleep_time)

    elif now_status == 'game': await end_game(dino_id)

    elif now_status == 'journey': await end_journey(dino_id)

    elif now_status == 'collecting':
        data = await long_activity.find_one({'dino_id': dino_id,
            'activity_type': 'collecting'}, comment='set_status_data')
        if data:
            items_list = []
            for key, count in data['items'].items(): 
                items_list += [key] * count

            await end_collecting(dino_id, data['items'], 
                                        data['sended'], '', False)

    elif now_status == 'kindergarten':
        data = await kindergarten.find_one({'dinoid': dino_id}, comment='set_status_data')
        if data: await kindergarten.delete_one({'_id': data['_id']}, comment='set_status_1')

    elif now_status == 'craft':

        res = await item_craft.find_one({'dino_id': dino_id})
        if res:
            await dino_notification(dino_id, 'craft_end')
            await item_craft.delete_one({'_id': res['_id']})

        await long_activity.delete_one({
            'dino_id': dino_id,
            'activity_type': 'craft'
        })

    elif now_status in ['gym', 'library', 'park', 'swimming_pool']:
        res = await long_activity.find_one(
        {'dino_id': dino_id})

        if res: 
            traning_time = int(time()) - res['start_time']
            way = ''

            if traning_time < res['min_time']:
                unit_percent = res['up_unit'] / 2

                skill =  res['up_skill']
                await dinosaurs.update_one({'_id': dino_id}, 
                                            {'$inc': {f'stats.{skill}': 
                                                round(-unit_percent)}
                                             })
                way = '_negative'

            await dino_notification(dino_id, res['activity_type'] + '_end' + way)
            await end_skill_activity(dino_id)

    elif now_status in ['bank', 'mine', 'sawmill']:
        res = await long_activity.find_one(
            {'activity_type': {'$in': ['bank', 'mine', 'sawmill']}, 
             'dino_id': dino_id}
        )

        if res:
            await long_activity.delete_one({'_id': res['_id']})
            await dino_notification(dino_id, f'{now_status}_end')



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