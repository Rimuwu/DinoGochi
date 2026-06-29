from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import User
from bot.models.dinosaur import DeadDino, Dino, DinoMood, DinoOwners, Egg, State
from bot.models.activity import Activity, KDActivity, Kindergarten
from bot.models.items import ItemCraft
import datetime
from datetime import datetime, timezone
from random import choice, randint, sample, uniform
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

from bot.modules.user.dinocollection import add_to_collection_dino
users = LazyCollection(User)
dinosaurs = LazyCollection(Dino)
incubations = LazyCollection(Egg)
dino_owners = LazyCollection(DinoOwners)
dead_dinos = LazyCollection(DeadDino)
dino_mood = LazyCollection(DinoMood)
states = LazyCollection(State)

kindergarten = LazyCollection(Kindergarten)
kd_activity = LazyCollection(KDActivity)
long_activity = LazyCollection(Activity)
item_craft = LazyCollection(ItemCraft)

from bot.models.dinosaur import Dino, Egg

def Dino.get_dino_data(data_id: int):
    data = {}
    try:
        data = DINOS['elements'][str(data_id)]
    except Exception as e:
        log(f'Ошибка в получении данных динозавра -> {e}', 3)
    return data

def Dino.random_dino(quality: str='com') -> int:
    """Рандомизация динозавра по редкости
    """
    return choice(DINOS[quality])

async def await Egg.incubation(egg_id: int, owner_id: int, 
                         inc_time: int=0, quality: str='random', 
                         dino_id: int=0):
    """Создание инкубируемого динозавра"""
    from bot.models.dinosaur import Egg
    
    egg = await Egg.find_one(
        Egg.owner_id == owner_id, 
        Egg.stage == 'choosing',
        Egg.quality == quality
    )

    if not egg:
        log(prefix='InsertEgg ERROR', message=f'owner_id: {owner_id} data: None', lvl=0)
        return None

    egg.incubation_time = inc_time + int(time())
    egg.egg_id = egg_id
    egg.owner_id = owner_id
    egg.quality = quality

    if not dino_id:
        egg.dino_id = egg.dinos[egg.eggs.index(egg_id)]
    else:
        egg.dino_id = dino_id

    if inc_time == 0:
        egg.incubation_time = int(time()) + GS['first_dino_time_incub']

    egg.stage = 'incubation'

    log(prefix='InsertEgg', 
        message=f'owner_id: {owner_id} data: {egg.__dict__}', lvl=0)
    
    await Egg.find_one(Egg.id == egg.id).update({
        '$set': {
            'incubation_time': egg.incubation_time,
            'egg_id': egg.egg_id,
            'owner_id': egg.owner_id,
            'quality': egg.quality,
            'dino_id': egg.dino_id,
            'stage': egg.stage
        },
        '$unset': {
            'id_message': 1,
            'eggs': 1,
            'dinos': 1,
            'start_choosing': 1
        }
    })
    return True

async def await DinoOwners.create_connection(dino_baseid: ObjectId, owner_id: int, con_type: str='owner'):
    """ Создаёт связь в базе между пользователем и динозавром
        con_type = owner / add_owner
    """
    from bot.models.dinosaur import DinoOwners
    assert con_type in ['owner', 'add_owner'], f'Неподходящий аргумент {con_type}'

    con = DinoOwners(
        dino_id=str(dino_baseid),
        owner_id=owner_id,
        type=con_type
    )

    log(prefix='CreateConnection', 
        message=f'Dino - Owner Data: {con}', 
        lvl=0)
    return await con.insert()

async def generation_code(owner_id: int):
    from bot.models.dinosaur import Dino
    code = f'{owner_id}_{random_code(8)}'
    if await Dino.find_one(Dino.alt_id == code):
        code = await generation_code(owner_id)
    return code

async def await Dino.insert_dino(owner_id: int=0, dino_id: int=0, quality: str='random'):
    """Создания динозавра в базе
       + связь с владельцем если передан owner_id 
    """
    from bot.models.dinosaur import Dino

    if quality in ['random', 'ran']: quality = random_quality()
    if not dino_id: dino_id = Dino.random_dino(quality)

    dino_data = Dino.get_dino_data(dino_id)
    dino = Dino(
        data_id=dino_id,
        alt_id=await generation_code(owner_id),
        name=dino_data['name'],
        quality=quality or dino_data['quality']
    )

    power, dexterity, intelligence, charisma = Dino.set_standart_specifications(dino_data['class'], dino.quality)

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
    
    await dino.insert()
    if owner_id != 0:
        await DinoOwners.create_connection(dino.id, owner_id)
    
    await add_to_collection_dino(owner_id, dino_id)
    return dino, dino.alt_id


async def await GameActivity.start(dino_baseid: ObjectId, duration: int=1800, 
               percent: float=1):
    """Запуск активности "игра". 
       + Изменение статуса динозавра 
    """
    from bot.models.activity import LongActivity

    result = False
    existing = await LongActivity.find_one(
        LongActivity.dino_id == str(dino_baseid),
        LongActivity.activity_type == 'game'
    )
    if not existing:
        game = LongActivity(
            dino_id=str(dino_baseid),
            start_time=int(time()),
            end_time=int(time()) + duration,
            activity_type='game',
            data={'game_percent': percent}
        )
        await game.insert()
        result = True

    return result

async def await GameActivity.end(dino_id: ObjectId, send_notif: bool=True):
    """Заканчивает игру и отсылает уведомление."""
    from bot.models.activity import LongActivity
    await LongActivity.find(LongActivity.dino_id == str(dino_id), LongActivity.activity_type == 'game').delete()

    if send_notif: await dino_notification(dino_id, 'game_end')


async def await SleepActivity.start(dino_baseid: ObjectId, s_type: str='long', 
                duration: int=1):
    """Запуск активности "сон". 
       + Изменение статуса динозавра 
    """
    from bot.models.activity import LongActivity

    assert s_type in ['long', 'short'], f'Неподходящий аргумент {s_type}'

    result = False
    existing = await LongActivity.find_one(
        LongActivity.dino_id == str(dino_baseid),
        LongActivity.activity_type == 'sleep'
    )
    if not existing:
        end_time = int(time()) + duration if s_type == 'short' else int(time()) + 86400 * 365
        sleep = LongActivity(
            dino_id=str(dino_baseid),
            start_time=int(time()),
            end_time=end_time,
            activity_type='sleep',
            data={'sleep_type': s_type}
        )
        await sleep.insert()
        result = True
    return result

async def await SleepActivity.end(dino_id: ObjectId,
                    sec_time: int=0, send_notif: bool=True):
    """Заканчивает сон и отсылает уведомление.
       sec_time - время в секундах, сколько спал дино.
    """
    from bot.models.activity import LongActivity
    await LongActivity.find(LongActivity.dino_id == str(dino_id), LongActivity.activity_type == 'sleep').delete()
    if send_notif:
        await dino_notification(dino_id, 'sleep_end', 
                            add_time_end=True,
                            secs=sec_time)


async def JourneyActivity.start(dino_baseid: ObjectId, owner_id: int, 
                  duration: int=1800, location: str = 'forest'):
    """Запуск активности "путешествие". 
       + Изменение статуса динозавра 
    """
    from bot.models.activity import LongActivity

    result = False
    existing = await LongActivity.find_one(
        LongActivity.dino_id == str(dino_baseid),
        LongActivity.activity_type == 'journey'
    )
    if not existing:
        journey = LongActivity(
            dino_id=str(dino_baseid),
            start_time=int(time()),
            end_time=int(time()) + duration,
            activity_type='journey',
            data={
                'sended': owner_id,
                'location': location,
                'journey_log': [],
                'items': [],
                'coins': 0
            }
        )
        await journey.insert()
        result = True

    return result

async def await JourneyActivity.end(dino_id: ObjectId):
    from bot.models.activity import LongActivity
    from bot.models.user import User
    from bot.modules.items.item import AddItemToUser

    data = await LongActivity.find_one(
        LongActivity.dino_id == str(dino_id),
        LongActivity.activity_type == 'journey'
    )
    if data and data.data:
        sended_user = data.data.get('sended')
        for i in data.data.get('items', []): 
            await AddItemToUser(sended_user, i)
        
        user_doc = await User.find_one(User.userid == sended_user)
        if user_doc:
            user_doc.coins += data.data.get('coins', 0)
            await user_doc.save()
            
        log(f"Edit coins: user: {sended_user} col: {data.data.get('coins', 0)}", 0, "take_coins")

        await data.delete()

async def CollectingActivity.start(dino_baseid: ObjectId, owner_id: int, coll_type: str, max_count: int):
    """Запуск активности "сбор пищи". 
       + Изменение статуса динозавра 
    """
    from bot.models.activity import LongActivity

    assert coll_type in ['collecting', 'hunt', 'fishing', 'all'], f'Неподходящий аргумент {coll_type}'

    result = False
    existing = await LongActivity.find_one(
        LongActivity.dino_id == str(dino_baseid),
        LongActivity.activity_type == 'collecting'
    )
    if not existing:
        collecting = LongActivity(
            dino_id=str(dino_baseid),
            start_time=int(time()),
            end_time=int(time()) + 86400 * 365,
            activity_type='collecting',
            data={
                'sended': owner_id,
                'collecting_type': coll_type,
                'max_count': max_count,
                'now_count': 0,
                'items': {}
            }
        )
        await collecting.insert()
        result = True
    return result

async def await CollectingActivity.end(dino_id: ObjectId, items: dict, recipient: int,
                         items_names: str,
                         send_notif: bool = True):
    """Конец сбора пищи"""
    from bot.models.activity import LongActivity
    await LongActivity.find(LongActivity.dino_id == str(dino_id), LongActivity.activity_type == 'collecting').delete()

    for key_id, count in items.items():
        await AddItemToUser(recipient, key_id, count)

    if send_notif:
        await dino_notification(dino_id, 'end_collecting', items_names=items_names)

def Dino.edited_stats(before: int, unit: int):
    """ Лёгкая функция проверки на 
        0 <= unit <= 100 
    """
    after = 0
    if before + unit > 100: after = 100
    elif before + unit < 0: after = 0
    else: after = before + unit

    return after

async def get_age(dinoid: ObjectId):
    from bot.models.dinosaur import Dino
    if isinstance(dinoid, str):
        dino = await Dino.find_one(Dino.alt_id == dinoid)
        if dino: dinoid = dino.id

    dino_create = ObjectId(dinoid).generation_time
    now = datetime.now(timezone.utc)
    delta = now - dino_create
    return delta

async def await Dino.mutate_stat(dino: dict, key: str, value: int):
    from bot.models.dinosaur import Dino
    st = dino['stats'][key]
    now = st + value
    if now > 100: value = 100 - st
    elif now < 0: value = -st

    if key == 'heal' and now <= 0:
        dino_d = await Dino.find_one(Dino.id == ObjectId(dino['_id']))
        if not dino_d:
            dino_d = await Dino.find_one(Dino.alt_id == str(dino['_id']))
        if dino_d:
            await dino_d.dead()
    else:
        r = await notification_manager(dino['_id'], key, now)
        await Dino.find_one(Dino.id == ObjectId(dino['_id'])).update({'$inc': {f'stats.{key}': value}})
        return r
    return 0

async def Dino.get_owner_by_id(dino_id: ObjectId):
    from bot.models.dinosaur import DinoOwners
    return await DinoOwners.find_one(DinoOwners.dino_id == str(dino_id), DinoOwners.type == 'owner')

async def Dino.get_language(dino_id: ObjectId) -> str:
    from bot.models.dinosaur import DinoOwners
    lang = 'en'

    owner = await DinoOwners.find_one(DinoOwners.dino_id == str(dino_id))
    if owner: lang = await get_lang(owner.owner_id)
    return lang

async def Dino.dead_check(userid: int):
    from bot.models.user import User
    from bot.models.dinosaur import DinoOwners, Egg
    
    user = await User.find_one(User.userid == userid)
    if user:
        col_dinos = await DinoOwners.find_one(
                        DinoOwners.owner_id == userid, DinoOwners.type == 'owner')
        col_eggs = await Egg.find_one(Egg.owner_id == userid)
        lvl = user.lvl <= GS['dead_dialog_max_lvl']

        if all([not col_dinos, not col_eggs, lvl]): return True
    return False

async def set_status(dino_id: ObjectId, new_status: str, now_status: str = ''):
    from bot.models.activity import LongActivity, Kindergarten
    from bot.models.items import ItemCraft
    
    assert new_status in ['sleep', 'game', 'journey', 'collecting', 'dungeon', 'kindergarten', 'hysteria', 'farm', 'mine', 'bank', 'sawmill', 'gym', 'library', 'park', 'swimming_pool', 'craft', 'unrestrained_play', 'pass'], f'Состояние {new_status} не найдено!'
    
    if not now_status:
        now_status = await check_status(dino_id)

    if now_status == 'sleep':
        sleeper = await LongActivity.find_one(
            LongActivity.dino_id == str(dino_id),
            LongActivity.activity_type == 'sleep'
        )
        if sleeper:
            sleep_time = int(time()) - sleeper.start_time
            await SleepActivity.end(dino_id, sleep_time)

    elif now_status == 'game': await GameActivity.end(dino_id)

    elif now_status == 'journey': await JourneyActivity.end(dino_id)

    elif now_status == 'collecting':
        data = await LongActivity.find_one(
            LongActivity.dino_id == str(dino_id),
            LongActivity.activity_type == 'collecting'
        )
        if data and data.data:
            items_dict = data.data.get('items', {})
            sended_user = data.data.get('sended')
            await CollectingActivity.end(dino_id, items_dict, sended_user, '', False)

    elif now_status == 'kindergarten':
        kg = await Kindergarten.find_one(Kindergarten.dinos.contains(str(dino_id)))
        if kg:
            kg.dinos.remove(str(dino_id))
            if not kg.dinos:
                await kg.delete()
            else:
                await kg.save()

    elif now_status == 'craft':
        res = await ItemCraft.find_one(ItemCraft.dino_id == str(dino_id))
        if res:
            await dino_notification(dino_id, 'craft_end')
            await res.delete()

        await LongActivity.find(
            LongActivity.dino_id == str(dino_id),
            LongActivity.activity_type == 'craft'
        ).delete()

    elif now_status in ['gym', 'library', 'park', 'swimming_pool']:
        res = await LongActivity.find_one(LongActivity.dino_id == str(dino_id))

        if res and res.data: 
            traning_time = int(time()) - res.start_time
            way = ''

            min_time = res.data.get('min_time', 0)
            up_unit = res.data.get('up_unit', 0)
            up_skill = res.data.get('up_skill', '')

            if traning_time < min_time:
                unit_percent = up_unit / 2

                from bot.models.dinosaur import Dino
                await Dino.find_one(Dino.id == dino_id).update({
                    '$inc': {f'stats.{up_skill}': round(-unit_percent)}
                })
                way = '_negative'

            await dino_notification(dino_id, res.activity_type + '_end' + way)
            await end_skill_activity(dino_id)

    elif now_status in ['bank', 'mine', 'sawmill']:
        res = await LongActivity.find_one(
            LongActivity.dino_id == str(dino_id),
            LongActivity.activity_type.in_(['bank', 'mine', 'sawmill'])
        )

        if res:
            await res.delete()
            await dino_notification(dino_id, f'{now_status}_end')



quality_spec = {
    'com': [0, 1],
    'unc': [0, 2],
    'rar': [0, 3],
    'mys': [0, 4], 
    'leg': [0, 5]
}

def Dino.set_standart_specifications(dino_type: str, dino_quality: str):

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