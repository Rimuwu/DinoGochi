from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import Ad, DinoCollection, Friend, Lang, Referral, Subscription
from bot.models.tavern import InsideShop
from bot.models.user import User
from bot.models.items import Item, ItemCraft
from bot.models.dinosaur import DeadDino, Dino, DinoOwners, Egg
from bot.models.market import Preferential, Product, Puhs, Seller
from bot.models.tavern import DailyAward, Quest, Tavern
from bot.models.other import DeadUser, MessageLog
from bot.models.group import GroupUser
from random import choice
from time import time
from typing import Union
from bson import ObjectId

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, item_list, list_to_inline, seconds_to_str, user_name_from_telegram
from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.models.dinosaur import Dino, Egg
from bot.modules.images import async_open
from bot.models.other import Event
from bot.modules.managment.tracking import update_all_user_track
from bot.modules.user.advert import create_ads_data
from bot.modules.items.item import AddItemToUser, get_item_dict
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_name
from bot.modules.localization import get_data, t, get_lang, available_locales
from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.models.user import Referral
from datetime import datetime, timedelta

from bot.modules.user.avatar import get_avatar
from bot.modules.user.friends import get_frineds
from bot.modules.user.premium import premium
from bot.modules.user.xp_boost import xpboost_percent

users = LazyCollection(User)
items = LazyCollection(Item)
dinosaurs = LazyCollection(Dino)
products = LazyCollection(Product)
sellers = LazyCollection(Seller)
puhs = LazyCollection(Puhs)
dead_dinos = LazyCollection(DeadDino)
tavern = LazyCollection(Tavern)
dino_collection = LazyCollection(DinoCollection)

incubations = LazyCollection(Egg)
dino_owners = LazyCollection(DinoOwners)
friends = LazyCollection(Friend)
subscriptions = LazyCollection(Subscription)
referals = LazyCollection(Referral)
daily_award_data = LazyCollection(DailyAward)
langs = LazyCollection(Lang)
ads = LazyCollection(Ad)
dead_users = LazyCollection(DeadUser)

quests = LazyCollection(Quest)
message_log = LazyCollection(MessageLog)
item_craft = LazyCollection(ItemCraft)
preferential = LazyCollection(Preferential)
inside_shop = LazyCollection(InsideShop)

group_users = LazyCollection(GroupUser)

from bot.models.user import User

async def insert_user(userid: int, lang: str, name = '', avatar = ''):
    """Создание пользователя"""
    from bot.models.user import Lang
    user = await User.find_one(User.userid == userid)
    if not user:
        log(prefix='InsertUser', message=f'User: {userid}', lvl=0)
        if lang not in available_locales: lang = 'en'
        l_doc = await Lang.find_one(Lang.userid == userid)
        if not l_doc:
            await Lang(userid=userid, lang=lang).insert()

        user = User(userid=userid)
        if name != '': 
            user.name = escape_markdown(name)
            if user.name == '': user.name = 'noname'
        if avatar != '': user.avatar = avatar

        await create_ads_data(userid, 1800)
        await user.insert()
        return user
    return user

async def get_dinos(userid: int, all_dinos: bool = True) -> list[Dino]:
    """Возвращает список с объектами динозавров.
       all_dinos = вернёт в том числе и совместных дино
    """
    from bot.models.dinosaur import DinoOwners
    dino_list = []

    if all_dinos:
        res = await DinoOwners.find(DinoOwners.owner_id == userid).to_list()
    else:
        res = await DinoOwners.find(DinoOwners.owner_id == userid, DinoOwners.type == 'owner').to_list()

    for dino_obj in res:
        try:
            dd = await Dino.find_one(Dino.id == ObjectId(dino_obj.dino_id))
        except Exception:
            dd = None
        if not dd:
            dd = await Dino.find_one(Dino.alt_id == dino_obj.dino_id)
        if dd: dino_list.append(dd)

    return dino_list

async def get_dinos_and_owners(userid: int) -> list:
    """Возвращает список с объектами динозавров, а так же правами на динозавра"""
    from bot.models.dinosaur import DinoOwners
    data = []
    res = await DinoOwners.find(DinoOwners.owner_id == userid).to_list()
    for dino_obj in res:
        try:
            dd = await Dino.find_one(Dino.id == ObjectId(dino_obj.dino_id))
        except Exception:
            dd = None
        if not dd:
            dd = await Dino.find_one(Dino.alt_id == dino_obj.dino_id)
        if dd:
            data.append({'dino': dd, 'owner_type': dino_obj.type})

    return data

async def col_dinos(userid: int) -> int:
    from bot.models.dinosaur import DinoOwners
    return await DinoOwners.find(DinoOwners.owner_id == userid).count()

async def get_eggs(userid: int) -> list:
    """Возвращает список с объектами динозавров."""
    from bot.models.dinosaur import Egg
    return await Egg.find(Egg.owner_id == userid, Egg.stage == 'incubation').to_list()

async def get_inventory(userid: int, exclude_ids: list  | None = None):
    from bot.models.items import Item
    if exclude_ids is None: exclude_ids = []
    
    inv, count = [], 0
    data_inv = await Item.find(Item.owner_id == userid).to_list()
    for item in data_inv:
        if item.items_data.get('item_id') not in exclude_ids:
            inv.append({
                '_id': item.id,
                'owner_id': item.owner_id,
                'items_data': item.items_data,
                'count': item.count
            })
            count += item.count
    return inv, count

async def items_count(userid: int):
    from bot.models.items import Item
    return await Item.find(Item.owner_id == userid).count()

async def last_dino(user: User) -> Union[Dino, None]:
    """Возвращает последнего выбранного динозавра.
       Если None - вернёт первого
       Если нет динозавров - None
    """
    last_dino_id = user.settings.get('last_dino')
    if last_dino_id:
        try:
            dino_data = await Dino.find_one(Dino.id == ObjectId(last_dino_id))
        except Exception:
            dino_data = None
        if not dino_data:
            dino_data = await Dino.find_one(Dino.alt_id == str(last_dino_id))
        if dino_data:
            return dino_data

    dino_list = await user.get_dinos()
    if dino_list:
        first_dino = dino_list[0]
        user.settings['last_dino'] = first_dino.id
        await user.save()
        return first_dino
    else:
        user.settings['last_dino'] = None
        await user.save()
        return None

async def award_premium(userid: int, end_time: Union[int, str]):
    """Присуждение премиум статуса юзеру"""
    from bot.models.user import Subscription
    user_doc = await Subscription.find_one(Subscription.userid == userid)
    if user_doc:
        if isinstance(user_doc.sub_end, str) and user_doc.sub_end == "inf":
            pass
        elif isinstance(end_time, str):
            user_doc.sub_end = end_time
        elif isinstance(end_time, int):
            if isinstance(user_doc.sub_end, (int, float)):
                user_doc.sub_end += end_time
            else:
                user_doc.sub_end = int(time()) + end_time
        await user_doc.save()
    else:
        if isinstance(end_time, int):
            end_time = int(time()) + end_time 
        user_doc = Subscription(
            userid=userid,
            sub_start=int(time()),
            sub_end=end_time
        )
        await user_doc.insert()

async def max_dino_col(lvl: int, user_id: int=0, premium_st: bool=False, add_slots: int=0):
    """Возвращает доступное количесвто динозавров, беря во внимание уровень и статус"""
    col = {
        'standart': {
            'now': 0, 'limit': 0
        },
        'additional': {
            'now': 0, 'limit': 1
        }
    }

    dino_lim_cfg = GS.get('dino_limit', {"premium_bonus": 1, "lvl_step": 20, "lvl_cap_step": 100})
    if premium_st: col['standart']['limit'] += dino_lim_cfg.get('premium_bonus', 1)
    col['standart']['limit'] += ((lvl // dino_lim_cfg.get('lvl_step', 20) + 1) - lvl // dino_lim_cfg.get('lvl_cap_step', 100))
    col['standart']['limit'] += add_slots

    if user_id:
        from bot.models.dinosaur import DinoOwners, Egg
        dinos = await DinoOwners.find(DinoOwners.owner_id == user_id).to_list()
        for dino in dinos:
            if dino.type == 'owner': col['standart']['now'] += 1
            else: col['additional']['now'] += 1

        eggs = await Egg.find(Egg.owner_id == user_id, Egg.stage == 'incubation').to_list()
        for _ in eggs: col['standart']['now'] += 1
 
    return col


def max_lvl_xp(lvl: int):
    xp_formula = GS.get('xp_formula', {"a": 5, "b": 50, "c": 100})
    return xp_formula.get('a', 5) * lvl * lvl + xp_formula.get('b', 50) * lvl + xp_formula.get('c', 100)

async def experience_enhancement(userid: int, xp: int):
    """Повышает количество опыта, если выполнены условия то повышает уровень и отпарвляет уведомление
    """
    user = await User().create(userid)
    lang = await user.lang

    xp = int(xp * await xpboost_percent(userid))

    if user:
        lvl, xp = 0, user.xp + xp

        lvl_messages = get_data('notifications.lvl_up', lang)

        while xp > 0:
            max_xp = max_lvl_xp(user.lvl + lvl)
            if max_xp <= xp:
                xp -= max_xp
                lvl += 1

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
            sub = await Referral.get_user_sub(userid)
            if sub:
                code = sub['code']
                referal = await Referral.get_code_owner(code)
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
            dino_status = t(f'user_profile.stats.{(await dino.status).value}', lang)
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
                     super_coins=user_super_coins,
                     boost=round(await xpboost_percent(userid), 1),
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