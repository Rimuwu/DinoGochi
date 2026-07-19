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
                        page_type: str, page: int = 0, filter_idx: int = 0):
    buttons = []

    if page_type == 'main':
        # Кнопки перехода в меню просмотра динозавров, достижений и инвентаря
        buttons.append(
            {'🦕': f'user_profile dino {userid} 0',
             '🏆': f'user_profile achievements {userid} 0',
             '🎒': f'user_profile inventory {userid} 0'}
        )

    elif page_type == 'levels':
        lvl_awards = GS.get('lvl_award', {})
        reward_lvls = sorted([int(k) for k in lvl_awards.keys()])
        per_page = 3
        total = len(reward_lvls) if reward_lvls else 41
        max_page = max(1, (total + per_page - 1) // per_page)

        page_plus = page + 1 if page + 1 < max_page else 0
        page_minus = page - 1 if page - 1 >= 0 else max_page - 1

        bts_dct = {
            GS['back_button']: f'user_profile levels {userid} {page_minus}',
            GS['forward_button']: f'user_profile levels {userid} {page_plus}'
        }
        if max_page > 1:
            buttons.append(bts_dct)


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

        # Add single-row rarity filter with 3 buttons between arrows
        rarity_order = ['mythical', 'legendary', 'mystical', 'rare', 'uncommon', 'common']
        existing_rarities = []
        for rank in rarity_order:
            has_item = False
            for item in items:
                item_data = get_item_data(item['items_data']['item_id'])
                if item_data.get('rank', 'common') == rank:
                    has_item = True
                    break
            if has_item:
                existing_rarities.append(rank)

        if existing_rarities:
            L = len(existing_rarities)

            def sort_key(item):
                item_id = item['items_data']['item_id']
                item_data = get_item_data(item_id)
                rank = item_data.get('rank', 'common')
                try:
                    return rarity_order.index(rank)
                except ValueError:
                    return len(rarity_order)

            sorted_items = sorted(items, key=sort_key)

            # slider_idx — window offset (which 3 to show), independent of active
            slider_idx = filter_idx % L

            # Detect active rarity from current page content (independent of slider)
            start_idx = page * per_page
            end_idx = start_idx + per_page
            page_items_slice = sorted_items[start_idx:end_idx]
            if page_items_slice:
                current_rarity = get_item_data(page_items_slice[0]['items_data']['item_id']).get('rank', 'common')
            else:
                current_rarity = existing_rarities[0]

            # Build list of 3 indices to display based on slider_idx
            if L >= 3:
                display_indices = [slider_idx, (slider_idx + 1) % L, (slider_idx + 2) % L]
            else:
                display_indices = list(range(L))

            prev_slider = (slider_idx - 1) % L
            next_slider = (slider_idx + 1) % L

            row_dict = {}
            # Arrows change slider window, stay on same page
            row_dict['⏪'] = f'user_profile inventory {userid} {page} {prev_slider}'

            for idx in display_indices:
                rank = existing_rarities[idx]
                rarity_title = t(f'item_info.rank.{rank}', lang)
                rarity_emoji = rarity_title.split()[0]

                # Clicking filter jumps to first page of that rarity, slider centers on it
                first_pos = next((i for i, item in enumerate(sorted_items) if get_item_data(item['items_data']['item_id']).get('rank', 'common') == rank), 0)
                target_page = first_pos // per_page

                cb_data = f'user_profile inventory {userid} {target_page} {idx}'
                if rank == current_rarity:
                    row_dict[rarity_emoji] = {
                        "callback_data": cb_data,
                        "style": "primary"
                    }
                else:
                    row_dict[rarity_emoji] = cb_data

            row_dict['⏩'] = f'user_profile inventory {userid} {page} {next_slider}'
            buttons.append(row_dict)

            f_idx = slider_idx

        bts_dct = {
            GS['back_button']: f'user_profile inventory {userid} {page_minus} {f_idx}',
            '👤': f'user_profile main {userid} 0',
            GS['forward_button']: f'user_profile inventory {userid} {page_plus} {f_idx}'
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

        from bot.models.user import Achievement
        all_user_achievements = await Achievement.find(Achievement.userid == userid).to_list()
        unlocked_ids = {a.achievement_id for a in all_user_achievements if a.unlocked_time > 0}

        local_display_groups = []
        for g in display_groups:
            local_display_groups.append({
                "key": g.get("key"),
                "achievements": list(g.get("achievements", []))
            })
        arena_group = next((g for g in local_display_groups if g.get("key") == "arena_group"), None)
        if not arena_group:
            arena_group = {"key": "arena_group", "achievements": []}
            local_display_groups.append(arena_group)

        for ach_id in unlocked_ids:
            if ach_id.startswith("arena_season_place_") or ach_id.startswith("arena_streak_seasons_"):
                if ach_id not in arena_group["achievements"]:
                    arena_group["achievements"].append(ach_id)

        visible_group_keys = []
        for group in local_display_groups:
            group_key = group.get('key', '')
            group_ach_ids = group.get('achievements', [])
            visible_in_group = [
                aid for aid in group_ach_ids
                if (aid in ach_dict or aid.startswith("arena_season_place_") or aid.startswith("arena_streak_seasons_")) and aid != "example"
            ]
            if visible_in_group:
                visible_group_keys.append(group_key)

        per_page = 3
        all_flat = []
        for gk in visible_group_keys:
            group = next(g for g in local_display_groups if g.get('key') == gk)
            group_ach_ids = group.get('achievements', [])
            visible_in_group = [
                aid for aid in group_ach_ids
                if (aid in ach_dict or aid.startswith("arena_season_place_") or aid.startswith("arena_streak_seasons_")) and aid != "example"
            ]
            visible_in_group.sort(key=lambda aid: 0 if aid in unlocked_ids else 1)
            all_flat.extend([(gk, aid) for aid in visible_in_group])

        total_visible = len(all_flat)
        max_page = max(1, (total_visible + per_page - 1) // per_page)

        page_plus = page + 1 if page + 1 < max_page else 0
        page_minus = page - 1 if page - 1 >= 0 else max_page - 1

        if visible_group_keys:
            L = len(visible_group_keys)

            # slider_idx — window offset (which 3 to show), independent of active
            slider_idx = filter_idx % L

            # Detect active group from current page content (independent of slider)
            start_idx = page * per_page
            end_idx = start_idx + per_page
            page_items_slice = all_flat[start_idx:end_idx]
            if page_items_slice:
                current_group_key = page_items_slice[0][0]
            else:
                current_group_key = visible_group_keys[0]

            # Build list of 3 indices to display based on slider_idx
            if L >= 3:
                display_indices = [slider_idx, (slider_idx + 1) % L, (slider_idx + 2) % L]
            else:
                display_indices = list(range(L))

            prev_slider = (slider_idx - 1) % L
            next_slider = (slider_idx + 1) % L

            row_dict = {}
            # Arrows change slider window, stay on same page
            row_dict['⏪'] = f'user_profile achievements {userid} {page} {prev_slider}'

            for idx in display_indices:
                gk = visible_group_keys[idx]
                group_title = t(f"achievements.groups.{gk}", lang)
                group_emoji = group_title.split()[0]

                # Clicking filter jumps to first page of that group, slider centers on it
                first_pos = next((i for i, (tmp_gk, _) in enumerate(all_flat) if tmp_gk == gk), 0)
                target_page = first_pos // per_page

                cb_data = f'user_profile achievements {userid} {target_page} {idx}'
                if gk == current_group_key:
                    row_dict[group_emoji] = {
                        "callback_data": cb_data,
                        "style": "primary"
                    }
                else:
                    row_dict[group_emoji] = cb_data

            row_dict['⏩'] = f'user_profile achievements {userid} {page} {next_slider}'
            buttons.append(row_dict)

            f_idx = slider_idx

        bts_dct = {
            GS['back_button']: f'user_profile achievements {userid} {page_minus} {f_idx}',
            '👤': f'user_profile main {userid} 0',
            GS['forward_button']: f'user_profile achievements {userid} {page_plus} {f_idx}'
        }
        if max_page <= 1:
            bts_dct = {
                '👤': f'user_profile main {userid} 0'
            }

        buttons.append(bts_dct)

    return list_to_inline(buttons, 5)

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

async def user_achievements_info(userid: int, lang: str, page: int = 0, is_own_profile: bool = True):
    from bot.const import ACHIEVEMENTS
    from bot.models.user import Achievement
    from bot.modules.items.collect_items import get_all_items
    from bot.redismanager import redis_get, redis_set
    from bot.modules.localization import resolve_custom_emojis
    import datetime

    ach_dict = ACHIEVEMENTS['achievements']
    display_groups = ACHIEVEMENTS.get('display_groups', [])

    # === FAST PATH: full page cache (own profile only) ===
    if is_own_profile:
        _FULL_KEY = f"profile_ach_full:{userid}:{lang}"
        _CACHE_TTL = 300  # 5 minutes
        cached = await redis_get(_FULL_KEY)
        if cached and isinstance(cached, dict):
            max_page = cached.get("max_page", 1)
            page = max(0, min(page, max_page - 1))
            text = cached.get("pages", {}).get(str(page), "")
            if text:
                user = await User().create(userid)
                image = await user.get_avatar()
                return text, image

    # === FULL COMPUTATION (cache miss or foreign profile) ===
    user = await User().create(userid)

    # Get all user achievements (single batch query)
    all_user_achievements = await Achievement.find(
        Achievement.userid == userid
    ).to_list()
    ach_docs = {a.achievement_id: a for a in all_user_achievements}
    unlocked_ids = {a.achievement_id: a for a in all_user_achievements if a.unlocked_time > 0}

    # For foreign profiles — skip all heavy progress queries
    if not is_own_profile:
        dino_count = 0; max_skills_dinos = 0; donations_count = 0
        friends_count = 0; invite_count = 0; quests_pct = 0
        collection_pct = 0; user_bgs = 0; total_eat = 0
    else:
        # Fetch total foods count
        all_items = get_all_items()
        all_eat_ids = {k for k, v in all_items.items() if getattr(v, 'type', '') == 'eat'}
        total_eat = len(all_eat_ids)

        from bot.models.arena import ArenaPlayerModel
        arena_player = await ArenaPlayerModel.find_one(ArenaPlayerModel.userid == userid)
        arena_wins = (arena_player.wins_solo + arena_player.wins_group) if arena_player else 0
        arena_streak = max(arena_player.win_streak_solo, arena_player.win_streak_group) if arena_player else 0

        from bot.models.dinosaur import DinoOwners, Dino
        from bot.models.other import Donation
        from bot.models.user import Friend, Referral
        from bot.models.enums import FriendType, ReferralType
        from bot.modules.user.achievements import _count_completable_achievements

        # Dinos count + max skills check (batch)
        dino_conns = await DinoOwners.find(DinoOwners.owner_id == userid).to_list()
        dino_count = len(dino_conns)
        max_skills_dinos = 0
        dino_ids = []
        for conn in dino_conns:
            try:
                if conn.dino:
                    link = conn.dino
                    if hasattr(link, 'ref') and hasattr(link.ref, 'id'):
                        dino_ids.append(link.ref.id)
                    elif hasattr(link, 'id'):
                        dino_ids.append(link.id)
            except Exception:
                pass
        if dino_ids:
            try:
                dinos = await Dino.find({"_id": {"$in": dino_ids}}).to_list()
                for d in dinos:
                    stats = d.stats or {}
                    if all(stats.get(s, 0) >= 20.0 for s in [
                            'power', 'dexterity', 'intelligence', 'charisma']):
                        max_skills_dinos += 1
            except Exception:
                pass

        donations_count = await Donation.find(
            Donation.userid == userid,
            Donation.product != "non_repayable"
        ).count()

        friends_count = await Friend.find(
            Friend.userid == userid,
            Friend.type == FriendType.FRIENDS
        ).count()

        ref_doc = await Referral.find_one(
            Referral.userid == userid, Referral.type == ReferralType.GENERAL)
        invite_count = 0
        if ref_doc:
            invite_count = await Referral.find(
                Referral.code == ref_doc.code,
                Referral.type == ReferralType.SUB
            ).count()

        total_completable = _count_completable_achievements()
        ignored_ids = [
            a_id for a_id, cfg in ACHIEVEMENTS.get('achievements', {}).items()
            if cfg.get('ignore_progress', False)
        ]
        unlocked_completable = sum(
            1 for a in all_user_achievements
            if a.unlocked_time > 0 and a.achievement_id not in ignored_ids
        )
        quests_pct = int(unlocked_completable * 100 / total_completable) if total_completable > 0 else 0

        from bot.models.user import DinoCollection
        from bot.const import DINOS
        total_families = len({v.get('name', '') for v in DINOS.get('elements', {}).values()})
        user_families = await DinoCollection.get_count_families(userid)
        collection_pct = int(user_families * 100 / total_families) if total_families > 0 else 0

        user_bgs = len(user.saved.get('backgrounds', []))

    # === INNER HELPERS ===
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

        if ach_id == "feed_all_food": target = total_eat
        elif ach_id == "journey_all_locations": target = 5
        elif ach_id == "journey_see_all_npc": target = 12
        elif ach_id == "journey_see_all_events": target = 74
        elif ach_id == "journey_all_sublocations": target = 11
        elif ach_id == "battle_defeat_all_mobs": target = 30
        elif ach_id == "all_activities": target = 4
        elif ach_id == "all_backgrounds_bought": target = 22

        if ach_id.startswith('quests_pct_') or ach_id == 'quests_pct_first': curr = quests_pct
        elif ach_id.startswith('quests_failed_'): curr = user.settings.get('quests_failed', 0)
        elif ach_id.startswith('quests_'): curr = user.settings.get('quests_ended', 0)
        elif ach_id.startswith('dino_count_'): curr = dino_count
        elif ach_id.startswith('dino_dead_'): curr = user.settings.get('dino_deaths', 0)
        elif ach_id == 'all_backgrounds_bought': curr = user_bgs
        elif ach_id.startswith('collection_pct_') or ach_id == 'collection_first_100': curr = collection_pct
        elif ach_id.startswith('battle_win_'): curr = user.settings.get('battle_wins', 0)
        elif ach_id == 'battle_lose_100': curr = user.settings.get('battle_losses', 0)
        elif ach_id.startswith('max_skills_dinos_'): curr = max_skills_dinos
        elif ach_id.startswith('lvl_') or ach_id.startswith('first_lvl_'): curr = user.lvl
        elif ach_id.startswith('market_sell_'): curr = user.settings.get('market_sell_count', 0)
        elif ach_id.startswith('market_coins_'): curr = user.settings.get('market_sell_total', 0)
        elif ach_id.startswith('buyer_sell_') or ach_id == 'sell_buyer_1k': curr = user.settings.get('buyer_sell_count', 0)
        elif ach_id.startswith('buyer_coins_'): curr = user.settings.get('buyer_sell_total', 0)
        elif ach_id.startswith('friends_'): curr = friends_count
        elif ach_id.startswith('invite_'): curr = invite_count
        elif ach_id.startswith('support_'): curr = donations_count
        elif ach_id == 'items_discarded_1000': curr = user.settings.get('items_discarded', 0)
        elif ach_id == 'items_transferred_1000': curr = user.settings.get('items_transferred', 0)
        elif ach_id == 'blacksmith_lost_1000': curr = user.settings.get('blacksmith_lost_items', 0)
        elif ach_id.startswith('arena_wins_'): curr = arena_wins
        elif ach_id.startswith('arena_streak_'): curr = arena_streak

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
        if ach_id.startswith("arena_season_place_") or ach_id.startswith("arena_streak_seasons_"):
            from bot.modules.user.achievements import get_dynamic_achievement_info
            ach_name, desc = get_dynamic_achievement_info(ach_id, lang)
            ach_doc = unlocked_ids.get(ach_id)
            date_text = f" — {format_unlock_date(ach_doc.unlocked_time)}" if ach_doc else ""
            card_text = f"🏆 *{ach_name}*{date_text}\n├ {desc}"
            return f"%%BLOCKQUOTESTART%%{card_text}%%BLOCKQUOTEEND%%\n\n"

        if ach_id not in ach_dict or ach_id == "example":
            return ""
        ach_cfg = ach_dict[ach_id]
        is_unlocked = ach_id in unlocked_ids
        ach_name = t(f"achievements.{ach_id}.name", lang)

        progress_str = ""
        if is_own_profile:
            prog = get_progress_stats(ach_id, ach_docs.get(ach_id))
            if prog:
                curr, target = prog
                progress_str = " " + t("achievements.progress", lang, current=curr, target=target)

        award = ach_cfg.get('award') or {}
        coins = award.get('coins', 0)
        exp = award.get('exp', 0)
        items = award.get('items', [])

        reward_clean_lines = []
        if coins > 0:
            reward_clean_lines.append(f"+{coins} {{custom_emoji:coins}}")
        if exp > 0:
            reward_clean_lines.append(f"+{exp} XP")
        if items:
            from bot.modules.items.item import get_name as get_item_name
            for it in items:
                it_id = it.get('item_id') or it.get('itemid')
                count = it.get('count', 1)
                abilities = it.get('abilities', {})
                if it_id:
                    it_name = get_item_name(it_id, lang, abilities, rare_emoji=False)
                    reward_clean_lines.append(f"{it_name} x{count}")

        reward_str = ""
        if reward_clean_lines:
            rewards_joined = ", ".join(reward_clean_lines)
            reward_str = f"\n└ {rewards_joined}"
            reward_str = resolve_custom_emojis(reward_str)

        if is_unlocked:
            ach_doc = unlocked_ids[ach_id]
            stack_text = f" (x{ach_doc.stack})" if ach_doc.stack > 1 else ""
            date_text = f" — {format_unlock_date(ach_doc.unlocked_time)}"
            desc = t(ach_cfg.get('description', ''), lang) + progress_str + reward_str
            card_text = f"🏆 *{ach_name}*{stack_text}{date_text}\n├ {desc}"
        else:
            is_secret = ach_cfg.get('secret', False)
            if is_secret:
                secret_tag = t('achievements.secret_tag', lang)
                secret_desc = t('achievements.secret_desc', lang)
                card_text = f"🔒 *{ach_name}* ({secret_tag})\n├ ❓ {secret_desc}{reward_str}"
            else:
                short_desc = t(
                    ach_cfg.get('short_description', ''), lang) + progress_str + reward_str
                card_text = f"🔒 *{ach_name}*\n├ {short_desc}"

        return f"%%BLOCKQUOTESTART%%{card_text}%%BLOCKQUOTEEND%%\n\n"

    # === BUILD FLAT LIST ===
    local_display_groups = []
    for g in display_groups:
        local_display_groups.append({
            "key": g.get("key"),
            "achievements": list(g.get("achievements", []))
        })
    arena_group = next((g for g in local_display_groups if g.get("key") == "arena_group"), None)
    if not arena_group:
        arena_group = {"key": "arena_group", "achievements": []}
        local_display_groups.append(arena_group)

    for ach_id in unlocked_ids:
        if ach_id.startswith("arena_season_place_") or ach_id.startswith("arena_streak_seasons_"):
            if ach_id not in arena_group["achievements"]:
                arena_group["achievements"].append(ach_id)

    visible_groups = []
    for group in local_display_groups:
        group_key = group.get('key', '')
        group_ach_ids = group.get('achievements', [])
        visible_in_group = [
            aid for aid in group_ach_ids
            if (aid in ach_dict or aid.startswith("arena_season_place_") or aid.startswith("arena_streak_seasons_")) and aid != "example"
        ]
        if visible_in_group:
            visible_in_group.sort(key=lambda aid: 0 if aid in unlocked_ids else 1)
            visible_groups.append((group_key, visible_in_group))

    total_ach = sum(1 for k in ach_dict if k != "example")
    per_page = 3
    all_flat = [(gk, aid) for gk, aids in visible_groups for aid in aids]
    max_page = max(1, (len(all_flat) + per_page - 1) // per_page)

    group_label = t("achievements.group_label", lang)

    def render_page(p: int) -> str:
        start = p * per_page
        end = start + per_page
        header = t("achievements.profile_header", lang,
                   count=len(unlocked_ids), total=total_ach) + "\n\n"
        text = header
        prev_group = None
        for gk, aid in all_flat[start:end]:
            if gk != prev_group:
                group_name = t(f"achievements.groups.{gk}", lang)
                text += resolve_custom_emojis(
                    f"{{custom_emoji:bookmark}} {group_label} — *{group_name}*\n\n"
                )
                prev_group = gk
            text += render_achievement(aid)
        if max_page > 1:
            text += t('user_profile.inventory_page.pages', lang, page=p+1, total_pages=max_page)
        return text

    # === CACHE ALL PAGES (own profile) or render single page (foreign) ===
    if is_own_profile:
        pages_cache = {str(p): render_page(p) for p in range(max_page)}
        await redis_set(_FULL_KEY, {"max_page": max_page, "pages": pages_cache}, ex=_CACHE_TTL)
        page = max(0, min(page, max_page - 1))
        return_text = pages_cache[str(page)]
    else:
        page = max(0, min(page, max_page - 1))
        return_text = render_page(page)

    image = await user.get_avatar()
    return return_text, image



    # Get all user achievements
    all_user_achievements = await Achievement.find(
        Achievement.userid == userid
    ).to_list()
    ach_docs = {a.achievement_id: a for a in all_user_achievements}
    unlocked_ids = {a.achievement_id: a for a in all_user_achievements if a.unlocked_time > 0}

    # For foreign profiles — skip all heavy progress queries
    if not is_own_profile:
        dino_count = 0
        max_skills_dinos = 0
        donations_count = 0
        friends_count = 0
        invite_count = 0
        quests_pct = 0
        collection_pct = 0
        user_bgs = 0
        total_eat = 0
    else:
        # --- Redis cache for heavy stats ---
        from bot.redismanager import redis_get, redis_set
        _CACHE_KEY = f"profile_ach:{userid}"
        _CACHE_TTL = 300  # 5 minutes

        cached = await redis_get(_CACHE_KEY)
        if cached and isinstance(cached, dict):
            dino_count       = cached.get("dino_count", 0)
            max_skills_dinos = cached.get("max_skills_dinos", 0)
            donations_count  = cached.get("donations_count", 0)
            friends_count    = cached.get("friends_count", 0)
            invite_count     = cached.get("invite_count", 0)
            quests_pct       = cached.get("quests_pct", 0)
            collection_pct   = cached.get("collection_pct", 0)
            user_bgs         = cached.get("user_bgs", 0)
            total_eat        = cached.get("total_eat", 0)
        else:
            # Fetch total foods to calculate progress for feed_all_food dynamically
            all_items = get_all_items()
            all_eat_ids = {k for k, v in all_items.items() if getattr(v, 'type', '') == 'eat'}
            total_eat = len(all_eat_ids)

            # Fetch progress stats asynchronously beforehand
            from bot.models.dinosaur import DinoOwners, Dino
            from bot.models.other import Donation
            from bot.models.user import Friend, Referral
            from bot.models.enums import FriendType, ReferralType
            from bot.modules.user.achievements import _count_completable_achievements

            # Fetch dinos count and max skill count — one batch query
            dino_conns = await DinoOwners.find(DinoOwners.owner_id == userid).to_list()
            dino_count = len(dino_conns)
            max_skills_dinos = 0

            # Batch-fetch all dino ids at once (safely extract ObjectId from link)
            dino_ids = []
            for conn in dino_conns:
                try:
                    if conn.dino:
                        link = conn.dino
                        if hasattr(link, 'ref') and hasattr(link.ref, 'id'):
                            dino_ids.append(link.ref.id)
                        elif hasattr(link, 'id'):
                            dino_ids.append(link.id)
                except Exception:
                    pass
            if dino_ids:
                from bot.models.dinosaur import Dino
                try:
                    dinos = await Dino.find({"_id": {"$in": dino_ids}}).to_list()
                    for d in dinos:
                        stats = d.stats or {}
                        if all(stats.get(s, 0) >= 20.0 for s in [
                                'power', 'dexterity', 'intelligence', 'charisma']):
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
            ref_doc = await Referral.find_one(
                Referral.userid == userid, Referral.type == ReferralType.GENERAL)
            invite_count = 0
            if ref_doc:
                invite_count = await Referral.find(
                    Referral.code == ref_doc.code,
                    Referral.type == ReferralType.SUB
                ).count()

            # Fetch quests pct progress
            total_completable = _count_completable_achievements()
            ignored_ids = [
                a_id for a_id, cfg in ACHIEVEMENTS.get('achievements', {}\
                ).items() if cfg.get('ignore_progress', False)
                ]
            unlocked_completable = sum(
                1 for a in all_user_achievements if a.unlocked_time > 0 and a.achievement_id not in ignored_ids
            )
            quests_pct = int(
                unlocked_completable * 100 / total_completable
                ) if total_completable > 0 else 0

            # Fetch collection pct progress
            from bot.models.user import DinoCollection
            from bot.const import DINOS
            total_families = len({v.get('name', '') for v in DINOS.get('elements', {}).values()})
            user_families = await DinoCollection.get_count_families(userid)
            collection_pct = int(user_families * 100 / total_families) if total_families > 0 else 0

            # Backgrounds count
            user_bgs = len(user.saved.get('backgrounds', []))

            # Store in Redis cache
            await redis_set(_CACHE_KEY, {
                "dino_count": dino_count,
                "max_skills_dinos": max_skills_dinos,
                "donations_count": donations_count,
                "friends_count": friends_count,
                "invite_count": invite_count,
                "quests_pct": quests_pct,
                "collection_pct": collection_pct,
                "user_bgs": user_bgs,
                "total_eat": total_eat,
            }, ex=_CACHE_TTL)

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
        if is_own_profile:
            prog = get_progress_stats(ach_id, ach_docs.get(ach_id))
            if prog:
                curr, target = prog
                progress_str = " " + t("achievements.progress", lang, current=curr, target=target)

        # Get award text
        award = ach_cfg.get('award') or {}
        coins = award.get('coins', 0)
        exp = award.get('exp', 0)
        items = award.get('items', [])

        reward_clean_lines = []
        if coins > 0:
            reward_clean_lines.append(f"+{coins} {{custom_emoji:coins}}")
        if exp > 0:
            reward_clean_lines.append(f"+{exp} XP")
        if items:
            from bot.modules.items.item import get_name as get_item_name
            for it in items:
                it_id = it.get('item_id') or it.get('itemid')
                count = it.get('count', 1)
                abilities = it.get('abilities', {})
                if it_id:
                    it_name = get_item_name(it_id, lang, abilities, rare_emoji=False)
                    reward_clean_lines.append(f"{it_name} x{count}")

        reward_str = ""
        if reward_clean_lines:
            rewards_joined = ", ".join(reward_clean_lines)
            reward_str = f"\n└ {rewards_joined}"
            from bot.modules.localization import resolve_custom_emojis
            reward_str = resolve_custom_emojis(reward_str)

        if is_unlocked:
            ach_doc = unlocked_ids[ach_id]
            stack_text = f" (x{ach_doc.stack})" if ach_doc.stack > 1 else ""
            date_text = f" — {format_unlock_date(ach_doc.unlocked_time)}"
            desc = t(ach_cfg.get('description', ''), lang) + progress_str + reward_str
            card_text = f"🏆 *{ach_name}*{stack_text}{date_text}\n├ {desc}"
        else:
            is_secret = ach_cfg.get('secret', False)
            if is_secret:
                secret_tag = t('achievements.secret_tag', lang)
                secret_desc = t('achievements.secret_desc', lang)
                card_text = f"🔒 *{ach_name}* ({secret_tag})\n├ ❓ {secret_desc}{reward_str}"
            else:
                short_desc = t(
                    ach_cfg.get('short_description', ''), lang) + progress_str + reward_str
                card_text = f"🔒 *{ach_name}*\n├ {short_desc}"

        return f"%%BLOCKQUOTESTART%%{card_text}%%BLOCKQUOTEEND%%\n\n"

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

    # Flatten all achievements for paging (N per page)
    per_page = 3
    all_flat = [(gk, aid) for gk, aids in visible_groups for aid in aids]
    total_flat = len(all_flat)
    max_page = max(1, (total_flat + per_page - 1) // per_page)
    page = max(0, min(page, max_page - 1))

    return_text = t("achievements.profile_header", lang,
    count=len(unlocked_ids), total=total_ach) + "\n\n"

    start = page * per_page
    end = start + per_page
    page_items = all_flat[start:end]

    prev_group = None
    for group_key, ach_id in page_items:
        if group_key != prev_group:
            from bot.modules.localization import resolve_custom_emojis
            group_label = t("achievements.group_label", lang)
            group_name = t(f"achievements.groups.{group_key}", lang)
            group_header = resolve_custom_emojis(f"{{custom_emoji:bookmark}} {group_label} — *{group_name}*\n\n")
            return_text += group_header
            prev_group = group_key
        return_text += render_achievement(ach_id)

    if max_page > 1:
        return_text += t('user_profile.inventory_page.pages', lang, page=page+1, total_pages=max_page)

    image = await user.get_avatar()
    return return_text, image


async def user_info(userid: int, lang: str, secret: bool = False, 
                    name: str | None = None):
    from bot.redismanager import redis_get, redis_set
    from bot.modules.user.avatar import get_avatar
    
    _CACHE_KEY = f"user_info_cache:{userid}:{lang}:{secret}:{name or ''}"
    _CACHE_TTL = 15  # 15 seconds cache
    
    try:
        cached = await redis_get(_CACHE_KEY)
        if cached and isinstance(cached, dict):
            avatar = cached.get('avatar')
            if not avatar or not isinstance(avatar, str):
                avatar = await get_avatar(userid)
            return cached['text'], avatar
    except Exception:
        pass

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
        
    user_coins = f"{user.coins:,}".replace(",", ".")
    user_super_coins = f"{user.super_coins:,}".replace(",", ".")
    
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
    # Fetch rating positions in parallel
    from bot.redismanager import redis_get
    import asyncio
    
    r_keys = ['lvl', 'coins', 'super', 'dontaion_all', 'arena_solo', 'arena_group']
    r_results = await asyncio.gather(*[redis_get(f'rating:{rk}') for rk in r_keys], return_exceptions=True)
    
    places = {}
    for r_key, r_data in zip(r_keys, r_results):
        if r_data and isinstance(r_data, dict) and userid in r_data.get('ids', []):
            places[r_key] = r_data['ids'].index(userid) + 1
        else:
            places[r_key] = "1000+"

    def format_place(place):
        if place == 1:
            return "{custom_emoji:top1}"
        elif place == 2:
            return "{custom_emoji:top2}"
        elif place == 3:
            return "{custom_emoji:top3}"
        elif place == "1000+":
            return "1000+"
        return f"#{place}"

    if secret:
        lvl_place = hide_text
        coins_place = hide_text
        super_place = hide_text
        donate_place = hide_text
        arena_solo_place = hide_text
        arena_group_place = hide_text
    else:
        lvl_place = format_place(places['lvl'])
        coins_place = format_place(places['coins'])
        super_place = format_place(places['super'])
        donate_place = format_place(places['dontaion_all'])
        arena_solo_place = format_place(places['arena_solo'])
        arena_group_place = format_place(places['arena_group'])

    rating_places_text = t('user_profile.rating_places', lang,
                           lvl_place=lvl_place,
                           coins_place=coins_place,
                           super_place=super_place,
                           donate_place=donate_place,
                           arena_solo_place=arena_solo_place,
                           arena_group_place=arena_group_place)

    return_text += t('user_profile.level', lang,
                     lvl=f"{user.lvl:,}".replace(",", "."),
                     xp_now=f"{user.xp:,}".replace(",", "."),
                     max_xp=f"{max_lvl_xp(user.lvl):,}".replace(",", "."),
                     coins=user_coins,
                     super_coins=user_super_coins,
                     boost=round(await xpboost_percent(userid), 1),
                     )
    return_text += '\n\n'
    return_text += rating_places_text
    return_text += '\n\n'

    return_text += t('user_profile.friends', lang,
                     friends_col=friends_count,
                     requests_col=request_count
                     )

    # Calculate achievements count
    from bot.models.user import Achievement
    from bot.const import ACHIEVEMENTS

    all_user_achievements = await Achievement.find(
        Achievement.userid == userid
    ).to_list()

    unlocked_simple = 0
    unlocked_secret = 0
    ach_dict = ACHIEVEMENTS.get('achievements', {})
    
    for a in all_user_achievements:
        if a.unlocked_time > 0:
            ach_cfg = ach_dict.get(a.achievement_id)
            if ach_cfg:
                is_secret = False
                if isinstance(ach_cfg, dict):
                    is_secret = ach_cfg.get('secret', False)
                else:
                    is_secret = getattr(ach_cfg, 'secret', False)
                
                if is_secret:
                    unlocked_secret += 1
                else:
                    unlocked_simple += 1

    total_simple = 0
    total_secret = 0
    for ach_id, ach_cfg in ach_dict.items():
        if ach_id == "example":
            continue
        is_secret = False
        if isinstance(ach_cfg, dict):
            is_secret = ach_cfg.get('secret', False)
        else:
            is_secret = getattr(ach_cfg, 'secret', False)
        
        if is_secret:
            total_secret += 1
        else:
            total_simple += 1

    if secret:
        normal_col = '`' + hide_text + '`'
        secret_col = '`' + hide_text + '`'
    else:
        normal_col = str(unlocked_simple)
        secret_col = str(unlocked_secret)

    achievements_text = t('user_profile.achievements_count', lang,
                          normal=normal_col,
                          total_normal=total_simple,
                          secret=secret_col,
                          total_secret=total_secret)
    
    return_text += '\n\n'
    return_text += achievements_text

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
    else:
        count = f"{count:,}".replace(",", ".")
        rarity_counts = {key: f"{val:,}".replace(",", ".") for key, val in rarity_counts.items()}

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
            return_text += t('user_profile.market.earned', lang, coins=f"{market.earned:,}".replace(",", "."))

    if secret:
        return_text += '\n\n'
        return_text += t('user_profile.secret', lang)

    avatar_val = await user.get_avatar()
    try:
        avatar_str = avatar_val if isinstance(avatar_val, str) else ""
        await redis_set(_CACHE_KEY, {'text': return_text, 'avatar': avatar_str}, ex=_CACHE_TTL)
    except Exception:
        pass

    return return_text, avatar_val






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

async def user_levels_info(userid: int, lang: str, page: int = 0):
    from bot.const import GAME_SETTINGS as GS
    from bot.modules.localization import resolve_custom_emojis
    from bot.modules.items.item import get_name as get_item_name

    user = await User().create(userid)
    user_lvl = user.lvl

    lvl_awards = GS.get('lvl_award', {})
    reward_lvls = sorted([int(k) for k in lvl_awards.keys()])
    if not reward_lvls:
        reward_lvls = list(range(5, 205, 5))

    per_page = 3
    max_page = max(1, (len(reward_lvls) + per_page - 1) // per_page)
    page = max(0, min(page, max_page - 1))

    text = t("levels_info.header", lang, lvl=user_lvl) + "\n\n"

    start = page * per_page
    end = start + per_page

    special_unlocks = {
        2: t("levels_info.unlock_market", lang),
        10: t("levels_info.unlock_arena", lang),
        20: t("levels_info.unlock_dino_slot", lang),
        40: t("levels_info.unlock_dino_slot", lang),
        60: t("levels_info.unlock_dino_slot", lang),
        80: t("levels_info.unlock_dino_slot", lang)
    }

    for lvl in reward_lvls[start:end]:
        str_lvl = str(lvl)
        award = lvl_awards.get(str_lvl, {})
        coins = award.get('coins', 0)
        super_coins = award.get('super_coins', 0)
        items = award.get('items', [])

        reward_parts = []
        if coins > 0:
            reward_parts.append(f"+{coins} {{custom_emoji:coins}}")
        if super_coins > 0:
            reward_parts.append(f"+{super_coins} {{custom_emoji:super_coins}}")
        if items:
            for it in items:
                it_id = it.get('item_id') or it.get('itemid')
                count = it.get('count', 1)
                abilities = it.get('abilities', {})
                if it_id:
                    it_name = get_item_name(it_id, lang, abilities, rare_emoji=False)
                    reward_parts.append(f"{it_name} x{count}")

        rewards_str = ", ".join(reward_parts) if reward_parts else t("levels_info.no_rewards", lang)

        status_icon = "✅" if user_lvl >= lvl else "🔒"
        lvl_title = t("levels_info.lvl_title", lang, status=status_icon, lvl=lvl)
        
        if lvl in special_unlocks:
            content = f"├ 🎁 {t('levels_info.reward_label', lang)}: {rewards_str}\n└ {special_unlocks[lvl]}"
        else:
            content = f"└ 🎁 {t('levels_info.reward_label', lang)}: {rewards_str}"

        card_text = f"{lvl_title}\n{content}"
        text += f"%%BLOCKQUOTESTART%%{card_text}%%BLOCKQUOTEEND%%\n\n"

    if max_page > 1:
        text += t('user_profile.inventory_page.pages', lang, page=page+1, total_pages=max_page)

    text = resolve_custom_emojis(text)
    image = await user.get_avatar()
    return text, image