import time
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.exec import bot
from bot.models.user import User
from bot.models.items import Item
from bot.models.arena import ArenaPlayerModel, ArenaSeasonModel, ArenaQueueModel, ArenaMatchModel, ArenaBattleModel
from bot.modules.localization import t, get_lang
from bot.modules.data_format import list_to_inline
from bot.const import GAME_SETTINGS
from bot.handlers.arena import get_player_or_create
from bot.modules.logs import log

async def check_matchmaking():
    current_time = int(time.time())
    arena_cfg = GAME_SETTINGS.get('arena', {})
    confirm_timeout = arena_cfg.get('confirm_timeout', 30)

    for category in ['solo', 'group']:
        queue = await ArenaQueueModel.find(ArenaQueueModel.category == category).sort("joined_time").to_list()
        matched_users = set()

        for i in range(len(queue)):
            a = queue[i]
            if a.userid in matched_users:
                continue

            for j in range(i + 1, len(queue)):
                b = queue[j]
                if b.userid in matched_users:
                    continue

                wait_a = current_time - a.joined_time
                wait_b = current_time - b.joined_time
                
                delta_a = 50 + (wait_a // 15) * 50
                delta_b = 50 + (wait_b // 15) * 50
                allowed_delta = max(delta_a, delta_b)

                if abs(a.elo - b.elo) <= allowed_delta:
                    # Check opponent cooldown (from settings.json, default 30 mins = 1800s)
                    same_opponent_cooldown = arena_cfg.get('same_opponent_cooldown', 1800)
                    cooldown_cutoff = current_time - same_opponent_cooldown
                    recent_battle = await ArenaBattleModel.find_one(
                        {"$or": [
                            {"userid_a": a.userid, "userid_b": b.userid},
                            {"userid_a": b.userid, "userid_b": a.userid}
                        ],
                        "battle_time": {"$gte": cooldown_cutoff}}
                    )
                    if recent_battle:
                        continue

                    # Match found!
                    matched_users.add(a.userid)
                    matched_users.add(b.userid)

                    # Delete queue entries
                    await a.delete()
                    await b.delete()

                    # Get names
                    user_a = await User.find_one(User.userid == a.userid)
                    user_b = await User.find_one(User.userid == b.userid)
                    name_a = user_a.name if (user_a and user_a.name) else f"Player_{a.userid}"
                    name_b = user_b.name if (user_b and user_b.name) else f"Player_{b.userid}"

                    # Create match
                    match = ArenaMatchModel(
                        player_a_id=a.userid,
                        player_b_id=b.userid,
                        player_a_name=name_a,
                        player_b_name=name_b,
                        player_a_dinos=a.dino_ids,
                        player_b_dinos=b.dino_ids,
                        player_a_bag=a.bag_items,
                        player_b_bag=b.bag_items,
                        player_a_free=a.is_free_attempt,
                        player_b_free=b.is_free_attempt,
                        category=category,
                        created_at=current_time,
                        expires_at=current_time + confirm_timeout
                    )
                    await match.insert()

                    # Send messages to both
                    lang_a = await get_lang(a.userid)
                    lang_b = await get_lang(b.userid)

                    buttons_a = [
                        [
                            {"text": t("arena.btn_ready", lang_a, default="🟢 Готов"), "callback_data": f"arena_confirm:ready:{match.id}"},
                            {"text": t("arena.btn_decline", lang_a, default="🔴 Отклонить"), "callback_data": f"arena_confirm:decline:{match.id}"}
                        ]
                    ]
                    buttons_b = [
                        [
                            {"text": t("arena.btn_ready", lang_b, default="🟢 Готов"), "callback_data": f"arena_confirm:ready:{match.id}"},
                            {"text": t("arena.btn_decline", lang_b, default="🔴 Отклонить"), "callback_data": f"arena_confirm:decline:{match.id}"}
                        ]
                    ]

                    markup_a = list_to_inline(buttons_a)
                    markup_b = list_to_inline(buttons_b)

                    text_a = t("arena.match_found", lang_a, opponent=name_b, default=f"⚔️ <b>Противник найден!</b>\n\nВаш соперник: {name_b}\nПодтвердите участие за 30 секунд:")
                    text_b = t("arena.match_found", lang_b, opponent=name_a, default=f"⚔️ <b>Противник найден!</b>\n\nВаш соперник: {name_a}\nПодтвердите участие за 30 секунд:")

                    try:
                        # Clear search states
                        from bot.modules.get_state import get_state
                        state_a = await get_state(a.userid, a.userid)
                        await state_a.clear()
                        msg_a = await bot.send_message(a.userid, text_a, reply_markup=markup_a)
                        match.player_a_msg_id = msg_a.message_id
                    except Exception:
                        pass

                    try:
                        state_b = await get_state(b.userid, b.userid)
                        await state_b.clear()
                        msg_b = await bot.send_message(b.userid, text_b, reply_markup=markup_b)
                        match.player_b_msg_id = msg_b.message_id
                    except Exception:
                        pass

                    await match.save()
                    break

async def check_confirm_timeouts():
    current_time = int(time.time())
    expired_matches = await ArenaMatchModel.find(ArenaMatchModel.expires_at <= current_time).to_list()
    for match in expired_matches:
        await handle_declined_match(match.id)

async def handle_declined_match(match_id: ObjectId):
    match = await ArenaMatchModel.find_one(ArenaMatchModel.id == match_id)
    if not match:
        return

    # Delete match record
    await match.delete()

    current_time = int(time.time())
    lang_a = await get_lang(match.player_a_id)
    lang_b = await get_lang(match.player_b_id)

    # Determine status of ready flags
    a_declined = (match.player_a_ready is not True)
    b_declined = (match.player_b_ready is not True)

    # 1. Apply ban and refund to player A if declined
    if a_declined:
        player_a = await get_player_or_create(match.player_a_id)
        player_a.ban_end_time = current_time + 300
        await player_a.save()
        
        # Refund A
        for item in match.player_a_bag:
            await Item.add(match.player_a_id, item["item_id"], item["count"], item.get("abilities", {}))
        
        if match.player_a_free:
            player_a.free_battles_used = max(0, player_a.free_battles_used - 1)
        else:
            player_a.tickets_used = max(0, player_a.tickets_used - 1)
            await Item.add(match.player_a_id, "wornoutticket", 1)
        await player_a.save()

        # Delete message
        if match.player_a_msg_id:
            try:
                await bot.delete_message(match.player_a_id, match.player_a_msg_id)
            except Exception:
                pass
        await bot.send_message(match.player_a_id, t("arena.ban_applied_msg", lang_a, default="❌ Вы проигнорировали или отклонили приглашение на бой. Поиск заблокирован на 5 минут."))

    else:
        # A was ready, B declined! A goes back to queue!
        player_a = await get_player_or_create(match.player_a_id)
        elo_a = player_a.elo_solo if match.category == 'solo' else player_a.elo_group
        
        queue_entry = ArenaQueueModel(
            userid=match.player_a_id,
            dino_ids=match.player_a_dinos,
            category=match.category,
            joined_time=match.created_at,  # preserve original search priority
            elo=elo_a,
            bag_items=match.player_a_bag,
            is_free_attempt=match.player_a_free
        )
        await queue_entry.insert()

        if match.player_a_msg_id:
            try:
                await bot.delete_message(match.player_a_id, match.player_a_msg_id)
            except Exception:
                pass
        await bot.send_message(match.player_a_id, t("arena.opponent_declined_msg", lang_a, default="⚠️ Противник отклонил или проигнорировал приглашение. Вы возвращены в очередь."))

    # 2. Apply ban and refund to player B if declined
    if b_declined:
        player_b = await get_player_or_create(match.player_b_id)
        player_b.ban_end_time = current_time + 300
        await player_b.save()
        
        # Refund B
        for item in match.player_b_bag:
            await Item.add(match.player_b_id, item["item_id"], item["count"], item.get("abilities", {}))
        
        if match.player_b_free:
            player_b.free_battles_used = max(0, player_b.free_battles_used - 1)
        else:
            player_b.tickets_used = max(0, player_b.tickets_used - 1)
            await Item.add(match.player_b_id, "wornoutticket", 1)
        await player_b.save()

        if match.player_b_msg_id:
            try:
                await bot.delete_message(match.player_b_id, match.player_b_msg_id)
            except Exception:
                pass
        await bot.send_message(match.player_b_id, t("arena.ban_applied_msg", lang_b, default="❌ Вы проигнорировали или отклонили приглашение на бой. Поиск заблокирован на 5 минут."))

    else:
        # B was ready, A declined! B goes back to queue!
        player_b = await get_player_or_create(match.player_b_id)
        elo_b = player_b.elo_solo if match.category == 'solo' else player_b.elo_group
        
        queue_entry = ArenaQueueModel(
            userid=match.player_b_id,
            dino_ids=match.player_b_dinos,
            category=match.category,
            joined_time=match.created_at,
            elo=elo_b,
            bag_items=match.player_b_bag,
            is_free_attempt=match.player_b_free
        )
        await queue_entry.insert()

        if match.player_b_msg_id:
            try:
                await bot.delete_message(match.player_b_id, match.player_b_msg_id)
            except Exception:
                pass
        await bot.send_message(match.player_b_id, t("arena.opponent_declined_msg", lang_b, default="⚠️ Противник отклонил или проигнорировал приглашение. Вы возвращены в очередь."))

async def check_top_decay():
    current_time = int(time.time())
    arena_cfg = GAME_SETTINGS.get('arena', {})
    inactivity_limit = arena_cfg.get('decay_inactivity_hours', 48) * 3600
    decay_loss = arena_cfg.get('decay_daily_loss', 20)

    # We run decay check only once a day
    # Loop over all active players
    players = await ArenaPlayerModel.find_all().to_list()
    for p in players:
        # Check solo inactivity decay
        if p.elo_solo > 1000 and (current_time - p.last_battle_time > inactivity_limit):
            if current_time - p.last_decay_time >= 24 * 3600:
                p.elo_solo = max(1000, p.elo_solo - decay_loss)
                p.last_decay_time = current_time
                await p.save()
                
                lang = await get_lang(p.userid)
                try:
                    await bot.send_message(p.userid, t("arena.decay_applied_solo", lang, loss=decay_loss, default=f"⚠️ С вашего Solo-рейтинга Арены списано {decay_loss} очков из-за неактивности более 48 часов!"))
                except Exception:
                    pass

        # Check group inactivity decay
        if p.elo_group > 1000 and (current_time - p.last_battle_time > inactivity_limit):
            if current_time - p.last_decay_time >= 24 * 3600:
                p.elo_group = max(1000, p.elo_group - decay_loss)
                p.last_decay_time = current_time
                await p.save()

                lang = await get_lang(p.userid)
                try:
                    await bot.send_message(p.userid, t("arena.decay_applied_group", lang, loss=decay_loss, default=f"⚠️ С вашего Group-рейтинга Арены списано {decay_loss} очков из-за неактивности более 48 часов!"))
                except Exception:
                    pass

def generate_season_rewards() -> dict:
    import random
    from bot.modules.items.item import ITEMS
    from bot.modules.items.item import get_name
    arena_cfg = GAME_SETTINGS.get('arena', {})
    rewards_config = arena_cfg.get('rewards_config', {})
    
    generated = {}
    for cat in ['solo', 'group']:
        generated[cat] = {}
        cat_cfg = rewards_config.get(cat, {})
        for place in ['1', '2', '3']:
            place_cfg = cat_cfg.get(place, {})
            
            # Select random coins
            coins_opts = place_cfg.get('coins_options', [1000])
            coins = random.choice(coins_opts)
            
            # Select random super coins
            sc_opts = place_cfg.get('super_coins_options', [10])
            super_coins = random.choice(sc_opts)
            
            # Select random items from groups
            items = []
            item_groups = place_cfg.get('item_groups', [])
            items_count = place_cfg.get('items_count', 1)
            
            matching_item_ids = []
            for item_id, item_obj in ITEMS.items():
                item_groups_list = getattr(item_obj, 'groups', []) or []
                if any(g in item_groups_list for g in item_groups):
                    matching_item_ids.append(item_id)
            
            if matching_item_ids and items_count > 0:
                for _ in range(items_count):
                    selected_id = random.choice(matching_item_ids)
                    existing = next((it for it in items if it['item_id'] == selected_id), None)
                    if existing:
                        existing['count'] += 1
                    else:
                        items.append({"item_id": selected_id, "count": 1})
            
            generated[cat][place] = {
                "coins": coins,
                "super_coins": super_coins,
                "items": items
            }
    return generated

async def check_and_award_season_achievements(userid: int, category: str, place: int, current_season_num: int):
    try:
        from bot.modules.user.achievements import award_achievement_to_user
        
        # 1. Award placement achievement
        ach_id = f"arena_season_place<i>{category}</i>{place}_{current_season_num}"
        await award_achievement_to_user(userid, ach_id)
        
        # 2. Check and award streak achievement for 1st place
        if place == 1:
            from bot.models.user import Achievement
            streak = 1
            prev_season = current_season_num - 1
            while prev_season > 0:
                prev_ach_id = f"arena_season_place<i>{category}</i>1_{prev_season}"
                exists = await Achievement.find_one(
                    Achievement.userid == userid,
                    Achievement.achievement_id == prev_ach_id,
                    Achievement.unlocked_time > 0
                )
                if exists:
                    streak += 1
                    prev_season -= 1
                else:
                    break
                    
            if streak >= 2:
                streak_ach_id = f"arena_streak_seasons<i>{category}</i>{streak}"
                await award_achievement_to_user(userid, streak_ach_id)
    except Exception as e:
        log(f"Error awarding seasonal achievements for user {userid}: {e}", lvl=3, prefix="arena_tasks")

async def roll_over_season(season: ArenaSeasonModel):
    current_time = int(time.time())
    arena_cfg = GAME_SETTINGS.get('arena', {})
    rewards = season.rewards or {}

    # Solo Leaderboard top 3
    top_solo = await ArenaPlayerModel.find(ArenaPlayerModel.elo_solo > 1000).sort("-elo_solo").limit(3).to_list()
    # Group Leaderboard top 3
    top_group = await ArenaPlayerModel.find(ArenaPlayerModel.elo_group > 1000).sort("-elo_group").limit(3).to_list()

    # Distribute solo rewards
    for idx, p in enumerate(top_solo, 1):
        place_rewards = rewards.get('solo', {}).get(str(idx), {})
        if place_rewards:
            await distribute_rewards(p.userid, idx, "solo", place_rewards)
        await check_and_award_season_achievements(p.userid, "solo", idx, season.season_number)

    # Distribute group rewards
    for idx, p in enumerate(top_group, 1):
        place_rewards = rewards.get('group', {}).get(str(idx), {})
        if place_rewards:
            await distribute_rewards(p.userid, idx, "group", place_rewards)
        await check_and_award_season_achievements(p.userid, "group", idx, season.season_number)

    # Reset all ratings in database
    await ArenaPlayerModel.find_all().update({"$set": {
        "elo_solo": 1000,
        "elo_group": 1000,
        "win_streak_solo": 0,
        "win_streak_group": 0
    }})

    # Start new season
    season.season_number += 1
    season.start_time = current_time
    duration_days = arena_cfg.get('season_duration_days', 30)
    season.end_time = current_time + duration_days * 24 * 3600
    season.rewards = generate_season_rewards()
    await season.save()

async def distribute_rewards(userid: int, place: int, category: str, place_rewards: dict):
    from bot.modules.items.item import get_name
    user = await User.find_one(User.userid == userid)
    if not user:
        return

    coins = place_rewards.get("coins", 0)
    super_coins = place_rewards.get("super_coins", 0)
    items = place_rewards.get("items", [])

    # Apply balances
    if coins > 0:
        user.coins += coins
    if super_coins > 0:
        # Assuming user has a super_coins attribute
        if hasattr(user, 'super_coins'):
            user.super_coins += super_coins
        elif hasattr(user, 'donat_coins'):
            user.donat_coins += super_coins
    await user.save()

    # Apply items
    items_desc = []
    for it in items:
        item_id = it["item_id"]
        count = it["count"]
        await Item.add(userid, item_id, count)
        
        # Get localized name
        name = get_name(item_id, user.settings.get('lang', 'ru'))
        items_desc.append(f"{name} x{count}")

    lang = await get_lang(userid)
    items_str = ", ".join(items_desc) if items_desc else t("arena.no_items", lang, default="нет")

    msg = t("arena.season_rewards_message", lang,
            place=place,
            category=category.upper(),
            coins=coins,
            super_coins=super_coins,
            items=items_str,
            default=f"🏆 <b>Поздравляем!</b>\n\nВы заняли <b>{place}-е место</b> в категории <b>{category.upper()}</b> на PvP Арене по итогам сезона!\n\n🎁 Ваши награды:\n🪙 Монеты: +{coins}\n💎 Супер монеты: +{super_coins}\n🎟️ Предметы: {items_str}\n\nНаграды начислены на ваш баланс и в инвентарь!")

    try:
        await bot.send_message(userid, msg)
    except Exception:
        pass

async def check_arena_season_loop():
    season = await ArenaSeasonModel.find_one()
    if not season:
        current_time = int(time.time())
        duration_days = GAME_SETTINGS.get('arena', {}).get('season_duration_days', 30)
        rewards = generate_season_rewards()
        season = ArenaSeasonModel(
            season_number=1,
            start_time=current_time,
            end_time=current_time + duration_days * 24 * 3600,
            rewards=rewards
        )
        await season.insert()
        return

    if int(time.time()) >= season.end_time:
        await roll_over_season(season)

def get_arena_status() -> tuple[bool, int]:
    """
    Returns (is_open, seconds_remaining)
    If is_open is True: seconds_remaining until arena closes.
    If is_open is False: seconds_remaining until arena opens.
    """
    arena_cfg = GAME_SETTINGS.get('arena', {})
    interval_hours = arena_cfg.get('schedule_interval_hours', 6)
    open_hours = arena_cfg.get('open_duration_hours', 1)

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((now - start_of_day).total_seconds())

    interval_seconds = interval_hours * 3600
    open_seconds = open_hours * 3600

    offset = seconds_since_midnight % interval_seconds
    if offset < open_seconds:
        remaining = open_seconds - offset
        return True, remaining
    else:
        remaining = interval_seconds - offset
        return False, remaining

async def clear_queue_if_closed():
    is_open, _ = get_arena_status()
    if not is_open:
        queue_entries = await ArenaQueueModel.find_all().to_list()
        if queue_entries:
            for entry in queue_entries:
                userid = entry.userid
                lang = await get_lang(userid)

                await entry.delete()

                player = await get_player_or_create(userid)
                if entry.is_free_attempt:
                    player.free_battles_used = max(0, player.free_battles_used - 1)
                else:
                    player.tickets_used = max(0, player.tickets_used - 1)
                    await Item.add(userid, "wornoutticket", 1)
                await player.save()

                for item in entry.bag_items:
                    await Item.add(userid, item["item_id"], item["count"], item.get("abilities", {}))

                try:
                    msg = t("arena.closed_queue_evict", lang, default="🔴 Арена закрылась. Вы убраны из очереди поиска, а все использованные ресурсы и билеты возвращены.")
                    await bot.send_message(userid, msg)
                except Exception:
                    pass

async def arena_task_worker():
    while True:
        try:
            is_open, _ = get_arena_status()
            if is_open:
                await check_matchmaking()
            else:
                await clear_queue_if_closed()
            await check_confirm_timeouts()
            await check_arena_season_loop()
        except Exception as e:
            log(f"Arena task worker error: {e}", lvl=3, prefix="arena_tasks")
        await asyncio.sleep(3.0)

async def arena_decay_worker():
    while True:
        try:
            await check_top_decay()
        except Exception as e:
            log(f"Arena decay worker error: {e}", lvl=3, prefix="arena_decay")
        # Run decay check every hour
        await asyncio.sleep(3600)

if __name__ != '__main__':
    from bot.config import conf
    from bot.taskmanager import add_task
    if conf.active_tasks:
        add_task(arena_task_worker, 3.0, 5.0)
        add_task(arena_decay_worker, 3600.0, 10.0)
