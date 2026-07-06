from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import Ad, DinoCollection, Friend, Lang, Referral, Subscription
from bot.models.tavern import InsideShop
from bot.models.user import User
from bot.models.items import Item, ItemCraft
from bot.models.dinosaur import DeadDino, Dino, DinoOwners, Egg
from bot.models.market import Preferential, Product, Puhs, Seller
from bot.models.tavern import DailyAward, Quest
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

def max_lvl_xp(lvl: int):
    xp_formula = GS.get('xp_formula', {"a": 5, "b": 50, "c": 100})
    return xp_formula.get('a', 5) * lvl * lvl + xp_formula.get('b', 50) * lvl + xp_formula.get('c', 100)

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

        user_obj = await User().create(userid)
        dinos = await user_obj.get_dinos_and_owners()
        eggs = await user_obj.get_eggs

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

    dd = await user.get_dead_dinos()

    dinos = await user.get_dinos_and_owners()
    eggs = await user.get_eggs

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

            dino_uniqueness = await Dino.get_uniqueness_factor(dino.data_id)

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
        find = await Subscription.find_one(Subscription.userid == userid)
        if find:
            if find.sub_end == 'inf': premium = '♾'
            else:
                premium = seconds_to_str(
                    find.sub_end - int(time()), lang)

    friends = await get_frineds(userid)
    friends_count = len(friends['friends'])
    request_count = len(friends['requests'])

    if not secret:
        if name is None or name == '': name = user.name
        if not name: name = await User.get_user_name(userid)
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
        market = await Seller.find_one(Seller.owner_id == userid)
        if market:
            return_text += '\n\n'
            return_text += t('user_profile.market.caption', lang)
            return_text += '\n'
            return_text += t('user_profile.market.market_name', lang, market_name=escape_markdown(market.name))
            return_text += '\n'
            return_text += t('user_profile.market.earned', lang, coins=market.earned)

    if secret:
        return_text += '\n\n'
        return_text += t('user_profile.secret', lang)

    return return_text, await user.get_avatar()






async def count_inventory_items(userid: int, find_type: list):
    """ Считает сколько предметов нужных типов в инвентаре
    """
    result = 0
    for item in await Item.find(Item.owner_id == userid).to_list():
        item_data = get_item_data(item.items_data.get('item_id'))
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
    res = await DailyAward.find_one(DailyAward.owner_id == userid)
    if res: return 0
    else:
        # Количество секунд в момент начала следующего дня
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)

        data = DailyAward(
            owner_id=userid,
            time_end=int(tomorrow.timestamp())
        )
        await data.insert()
        return int(tomorrow.timestamp())

async def max_eat(userid: int):
    """ Функция проверяет количество еды в инвентаре
    """
    user = await User.find_one(User.userid == userid)
    if not user:
        return 50
    col = await user.get_col_dinos

    if await user.premium:
        per_one = GS['premium_max_eat_items']
    else: 
        per_one = GS['max_eat_items']

    max_col = col * per_one + 50
    return max_col