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



from bot.models.user import User

def max_lvl_xp(lvl: int):
    xp_formula = GS.get('xp_formula', {"a": 5, "b": 50, "c": 100})
    return xp_formula.get('a', 5) * lvl * lvl + xp_formula.get('b', 50) * lvl + xp_formula.get('c', 100)

async def user_profile_markup(userid: int, lang: str, 
                        page_type: str, page: int = 0):
    buttons = []

    if page_type == 'main':
        # Кнопки перехода в меню просмотра динозавров, достижений и инвентаря
        buttons.append(
            {'🦕': f'user_profile dino {userid} 0',
             '🏆': f'user_profile achievements {userid} 0',
             '🎒': f'user_profile inventory {userid} 0'}
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

    elif page_type == 'inventory':
        per_page = GS.get('profiles_items_per_page', 10)

        user_obj = await User().create(userid)
        items, count = await user_obj.get_inventory()

        total = len(items)
        max_page = (total + per_page - 1) // per_page
        if max_page == 0:
            max_page = 1

        page_plus = page + 1 if page + 1 < max_page else 0
        page_minus = page - 1 if page - 1 >= 0 else max_page - 1

        bts_dct = {
            GS['back_button']: f'user_profile inventory {userid} {page_minus}',
            '👤': f'user_profile main {userid} 0',
            GS['forward_button']: f'user_profile inventory {userid} {page_plus}'
        }
        if total <= 1:
            bts_dct = {
                '👤': f'user_profile main {userid} 0'
            }

        buttons.append(bts_dct)

    elif page_type == 'achievements':
        from bot.const import ACHIEVEMENTS
        display_groups = ACHIEVEMENTS.get('display_groups', [])
        ach_dict = ACHIEVEMENTS['achievements']
        
        visible_groups_count = 0
        for group in display_groups:
            group_ach_ids = group.get('achievements', [])
            has_visible = False
            for ach_id in group_ach_ids:
                if ach_id in ach_dict and ach_id != "example":
                    has_visible = True
                    break
            if has_visible:
                visible_groups_count += 1
                
        max_page = max(visible_groups_count, 1)
            
        page_plus = page + 1 if page + 1 < max_page else 0
        page_minus = page - 1 if page - 1 >= 0 else max_page - 1
        
        bts_dct = {
            GS['back_button']: f'user_profile achievements {userid} {page_minus}',
            '👤': f'user_profile main {userid} 0',
            GS['forward_button']: f'user_profile achievements {userid} {page_plus}'
        }
        if max_page <= 1:
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

async def user_inventory_info(userid: int, lang: str, page: int = 0):
    user = await User().create(userid)
    return_text = ''
    per_page = GS.get('profiles_items_per_page', 10)

    items, count = await user.get_inventory()

    return_text += t('user_profile.inventory_page.caption', lang, count=count)
    return_text += '\n\n'

    if not items:
        return_text += t('user_profile.inventory_page.no_items', lang)
        image = await user.get_avatar()
        return return_text, image

    # Sort items by rarity (mythical down to common)
    rarity_order = ['mythical', 'legendary', 'mystical', 'rare', 'uncommon', 'common']
    
    def sort_key(item):
        item_id = item['items_data']['item_id']
        item_data = get_item_data(item_id)
        rank = item_data.get('rank', 'common')
        try:
            return rarity_order.index(rank)
        except ValueError:
            return len(rarity_order)

    sorted_items = sorted(items, key=sort_key)

    total_items = len(sorted_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))

    start = page * per_page
    end = start + per_page
    page_items = sorted_items[start:end]

    # Group page_items by rarity
    groups = {}
    for item in page_items:
        item_id = item['items_data']['item_id']
        item_data = get_item_data(item_id)
        rank = item_data.get('rank', 'common')
        if rank not in groups:
            groups[rank] = []
        groups[rank].append(item)

    for rank in rarity_order:
        if rank in groups:
            rank_title = t(f'item_info.rank.{rank}', lang)
            return_text += f"*{rank_title}*:\n"
            for item in groups[rank]:
                item_id = item['items_data']['item_id']
                abilities = item['items_data'].get('abilities')
                item_name = get_name(item_id, lang, abilities)
                return_text += f" • {item_name} x{item['count']}\n"
            return_text += "\n"

    if total_pages > 1:
        return_text += t('user_profile.inventory_page.pages', lang, page=page+1, total_pages=total_pages)

    image = await user.get_avatar()
    return return_text, image

async def user_achievements_info(userid: int, lang: str, page: int = 0):
    from bot.const import ACHIEVEMENTS
    from bot.models.user import Achievement
    from bot.modules.items.collect_items import get_all_items
    import datetime

    user = await User().create(userid)
    ach_dict = ACHIEVEMENTS['achievements']
    display_groups = ACHIEVEMENTS.get('display_groups', [])

    # Get all user achievements
    all_user_achievements = await Achievement.find(
        Achievement.userid == userid
    ).to_list()
    ach_docs = {a.achievement_id: a for a in all_user_achievements}
    unlocked_ids = {a.achievement_id: a for a in all_user_achievements if a.unlocked_time > 0}

    # Fetch total foods to calculate progress for feed_all_food dynamically
    all_items = get_all_items()
    all_eat_ids = {k for k, v in all_items.items() if getattr(v, 'type', '') == 'eat'}
    total_eat = len(all_eat_ids)

    # Fetch progress stats asynchronously beforehand
    from bot.models.dinosaur import DinoOwners
    from bot.models.other import Donation
    from bot.models.user import Friend, Referral
    from bot.models.enums import FriendType, ReferralType
    from bot.modules.user.achievements import _count_completable_achievements

    # Fetch dinos count and max skill count
    dino_conns = await DinoOwners.find(DinoOwners.owner_id == userid).to_list()
    dino_count = len(dino_conns)
    max_skills_dinos = 0
    for conn in dino_conns:
        if conn.dino:
            try:
                d = await conn.dino.fetch()
                if d:
                    stats = d.stats or {}
                    if all(stats.get(s, 0) >= 20.0 for s in ['power', 'dexterity', 'intelligence', 'charisma']):
                        max_skills_dinos += 1
            except Exception:
                pass

    # Fetch donations count
    donations_count = await Donation.find(
        Donation.userid == userid,
        Donation.product != "non_repayable"
    ).count()

    # Fetch friends count
    friends_count = await Friend.find(
        Friend.userid == userid,
        Friend.type == FriendType.FRIENDS
    ).count()

    # Fetch referrals count
    ref_doc = await Referral.find_one(Referral.userid == userid, Referral.type == ReferralType.GENERAL)
    invite_count = 0
    if ref_doc:
        invite_count = await Referral.find(
            Referral.code == ref_doc.code,
            Referral.type == ReferralType.SUB
        ).count()

    # Fetch quests pct progress
    total_completable = _count_completable_achievements()
    ignored_ids = [a_id for a_id, cfg in ACHIEVEMENTS.get('achievements', {}).items() if cfg.get('ignore_progress', False)]
    unlocked_completable = sum(1 for a in all_user_achievements if a.unlocked_time > 0 and a.achievement_id not in ignored_ids)
    quests_pct = int(unlocked_completable * 100 / total_completable) if total_completable > 0 else 0

    # Fetch collection pct progress
    from bot.models.user import DinoCollection
    from bot.const import DINOS
    total_families = len({v.get('name', '') for v in DINOS.get('elements', {}).values()})
    user_families = await DinoCollection.get_count_families(userid)
    collection_pct = int(user_families * 100 / total_families) if total_families > 0 else 0

    # Backgrounds count
    user_bgs = len(user.saved.get('backgrounds', []))

    def get_progress_stats(ach_id, ach_doc) -> tuple[int, int] | None:
        curr = 0
        if ach_doc:
            if isinstance(ach_doc.progress, list):
                curr = len(ach_doc.progress)
            elif isinstance(ach_doc.progress, (int, float)):
                curr = int(ach_doc.progress)

        target = None
        parts = ach_id.split('_')
        last_part = parts[-1]

        if last_part.isdigit():
            target = int(last_part)
        elif last_part.endswith('m') and last_part[:-1].isdigit():
            target = int(last_part[:-1]) * 1000000
        elif last_part.endswith('k') and last_part[:-1].isdigit():
            target = int(last_part[:-1]) * 1000
        elif last_part.endswith('h') and last_part[:-1].isdigit():
            target = int(last_part[:-1])

        # Overrides/defaults for specific achievements
        if ach_id == "feed_all_food":
            target = total_eat
        elif ach_id == "journey_all_locations":
            target = 5
        elif ach_id == "journey_see_all_npc":
            target = 12
        elif ach_id == "journey_see_all_events":
            target = 74
        elif ach_id == "journey_all_sublocations":
            target = 11
        elif ach_id == "battle_defeat_all_mobs":
            target = 30
        elif ach_id == "all_activities":
            target = 4
        elif ach_id == "all_backgrounds_bought":
            target = 22

        # Assign correct current progress value
        if ach_id.startswith('quests_pct_') or ach_id == 'quests_pct_first':
            curr = quests_pct
        elif ach_id.startswith('quests_failed_'):
            curr = user.settings.get('quests_failed', 0)
        elif ach_id.startswith('quests_'):
            curr = user.settings.get('quests_ended', 0)
        elif ach_id.startswith('dino_count_'):
            curr = dino_count
        elif ach_id.startswith('dino_dead_'):
            curr = user.settings.get('dino_deaths', 0)
        elif ach_id == 'all_backgrounds_bought':
            curr = user_bgs
        elif ach_id.startswith('collection_pct_') or ach_id == 'collection_first_100':
            curr = collection_pct
        elif ach_id.startswith('battle_win_'):
            curr = user.settings.get('battle_wins', 0)
        elif ach_id == 'battle_lose_100':
            curr = user.settings.get('battle_losses', 0)
        elif ach_id.startswith('max_skills_dinos_'):
            curr = max_skills_dinos
        elif ach_id.startswith('lvl_') or ach_id.startswith('first_lvl_'):
            curr = user.lvl
        elif ach_id.startswith('market_sell_'):
            curr = user.settings.get('market_sell_count', 0)
        elif ach_id.startswith('market_coins_'):
            curr = user.settings.get('market_sell_total', 0)
        elif ach_id.startswith('buyer_sell_') or ach_id == 'sell_buyer_1k':
            curr = user.settings.get('buyer_sell_count', 0)
        elif ach_id.startswith('buyer_coins_'):
            curr = user.settings.get('buyer_sell_total', 0)
        elif ach_id.startswith('friends_'):
            curr = friends_count
        elif ach_id.startswith('invite_'):
            curr = invite_count
        elif ach_id.startswith('support_'):
            curr = donations_count
        elif ach_id == 'items_discarded_1000':
            curr = user.settings.get('items_discarded', 0)
        elif ach_id == 'items_transferred_1000':
            curr = user.settings.get('items_transferred', 0)
        elif ach_id == 'blacksmith_lost_1000':
            curr = user.settings.get('blacksmith_lost_items', 0)

        if target is not None:
            if ach_doc and ach_doc.unlocked_time > 0:
                curr = max(curr, target)
            curr = min(curr, target)
            return curr, target
        return None

    def format_unlock_date(unlocked_time: int) -> str:
        dt = datetime.datetime.fromtimestamp(unlocked_time, tz=datetime.timezone.utc)
        return dt.strftime("%d.%m.%Y")

    def render_achievement(ach_id: str) -> str:
        if ach_id not in ach_dict or ach_id == "example":
            return ""
        ach_cfg = ach_dict[ach_id]
        is_unlocked = ach_id in unlocked_ids
        ach_name = t(f"achievements.{ach_id}.name", lang)

        progress_str = ""
        prog = get_progress_stats(ach_id, ach_docs.get(ach_id))
        if prog:
            curr, target = prog
            progress_str = " " + t("achievements.progress", lang, current=curr, target=target)

        if is_unlocked:
            ach_doc = unlocked_ids[ach_id]
            stack_text = f" (x{ach_doc.stack})" if ach_doc.stack > 1 else ""
            date_text = f" — {format_unlock_date(ach_doc.unlocked_time)}"
            desc = t(ach_cfg.get('description', ''), lang) + progress_str
            return f"🏆 *{ach_name}*{stack_text}{date_text}\n└ {desc}\n\n"
        else:
            is_secret = ach_cfg.get('secret', False)
            if is_secret:
                secret_tag = t('achievements.secret_tag', lang)
                secret_desc = t('achievements.secret_desc', lang)
                return f"🔒 *{ach_name}* ({secret_tag})\n└ ❓ {secret_desc}\n\n"
            else:
                short_desc = t(ach_cfg.get('short_description', ''), lang) + progress_str
                return f"🔒 *{ach_name}*\n└ {short_desc}\n\n"

    # Build list of visible groups (skip empty groups)
    visible_groups = []
    for group in display_groups:
        group_key = group.get('key', '')
        group_ach_ids = group.get('achievements', [])

        visible_in_group = []
        for ach_id in group_ach_ids:
            if ach_id not in ach_dict or ach_id == "example":
                continue
            visible_in_group.append(ach_id)

        if visible_in_group:
            # Sort: unlocked first within each group
            visible_in_group.sort(key=lambda aid: 0 if aid in unlocked_ids else 1)
            visible_groups.append((group_key, visible_in_group))

    # Count total achievements excluding "example"
    total_ach = sum(1 for k in ach_dict if k != "example")

    # Paginate by group
    total_groups = len(visible_groups)
    per_page = 1  # one group per page
    max_page = max(total_groups, 1)
    page = max(0, min(page, max_page - 1))

    return_text = t("achievements.profile_header", lang, count=len(unlocked_ids), total=total_ach) + "\n\n"

    if visible_groups:
        group_key, group_ach_ids = visible_groups[page]
        group_name = t(f"achievements.groups.{group_key}", lang)
        return_text += f"*{group_name}*\n\n"
        for ach_id in group_ach_ids:
            return_text += render_achievement(ach_id)

    if max_page > 1:
        return_text += t('user_profile.inventory_page.pages', lang, page=page+1, total_pages=max_page)

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

    if not isinstance(result, bool) and hasattr(result, 'status'):
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