from random import choice
from time import time

from telebot.types import User as teleUser

from bot.config import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, seconds_to_str, user_name
from bot.modules.dinosaur.dinosaur import Dino, Egg
from bot.modules.user.friends import get_frineds
from bot.modules.items.item import AddItemToUser
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_name
from bot.modules.localization import get_data, t, get_lang, available_locales
from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.modules.managment.referals import get_code_owner, get_user_sub
from datetime import datetime, timedelta


from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
items = DBconstructor(mongo_client.items.items)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
products = DBconstructor(mongo_client.market.products)
sellers = DBconstructor(mongo_client.market.sellers)
puhs = DBconstructor(mongo_client.market.puhs)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
tavern = DBconstructor(mongo_client.tavern.tavern)

incubations = DBconstructor(mongo_client.dinosaur.incubation)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
friends = DBconstructor(mongo_client.user.friends)
subscriptions = DBconstructor(mongo_client.user.subscriptions)
referals = DBconstructor(mongo_client.user.referals)
daily_award_data = DBconstructor(mongo_client.tavern.daily_award)
langs = DBconstructor(mongo_client.user.lang)
ads = DBconstructor(mongo_client.user.ads)
dead_users = DBconstructor(mongo_client.other.dead_users)

class User:

    def __init__(self):
        """Создание объекта пользователя
        """
        self.userid = 0

        self.last_message_time = 0
        self.last_markup = 'main_menu'

        self.settings = {
            'notifications': True,
            'last_dino': None, #храним ObjectId
            'profile_view': 1,
            'inv_view': [2, 3],
            'my_name': '' # Как вас называет динозавр
            }

        self.notifications = {}

        self.coins = 100
        self.super_coins = 0

        self.lvl = 0
        self.xp = 0

        self.dungeon = { 
            'quest_ended': 0,
            'dungeon_ended': 0
        }

        self.saved = {
            'backgrounds': []
        }

    async def create(self, userid: int):
        self.userid = userid
        data = await users.find_one({"userid": userid}, comment='User_create')
        self.UpdateData(data) #Обновление данных
        return self

    def UpdateData(self, data):
        if data: self.__dict__ = data

    async def get_dinos(self, all_dinos: bool=True) -> list[Dino]:
        """Возвращает список с объектами динозавров.
           all_dinos - Если False то не запросит совместных динозавров 
        """
        dino_list = await get_dinos(self.userid, all_dinos)
        self.dinos = dino_list
        return dino_list

    @property
    async def get_col_dinos(self) -> int:
        col = await col_dinos(self.userid)
        self.col_dinos = col
        return col

    @property
    async def get_eggs(self) -> list:
        """Возвращает список с объектами динозавров."""
        eggs_list = await get_eggs(self.userid)
        self.eggs = eggs_list
        return eggs_list

    async def get_inventory(self, exclude_ids: list=[]):
        """Возвращает список с предметами в инвентаре"""
        inv, count = await get_inventory(self.userid, exclude_ids)
        self.inventory = inv
        return inv, count

    @property
    async def get_friends(self) -> dict:
        """Возвращает словарь с 2 видами связей
           friends - уже друзья
           requests - запрос на добавление
        """
        friends_dict = await get_frineds(self.userid)
        self.friends = friends_dict
        return friends_dict

    @property
    async def premium(self) -> bool: return await premium(self.userid)

    @property
    async def lang(self) -> str: return await get_lang(self.userid)

    def view(self):
        """ Отображает все данные объекта."""

        print(f'userid: {self.userid}')
        print(f'DATA: {self.__dict__}')

    async def update(self, update_data) -> None:
        """
        {"$set": {'coins': 12}} - установить
        {"$inc": {'coins': 12}} - добавить
        """
        data = await users.update_one({"userid": self.userid}, update_data, comment='User_update')
        # self.UpdateData(data) #Не получается конвертировать в словарь возвращаемый объект

    async def full_delete(self):
        """Удаление юзера и всё с ним связанное из базы.
        """

        for collection in [items, products, dead_dinos, incubations, sellers, puhs, daily_award_data]:
            await collection.delete_many({'owner_id': self.userid}, comment='User_full_delete')

        for collection in [referals, langs, ads, dead_users, subscriptions, tavern, dead_users]:
            await collection.delete_many({'userid': self.userid}, comment='User_full_delete_1')

        """ При полном удалении есть возможность, что у динозавра
            есть другие владельцы, значит мы должны передать им полные права
            или наобраот удалить, чтобы не остался пустой динозавр
        """
        #запрашиваем все связи с владельцем
        dinos_conn = await dino_owners.find(
            {'owner_id': self.userid}, comment='full_delete_dinos_conn')
        for conn in dinos_conn:
            #Если он главный
            if conn['type'] == 'owner':
                #Запрашиваем всех владельцев динозавра (тут уже не будет главного)
                alt_conn_fo_dino = await dino_owners.find(
                    {'dino_id': conn['dino_id'], 'type': 'add_owner'}, comment='full_delete_230'
                        )

                #Проверяем, пустой ли список
                if len(alt_conn_fo_dino) > 1:
                    #Связь с кем то есть, ищем первого попавшегося и делаем главным
                    await dino_owners.update_one({'dino_id': conn['dino_id']}, 
                                                 {'$set': {'type': 'owner'}}, comment='full_delete_1')
                else:
                    # Если пустой, то удаляем динозавра (связи уже нет)
                    dino_d = await Dino().create(conn['dino_id'])
                    await dino_d.delete()

            #Удаляем его связь
            await dino_owners.delete_one({'_id': conn['_id']}, comment='full_delete_2')

        # Удаление связи с друзьями
        friends_conn = await friends.find(
            {'userid': self.userid}, comment='full_delete_friends_conn')
        friends_conn2 = await friends.find(
            {'friendid': self.userid}, comment='full_delete_friends_conn2')

        for conn in [friends_conn, friends_conn2]:
            for obj in conn: await friends.delete_one({'_id': obj['_id']}, comment='full_delete_conn')

        # Удаляем юзера
        await self.delete()

    async def delete(self):
        """Удаление юзера из базы.
        """
        await users.delete_one({'userid': self.userid}, comment='User_delete')
        log(f'Удаление {self.userid} из базы.', 0)

    async def get_last_dino(self) -> Dino:
        """Возвращает последнего динозавра или None
        """
        return await last_dino(self) # type: ignore

    async def max_dino_col(self):
        """Возвращает доступное количесвто динозавров, беря во внимание уровень и статус,
           считает сколько динозавров у юзера вместе с лимитом
           {
             'standart': { 'now': 0, 'limit': 0},
             'additional': {'now': 0, 'limit': 1}
            }
        """
        return await max_dino_col(self.lvl, self.userid, await self.premium)


async def insert_user(userid: int, lang: str):
    """Создание пользователя"""
    log(prefix='InsertUser', message=f'User: {userid}', lvl=0)

    if not await users.find_one({'userid': userid}, comment='insert_user'):
        if lang not in available_locales: lang = 'en'
        await langs.insert_one({'userid': userid, 'lang': lang}, comment='insert_user_1')

        user = await User().create(userid)
        return await users.insert_one(user.__dict__, comment='insert_user')

async def get_dinos(userid: int, all_dinos: bool = True) -> list[Dino]:
    """Возвращает список с объектами динозавров."""
    dino_list = []

    if all_dinos:
        res = await dino_owners.find({'owner_id': userid}, 
                                          {'dino_id': 1}, comment='get_dinos_res')
    else:
        res = await dino_owners.find(
            {'owner_id': userid, 'type': 'owner'}, {'dino_id': 1}, comment='get_dinos_res')

    for dino_obj in res:
        dino_list.append(await Dino().create(dino_obj['dino_id']))

    return dino_list

async def get_dinos_and_owners(userid: int) -> list:
    """Возвращает список с объектами динозавров, а так же правами на динозавра"""
    data = []
    for dino_obj in await dino_owners.find({'owner_id': userid}, comment='get_dinos_and_owners'):
        data.append({'dino': await Dino().create(dino_obj['dino_id']), 'owner_type': dino_obj['type']})

    return data

async def col_dinos(userid: int) -> int:
    return len(list(
        await dino_owners.find({'owner_id': userid}, {'_id': 1}, comment='col_dinos')))

async def get_eggs(userid: int) -> list:
    """Возвращает список с объектами динозавров."""
    eggs_list = []
    for egg in await incubations.find({'owner_id': userid}, comment='get_eggs'):
        eggs_list.append(await Egg().create(egg['_id']))

    return eggs_list

async def get_inventory(userid: int, exclude_ids: list = []):
    inv, count = [], 0
    data_inv = await items.find({'owner_id': userid}, 
                                {'_id': 0, 'owner_id': 0}, comment='get_inventory')
    for item_dict in data_inv:
        if item_dict['items_data']['item_id'] not in exclude_ids:
            item = {
                'item': item_dict['items_data'], 
                "count": item_dict['count']
                }
            inv.append(item)
            count += item_dict['count']
    return inv, count

async def items_count(userid: int):
    return len(list(await items.find({'owner_id': userid}, {'_id': 1}, comment='items_count')))

async def last_dino(user: User):
    """Возвращает последнего выбранного динозавра.
       Если None - вернёт первого
       Если нет динозавров - None
    """
    last_dino = user.settings['last_dino']
    if last_dino:
        dino_data = await dinosaurs.find_one({'_id': last_dino}, {"_id": 1}, comment='last_dino')
        if dino_data:
            return await Dino().create(dino_data['_id'])
        else:
            await user.update({'$set': {'settings.last_dino': None}})
            return await last_dino(user)
    else:
        dino_lst = await user.get_dinos()
        if dino_lst:
            dino = dino_lst[0]
            await user.update({'$set': {'settings.last_dino': dino._id}})
            return dino
        else:
            await user.update({'$set': {'settings.last_dino': None}})
            return None

async def award_premium(userid:int, end_time):
    """
    Присуждение премиум статуса юзеру
    {
        'userid': int,
        'sub_start': int,
        'sub_end': int | str (inf),
        'end_notif': bool (отправлено ли уведомление о окончании подписки)
    }
    """
    user_doc = await subscriptions.find_one({'userid': userid}, comment='award_premium_user_doc')
    if user_doc:
        if type(user_doc['sub_end']) == str and type(end_time) == int:
            user_doc['sub_end'] = int(time()) + end_time
        elif type(end_time) == str:
            user_doc['sub_end'] = end_time
        elif type(end_time) == int:
            user_doc['sub_end'] += end_time

        await subscriptions.update_one({'userid': userid}, 
                                       {'$set': {'sub_end': user_doc['sub_end']}}, comment='award_premium_1')
    else:
        if type(end_time) == int:
            end_time = int(time()) + end_time 

        user_doc = {
            'userid': userid,
            'sub_start': int(time()),
            'sub_end': end_time,
            'end_notif': False
        }
        await subscriptions.insert_one(user_doc, comment='award_premium_2')

async def max_dino_col(lvl: int, user_id: int=0, premium_st: bool=False):
    """Возвращает доступное количесвто динозавров, беря во внимание уровень и статус
       Если передаётся user_id то считает сколько динозавров у юзера вместе с лимитом
       {
          'standart': { 'now': 0, 'limit': 0},
          'additional': {'now': 0, 'limit': 1}
        }
    """
    col = {
        'standart': {
            'now': 0, 'limit': 0
        },
        'additional': {
            'now': 0, 'limit': 1
        }
    }

    if premium_st: col['standart']['limit'] += 1
    col['standart']['limit'] += ((lvl // 20 + 1) - lvl // 80)

    if user_id:
        dinos = await dino_owners.find({'owner_id': user_id}, comment='max_dino_col_dinos')
        for dino in dinos:
            if dino['type'] == 'owner': col['standart']['now'] += 1
            else: col['additional']['now'] += 1

        eggs = await incubations.find({'owner_id': user_id}, comment='max_dino_col_eggs')
        for _ in eggs: col['standart']['now'] += 1
 
    return col

def max_lvl_xp(lvl: int): return 5 * lvl * lvl + 50 * lvl + 100

async def experience_enhancement(userid: int, xp: int):
    """Повышает количество опыта, если выполнены условия то повышает уровень и отпарвляет уведомление
    """
    user = await users.find_one({'userid': userid}, comment='experience_enhancement_user')
    if user:
        lvl = 0
        xp = user['xp'] + xp

        try:
            chat_user = await bot.get_chat_member(userid, userid)
            lang = await get_lang(chat_user.user.id)
            name = user_name(chat_user.user)
        except: 
            lang = 'en'
            name = 'name'

        lvl_messages = get_data('notifications.lvl_up', lang)

        while xp > 0:
            max_xp = max_lvl_xp(user['lvl'])
            if max_xp <= xp:
                xp -= max_xp
                lvl += 1
                if lvl >= 100: break

                if str(user['lvl'] + lvl) in lvl_messages: 
                    add_way = str(user['lvl'] + lvl)
                else: add_way = 'standart'

                await user_notification(userid, 'lvl_up', lang, 
                                        user_name=name,
                                        lvl=user['lvl'] + lvl, 
                                        add_way=add_way)
            else: break

        if lvl: await users.update_one({'userid': userid}, {'$inc': {'lvl': lvl}}, comment='experience_enhancement_1')
        await users.update_one({'userid': userid}, {'$set': {'xp': xp}}, comment='experience_enhancement_2')

        # Выдача награда за реферал
        if user['lvl'] < 5 and user['lvl'] + lvl >= GS['referal']['award_lvl']:
            sub = await get_user_sub(userid)
            if sub:
                code = sub['code']
                referal = await get_code_owner(code)
                if referal:
                    code_owner = referal['userid']
                    random_item = choice(GS['referal']['award_items'])
                    item_name = get_name(random_item, lang)

                    await AddItemToUser(code_owner, random_item)
                    await user_notification(code_owner, 'referal_award', lang, 
                                        user_name=name,
                                        lvl=user['lvl'] + lvl, item_name=item_name)

async def user_info(data_user: teleUser, lang: str, secret: bool = False):
    user = await User().create(data_user.id)
    return_text = ''

    premium = t('user_profile.no_premium', lang)
    if await user.premium:
        find = await subscriptions.find_one({'userid': data_user.id}, comment='user_info_find')
        if find:
            if find['sub_end'] == 'inf':
                premium = '♾'
            else:
                premium = seconds_to_str(
                    find['sub_end'] - find['sub_start'], lang)

    friends = await get_frineds(data_user.id)
    friends_count = len(friends['friends'])
    request_count = len(friends['requests'])

    dinos = await get_dinos_and_owners(data_user.id)
    eggs = await get_eggs(data_user.id)

    m_name = escape_markdown(user_name(data_user))

    return_text += t('user_profile.user', lang,
                     name = m_name,
                     userid = data_user.id,
                     premium_status = premium
                     )
    return_text += '\n\n'
    return_text += t('user_profile.level', lang,
                     lvl=user.lvl, xp_now=user.xp,
                     max_xp=max_lvl_xp(user.lvl),
                     coins=user.coins,
                     super_coins=user.super_coins
                     )
    return_text += '\n\n'
    if not secret:
        dd = await dead_dinos.find({'owner_id': user.userid}, comment='user_info_dd')
        return_text += t(f'user_profile.dinosaurs', lang,
                        dead=len(list(dd)), dino_col = len(dinos)
                        )
        return_text += '\n\n'
        for iter_data in dinos:
            dino = iter_data['dino']
            dino_status = t(f'user_profile.stats.{await dino.status}', lang)
            dino_rare_dict = get_data(f'rare.{dino.quality}', lang)
            dino_rare = f'{dino_rare_dict[2]} {dino_rare_dict[1]}'
            
            if iter_data['owner_type'] == 'owner': 
                dino_owner = t(f'user_profile.dino_owner.owner', lang)
            else:
                dino_owner = t(f'user_profile.dino_owner.noowner', lang)

            age = await dino.age()
            return_text += t('user_profile.dino', lang,
                            dino_name=escape_markdown(dino.name), 
                            dino_status=dino_status,
                            dino_rare=dino_rare,
                            owner=dino_owner,
                            age=seconds_to_str(age.days * 86400, lang, True)
                        )

        for egg in eggs:
            egg_rare_dict = get_data(f'rare.{egg.quality}', lang)
            egg_rare = f'{egg_rare_dict[3]}'
            return_text += t('user_profile.egg', lang,
                            egg_quality=egg_rare, 
                            remained=
                            seconds_to_str(egg.incubation_time - int(time()), lang, True)
                        )

    return_text += t('user_profile.friends', lang,
                     friends_col=friends_count,
                     requests_col=request_count
                     )

    if not secret:
        items, count = await user.get_inventory()

        return_text += '\n\n'
        return_text += t('user_profile.inventory', lang,
                        items_col=count
                        )

    return return_text

async def premium(userid: int):
    res = await subscriptions.find_one({'userid': userid}, comment='premium_res')
    return bool(res)

async def take_coins(userid: int, col: int, update: bool = False) -> bool:
    """Функция проверяет, можно ли отнять / добавить col монет у / к пользователя[ю]
       Если updatе - то обновляет данные

       ЕСЛИ ХОТИМ ОТНЯТЬ, НЕ ЗАБЫВАЕМ В COL УКАЗЫВАТЬ ОТРИЦАТЕЛЬНОЕ ЧИСЛО
    """
    user = await users.find_one({'userid': userid}, comment='take_coins_user')
    if user:
        coins = user['coins']
        if coins + col < 0: return False
        else: 
            if update:
                await users.update_one({'userid': userid}, 
                                 {'$inc': {'coins': col}}, comment='take_coins_1')
                log(f"Edit coins: user: {userid} col: {col}", 0, "take_coins")
            return True
    return False

async def get_dead_dinos(userid: int):
    return await dead_dinos.find({'owner_id': userid}, comment='get_dead_dinos')

async def count_inventory_items(userid: int, find_type: list):
    """ Считает сколько предметов нужных типов в инвентаре
    """
    result = 0
    for item in await items.find({'owner_id': userid}, 
                                {'_id': 0, 'owner_id': 0}, comment='count_inventory_items'):
        item_data = get_item_data(item['items_data']['item_id'])
        try:
            item_type = item_data['type']
        except Exception as E:
            item_type = None

        if item_type in find_type or not find_type: result += 1
    return result

async def user_in_chat(userid: int, chatid: int):
    statuss = ['creator', 'administrator', 'member']
    try:
        result = await bot.get_chat_member(chat_id=chatid, user_id=userid)
    except Exception as e: return False

    if result.status in statuss: return result.status
    return False

def check_name(user: teleUser):
    """ Проверяет есть ли в нике надпись DinoGochi
    """
    text = user.full_name.lower()
    if 'dinogochi' in text: return True
    return False

async def daily_award_con(userid: int):
    """ Заносит в данные чекин о награде
        0 - уже в базе 
        != 0 - занесён в базу
    """
    res = await daily_award_data.find_one({'owner_id': userid}, comment='daily_award_con_res')
    if res: return 0
    else:
        # Количество секунд в момент начала следующего дня
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)

        data = {
            'owner_id': userid,
            'time_end': int(tomorrow.timestamp())
        }
        await daily_award_data.insert_one(data, comment='daily_award_con_1')
        return int(tomorrow.timestamp())

async def max_eat(userid: int):
    """ Функция проверяет количество еды в инвентаре
    """
    col = await col_dinos(userid)

    if await premium(userid):
        per_one = GS['premium_max_eat_items']
    else: 
        per_one = GS['max_eat_items']

    max_col = col * per_one + 50
    return max_col

async def get_inventory_from_i(userid: int, items_l: list = []):
    inv = []
    data_inv = await items.find(
        {'owner_id': userid}, 
        {'_id': 0, 'owner_id': 0}, comment='get_inventory_from_i')
    for item_dict in data_inv:
        if item_dict['items_data']['item_id'] in items_l:
            item = {
                'item': item_dict['items_data'], 
                "count": item_dict['count']
                }
            inv.append(item)
    return inv