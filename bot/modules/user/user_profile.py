

# Функция для генерации кнопок
from time import time
from bot.const import GAME_SETTINGS as GS
from bot.modules.data_format import escape_markdown, list_to_inline, seconds_to_str, user_name_from_telegram
from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.json_item import GetItem
from bot.modules.localization import get_data, t
from bot.modules.user.friends import get_frineds
from bot.modules.user.user import User, get_dinos_and_owners, get_eggs, max_lvl_xp, user_name
from bot.modules.user.xp_boost import xpboost_percent
from bot.exec import bot

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.dbmanager import mongo_client

dead_users = DBconstructor(mongo_client.other.dead_users)
subscriptions = DBconstructor(mongo_client.user.subscriptions)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
sellers = DBconstructor(mongo_client.market.sellers)


# Функция для создания кнопок профиля
async def user_profile_markup(userid: int, lang: str, 
                        page_type: str, page: int = 0):
    buttons = []

    match page_type:
        case 'main':
            # Кнопка перехода в меню просмотра динозавров
            buttons.extend( [
                {
                    '🦕': f'user_profile dino {userid} 0',
                    '⚡': f'user_profile lvl {userid} 0',
                    '🏆': f'user_profile achievements {userid} 0'
                }
            ])

        case 'dino':
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

        case 'lvl':
            pass

        case 'achievements':
            pass

    return list_to_inline(buttons, 3)

# Страница динозавры
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

            age = await dino.get_age()
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

async def user_lvl_info(userid: int, lang: str, page: int = 0):
    user = await User().create(userid)
    return_text = ''

    return return_text, await user.get_avatar()

async def user_achievements_info(userid: int, lang: str, page: int = 0):
    user = await User().create(userid)
    return_text = ''

    return return_text, await user.get_avatar()

# Главная страница
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
            item_data = GetItem(item.item_id)
            rarity = item_data.rank
            if rarity in rarity_counts:
                rarity_counts[rarity] += item.count

    if secret:
        count = '`' + hide_text + '`'
        rarity_counts = {key: '`' + hide_text + '`' for key in rarity_counts.keys()}

    return_text += '\n\n'
    return_text += t('user_profile.inventory', lang,
                    items_col=count,
                    formating=True,
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