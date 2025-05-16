from random import choice
from time import time
from typing import Union

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, item_list, list_to_inline, seconds_to_str, user_name_from_telegram
from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.modules.dinosaur.dinosaur import Dino, Egg
from bot.modules.images import async_open
from bot.modules.managment.events import check_event, get_event
from bot.modules.managment.tracking import update_all_user_track
from bot.modules.user.advert import create_ads_data
from bot.modules.items.item import AddItemToUser, get_item_dict
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_name
from bot.modules.localization import get_data, t, get_lang, available_locales
from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.modules.managment.referals import get_code_owner, get_user_sub
from datetime import datetime, timedelta

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.avatar import get_avatar
from bot.modules.user.friends import get_frineds
from bot.modules.user.premium import premium
from bot.modules.user.rtl_name import check_name

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

quests = DBconstructor(mongo_client.tavern.quests)
message_log = DBconstructor(mongo_client.other.message_log)
item_craft = DBconstructor(mongo_client.items.item_craft)
preferential = DBconstructor(mongo_client.market.preferential)
inside_shop = DBconstructor(mongo_client.market.inside_shop)

class User:

    def __init__(self):
        """Создание объекта пользователя
        """
        self.userid = 0
        self.name = 'noname' # Имя пользователя
        self.avatar = '' # file_id аватара

        self.last_message_time = 0
        self.last_markup = 'main_menu'

        self.settings = {
            'notifications': True, # Уведомления 
            'last_dino': None, #храним ObjectId
            'profile_view': 1, # Вид UI для профиля динозавров
            'inv_view': [2, 3], # Размер UI инвентаря
            'my_name': '', # Как вас называет динозавр
            'no_talk': False, # Сообщения типо общения в рандомный момент
            'confidentiality': False # Если True то устанавливает уровень secret в профиле в группах + не отображается в локальном рейтинге
            }

        self.notifications = {}

        self.coins = 100
        self.super_coins = 0

        self.lvl = 0
        self.xp = 0

        self.add_slots = 0

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

        if data:
            if 'name' not in data:
                data['name'] = ''
                data['avatar']  = ''
                await self.update({'$set': {'name': '', 'avatar': ''}})

            if not data['name']:
                # Долговременная мера по сохранению имени в базе
                await user_name(userid) 

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

        for collection in [items, products, dead_dinos, incubations, sellers, puhs, daily_award_data, quests, inside_shop]:
            await collection.delete_many({'owner_id': self.userid}, comment='User_full_delete')

        for collection in [referals, langs, ads, dead_users, subscriptions, tavern, dead_users, message_log, item_craft, preferential, inside_shop]:
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
                    if dino_d:
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

        # Обновляем трекеры
        await update_all_user_track(self.userid, 'delete_account')

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
        return await max_dino_col(self.lvl, self.userid, await self.premium, self.add_slots)

    async def get_avatar(self):
        """Возвращает аватарку пользователя, если файл устарел - обновляет и возвращает новую."""

        return await get_avatar(self.userid)

async def insert_user(userid: int, lang: str, name = '', avatar = ''):
    """Создание пользователя"""

    if not await users.find_one({'userid': userid}, comment='insert_user'):
        log(prefix='InsertUser', message=f'User: {userid}', lvl=0)
        if lang not in available_locales: lang = 'en'
        set_lang = await langs.find_one({'userid': userid}) == {}
        if set_lang:
            await langs.insert_one({'userid': userid, 'lang': lang}, comment='insert_user_1')

        user = await User().create(userid)
        if name != '': 
            user.name = escape_markdown(name)
            if user.name == '': user.name = 'noname'
        if avatar == '': user.avatar = avatar

        await create_ads_data(userid, 1800)
        return await users.insert_one(user.__dict__, comment='insert_user')

async def get_dinos(userid: int, all_dinos: bool = True) -> list[Dino]:
    """Возвращает список с объектами динозавров.
       all_dinos = вернёт в том числе и совместных дино
    """
    dino_list = []

    if all_dinos:
        res = await dino_owners.find({'owner_id': userid}, 
                                          {'dino_id': 1}, comment='get_dinos_res')
    else:
        res = await dino_owners.find(
            {'owner_id': userid, 'type': 'owner'}, {'dino_id': 1}, comment='get_dinos_res')

    for dino_obj in res:
        dd = await Dino().create(dino_obj['dino_id'])
        if dd: dino_list.append(dd)

    return dino_list

async def get_dinos_and_owners(userid: int) -> list:
    """Возвращает список с объектами динозавров, а так же правами на динозавра"""
    data = []
    for dino_obj in await dino_owners.find({'owner_id': userid}, comment='get_dinos_and_owners'):
        dd = await Dino().create(dino_obj['dino_id'])
        if dd:
            data.append({'dino': dd, 'owner_type': dino_obj['type']})

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

async def get_inventory(userid: int, exclude_ids: list  | None = None):
    if exclude_ids is None: exclude_ids = []
    
    inv, count = [], 0
    data_inv = await items.find({'owner_id': userid}, 
                                {'owner_id': 0}, comment='get_inventory')
    for item_dict in data_inv:
        if item_dict['items_data']['item_id'] not in exclude_ids:
            inv.append(item_dict)

            count += item_dict['count']
    return inv, count

async def items_count(userid: int):
    return len(list(await items.find({'owner_id': userid}, {'_id': 1}, comment='items_count')))

async def last_dino(user: User) -> Union[Dino, None]:
    """Возвращает последнего выбранного динозавра.
       Если None - вернёт первого
       Если нет динозавров - None
    """
    last_dino_id = user.settings.get('last_dino')
    if last_dino_id:
        dino_data = await dinosaurs.find_one({'_id': last_dino_id}, {"_id": 1}, comment='last_dino')
        if dino_data:
            return await Dino().create(dino_data['_id'])

    dino_list = await user.get_dinos()
    if dino_list:
        first_dino = dino_list[0]
        await user.update({'$set': {'settings.last_dino': first_dino._id}})
        return first_dino
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
            pass
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

async def max_dino_col(lvl: int, user_id: int=0, premium_st: bool=False, add_slots: int=0):
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
    col['standart']['limit'] += ((lvl // 20 + 1) - lvl // 100)
    col['standart']['limit'] += add_slots

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
    user = await User().create(userid)
    lang = await user.lang

    # if await check_event('april_5'): xp *= 2

    if user:
        lvl, xp = 0, user.xp + xp

        lvl_messages = get_data('notifications.lvl_up', lang)

        while xp > 0:
            max_xp = max_lvl_xp(user.lvl + lvl)
            if max_xp <= xp:
                xp -= max_xp
                lvl += 1
                if lvl >= 100: break

                if str(user.lvl + lvl) in lvl_messages: 
                    add_way = str(user.lvl + lvl)
                else: add_way = 'standart'

                friend_lang = await get_lang(userid)
                await user_notification(userid, 'lvl_up', friend_lang, 
                                        user_name=user.name,
                                        lvl=user.lvl + lvl, 
                                        add_way=add_way)
            else: break

        if lvl: await users.update_one({'userid': userid}, {'$inc': {'lvl': lvl}}, comment='experience_enhancement_1')
        await users.update_one({'userid': userid}, 
                               {'$set': {'xp': xp}}, comment='experience_enhancement_2')

        # Выдача награда за реферал
        if user.lvl < 5 and user.lvl + lvl >= GS['referal']['award_lvl']:
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
                                        user_name=user.name,
                                        lvl=user.lvl + lvl, item_name=item_name)

async def user_profile_markup(userid: int, lang: str, 
                        page_type: str, page: int = 0):
    buttons = []

    if page_type == 'main':
        # Кнопка перехода в меню просмотра динозавров
        buttons.append(
            {'🦕': f'user_profile dino {userid} 0'}
        )

    elif page_type == 'dino':
        per_page = GS['profiles_dinos_per_page']

        dinos = await get_dinos_and_owners(userid)
        eggs = await get_eggs(userid)

        total = len(dinos) + len(eggs)
        max_page = (total + per_page - 1) // per_page

        page_plus = page + 1 if page + 1 < max_page else 0
        page_minus = page - 1 if page - 1 >= 0 else max_page - 1

        bts_dct = {
            GS['back_button']: f'user_profile dino {userid} {page_minus}',
            '👤': f'user_profile main {userid} 0',
            GS['forward_button']: f'user_profile dino {userid} {page_plus}'
        }
        if total == 1:
            bts_dct = {
                '👤': f'user_profile main {userid} 0'
            }

        buttons.append(bts_dct)

    return list_to_inline(buttons, 3)

async def user_dinos_info(userid: int, lang: str, page: int = 0):
    user = await User().create(userid)
    return_text = ''
    per_page = GS['profiles_dinos_per_page']

    dd = await dead_dinos.find({'owner_id': user.userid}, comment='user_info_dd')

    dinos = await get_dinos_and_owners(userid)
    eggs = await get_eggs(userid)

    slots = await user.max_dino_col()
    dino_slots = f'{slots["standart"]["now"]}/{slots["standart"]["limit"]}'
    return_text += t(f'user_profile.dinosaurs', lang,
                    dead=len(list(dd)), dino_col=len(dinos), dino_slots=dino_slots
                    )
    return_text += '\n\n'

    # Pagination for dinos and eggs
    all_items = dinos + eggs
    total_items = len(all_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))

    start = page * per_page
    end = start + per_page
    page_items = all_items[start:end]

    for iter_data in page_items:
        if isinstance(iter_data, dict):  # Dino
            dino: Dino = iter_data['dino']
            dino_status = t(f'user_profile.stats.{await dino.status}', lang)
            dino_rare_dict = get_data(f'rare.{dino.quality}', lang)
            dino_rare = f'{dino_rare_dict[2]} {dino_rare_dict[1]}'

            dino_uniqueness = await get_dino_uniqueness_factor(dino.data_id)

            if iter_data['owner_type'] == 'owner':
                dino_owner = t(f'user_profile.dino_owner.owner', lang)
            else:
                dino_owner = t(f'user_profile.dino_owner.noowner', lang)

            age = await dino.age()
            if age.days == 0:
                age = seconds_to_str(age.seconds, lang, True)
            else:
                age = seconds_to_str(age.days * 86400, lang, True)

            return_text += t('user_profile.dino', lang,
                            dino_name=escape_markdown(dino.name),
                            dino_status=dino_status,
                            dino_rare=dino_rare,
                            owner=dino_owner,
                            age=age,
                            dino_uniqueness=dino_uniqueness,
                            heal=dino.stats['heal'],
                            eat=dino.stats['eat'],
                            mood=dino.stats['mood'],
                            game=dino.stats['game'],
                            energy=dino.stats['energy']
                        )
        else:  # Egg
            egg = iter_data
            egg_rare_dict = get_data(f'rare.{egg.quality}', lang)
            egg_rare = f'{egg_rare_dict[3]}'
            return_text += t('user_profile.egg', lang,
                            egg_quality=egg_rare,
                            remained=seconds_to_str(egg.incubation_time - int(time()), lang, True)
                        )

    # Add page info if more than one page
    if total_pages > 1:
        return_text += f"{page + 1}/{total_pages}"

    image = await user.get_avatar()
    return return_text, image

async def user_info(userid: int, lang: str, secret: bool = False, 
                    name: str | None = None):
    user = await User().create(userid)
    return_text = ''

    premium = t('user_profile.no_premium', lang)
    if await user.premium:
        find = await subscriptions.find_one({'userid': userid}, comment='user_info_find')
        if find:
            if find['sub_end'] == 'inf': premium = '♾'
            else:
                premium = seconds_to_str(
                    find['sub_end'] - int(time()), lang)

    friends = await get_frineds(userid)
    friends_count = len(friends['friends'])
    request_count = len(friends['requests'])

    if not secret:
        if name is None or name == '': name = user.name
        if not name: name = await user_name(userid)
        name = escape_markdown(name)
    else:
        try:
            chat_user = await bot.get_chat_member(userid, userid)
            user_in_c = chat_user.user
            name = user_name_from_telegram(user_in_c)
        except: name = 'noname'
        
    user_coins = user.coins
    user_super_coins = user.super_coins
    
    hide_text = t('user_profile.hide', lang)

    if secret:
        id_for_text = hide_text
        name_for_text = hide_text
        premium = '`' + hide_text + '`'
        request_count = '`' + hide_text + '`'
        user_coins = '`' + hide_text + '`'
        user_super_coins = '`' + hide_text + '`'
    else:
        id_for_text = str(userid)
        name_for_text = escape_markdown(name)

    return_text += t('user_profile.user', lang,
                     name = name_for_text,
                     userid = id_for_text,
                     premium_status = premium
                     )
    return_text += '\n\n'
    return_text += t('user_profile.level', lang,
                     lvl=user.lvl, xp_now=user.xp,
                     max_xp=max_lvl_xp(user.lvl),
                     coins=user_coins,
                     super_coins=user_super_coins
                     )
    return_text += '\n\n'

    return_text += t('user_profile.friends', lang,
                     friends_col=friends_count,
                     requests_col=request_count
                     )

    items, count = await user.get_inventory()

    # Подсчёт предметов по редкостям
    rarity_counts = {
        'common': 0,
        'uncommon': 0,
        'rare': 0,
        'mystical': 0,
        'legendary': 0,
        'mythical': 0
    }

    if not secret:

        for item in items:
            item_data = get_item_data(item['items_data']['item_id'])
            rarity = item_data.get('rank', 'common')
            if rarity in rarity_counts:
                rarity_counts[rarity] += item['count']

    if secret:
        count = '`' + hide_text + '`'
        rarity_counts = {key: '`' + hide_text + '`' for key in rarity_counts.keys()}

    return_text += '\n\n'
    return_text += t('user_profile.inventory', lang,
                    items_col=count,
                    **rarity_counts
                    )

    if not secret:
        market = await sellers.find_one({'owner_id': userid}, comment='user_info_market')
        if market:
            return_text += '\n\n'
            return_text += t('user_profile.market.caption', lang)
            return_text += '\n'
            return_text += t('user_profile.market.market_name', lang, market_name=escape_markdown(market['name']))
            return_text += '\n'
            return_text += t('user_profile.market.earned', lang, coins=market['earned'])

    if secret:
        return_text += '\n\n'
        return_text += t('user_profile.secret', lang)

    return return_text, await user.get_avatar()

async def user_name(userid: int):
    user = await users.find_one({'userid': int(userid)}, comment='user_name')
    if user: 
        if user['name'] or user['name'] != '' or user['name'] != 'noname':
            return user['name']
        else:
            chat_user = await bot.get_chat_member(userid, userid)
            if chat_user:
                name = chat_user.user.first_name
                await users.update_one({'userid': userid}, 
                                       {'$set': {'name': name}}, comment='set_user_name_1')
                return name
    return 'NoName_NoUser'

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

async def get_inventory_from_i(userid: int, items_l: list[dict] | None = None, 
                               limit = None, one_count = False):
    """ 
        items_l - [ {'item_id': int, 'abilities': dict} ]
        one_count - стандартные значения хар и 1 количество (советую использовать с limit = 1)
    """
    if items_l is None: items_l = []
    
    if one_count: id_list = []

    find_i = []
    for item in items_l:
        item_id: int = item['item_id']
        abilities: dict = item.get('abilities', {})

        if abilities:
            find_data = {'owner_id': userid, 
                         'items_data.item_id': item_id, 
                         'items_data.abilities': abilities}
        else:
            find_data = {'owner_id': userid, 'items_data.item_id': item_id}

        fi = await items.find(find_data, {'_id': 0, 'owner_id': 0}, 
                              max_col=limit)
        pre_l = list(map(
            lambda i: {'item': i['items_data'], 'count': i['count']}, fi))
        if one_count:

            for i in pre_l:
                if i['item']['item_id'] not in id_list:
                    id_list.append(i['item']['item_id'])

                    item = get_item_dict(i['item']['item_id'])
                    # Считаем общее количество предметов с таким же item_id
                    total_count = sum(j['count'] for j in pre_l if j['item']['item_id'] == i['item']['item_id'])
                    find_i.append(
                        {
                            "item": item,
                            "count": total_count
                        }
                    )
        else:
            find_i += pre_l

    result = item_list(find_i)
    return result

async def user_have_account(userid: int) -> bool:
    """ Проверяет есть ли у юзера аккаунт в базе данных
    """
    user = await users.find_one({'userid': userid}, comment='user_have_account')
    return bool(user)