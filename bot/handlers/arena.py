import time
import asyncio
import uuid
import re
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.modules.logs import log

from bot.exec import main_router, bot
from bot.modules.localization import t, get_lang, get_data, resolve_custom_emojis
from bot.modules.markup import markups_menu as m
from bot.modules.data_format import list_to_inline, seconds_to_str, md_to_html
from bot.models.user import User
from bot.models.dinosaur import Dino, DinoStatus
from bot.models.items import Item
from bot.models.arena import ArenaPlayerModel, ArenaSeasonModel, ArenaQueueModel, ArenaMatchModel, ArenaBattleModel
from bot.const import GAME_SETTINGS
from bot.modules.get_state import get_state
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.translated_text import Text
from bot.modules.states_fabric.state_handlers import ChooseDinoListHandler, ChooseStepHandler, ChooseDinoHandler
from bot.modules.states_fabric.steps_datatype import MultiInventoryStepData, StepMessage
from bot.modules.items.item import get_item_capacity, get_name, get_data as get_item_data
from bot.modules.combat.auto_combat import AutoCombat, CombatParticipant
from bot.modules.logs import log

class ArenaStates(StatesGroup):
    searching = State()

async def get_player_or_create(userid: int) -> ArenaPlayerModel:
    player = await ArenaPlayerModel.find_one(ArenaPlayerModel.userid == userid)
    if not player:
        player = ArenaPlayerModel(userid=userid)
        await player.insert()
    
    # Check date reset (daily UTC)
    from datetime import datetime, timezone
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if player.last_reset_date != today_utc:
        player.free_battles_used = 0
        player.tickets_used = 0
        player.last_reset_date = today_utc
        await player.save()
    
    return player

async def get_rewards_details_text(lang: str) -> str:
    season = await ArenaSeasonModel.find_one()
    if season and season.rewards:
        rewards = season.rewards
    else:
        from bot.tasks.arena_tasks import generate_season_rewards
        rewards = generate_season_rewards()
    
    lines = []
    lines.append(t("arena.season_rewards_details_header", lang, default="🎁 <b>Награды сезона (1-3 место):</b>\n"))
    
    for cat in ['solo', 'group']:
        cat_title = t("arena.btn_solo", lang, default="👤 Соло") if cat == 'solo' else t("arena.btn_group", lang, default="👥 Групповой")
        lines.append(f"<b>{cat_title}:</b>")
        
        cat_rewards = rewards.get(cat, {})
        cat_lines = []
        for place in sorted(cat_rewards.keys(), key=int):
            place_data = cat_rewards[place]
            coins = place_data.get('coins', 0)
            super_coins = place_data.get('super_coins', 0)
            items_list = place_data.get('items', [])
            
            parts = []
            if coins > 0:
                parts.append(f"{coins} {{custom_emoji:coins}}")
            if super_coins > 0:
                parts.append(f"{super_coins} {{custom_emoji:super_coin}}")
                
            for it in items_list:
                it_name = get_name(it['item_id'], lang)
                count = it.get('count', 1)
                cnt_suffix = f" x{count}" if count > 1 else ""
                parts.append(f"{it_name}{cnt_suffix}")
                
            rewards_str = " + ".join(parts)
            emoji_place = f"{{custom_emoji:top{place}}}" if str(place) in ['1', '2', '3'] else f"{place}."
            cat_lines.append(f"{emoji_place} {rewards_str}")
            
        lines.append("<blockquote>" + "\n".join(cat_lines) + "</blockquote>")
        lines.append("") # empty line between categories
        
    return "\n".join(lines).strip()


async def show_arena_menu(chatid: int, userid: int, lang: str, callback: CallbackQuery = None):
    # Exclude user's own queue entries from counts
    solo_count = await ArenaQueueModel.find(
        ArenaQueueModel.category == 'solo',
        ArenaQueueModel.userid != userid
    ).count()
    group_entries = await ArenaQueueModel.find(
        ArenaQueueModel.category == 'group',
        ArenaQueueModel.userid != userid
    ).to_list()
    group_count = sum(len(e.dino_ids) for e in group_entries)

    user = await User.find_one(User.userid == userid)
    is_premium = False
    if user:
        is_premium = await user.premium

    player = await get_player_or_create(userid)
    arena_cfg = GAME_SETTINGS.get('arena', {})
    free_total = arena_cfg.get('free_limit_premium', 10) if is_premium else arena_cfg.get('free_limit_standard', 3)
    free_left = max(0, free_total - player.free_battles_used)

    ticket_limit = arena_cfg.get('ticket_limit_premium', 10) if is_premium else arena_cfg.get('ticket_limit_standard', 7)
    tickets_left = max(0, ticket_limit - player.tickets_used)

    items = await Item.find({"owner": userid, "items_data.item_id": "wornoutticket"}).to_list()
    tickets_count = sum(it.count for it in items)

    from bot.tasks.arena_tasks import get_arena_status
    is_open, time_rem = get_arena_status()
    target_timestamp = int(time.time()) + time_rem
    time_str = seconds_to_str(time_rem, lang, mini=True)

    if is_open:
        status_text = t("arena.status_open", lang, time=time_str, timestamp=target_timestamp, default=f"🟢 <b>Арена открыта</b> (закроется <tg-time unix=\"{target_timestamp}\" format=\"r\">{time_str}</tg-time>)")
        search_text = t("arena.search_counts", lang, solo_count=solo_count, group_count=group_count, default=f"\n\nВ поиске противников:\n👤 Соло: {solo_count} дино\n👥 Групповой: {group_count} дино")
    else:
        status_text = t("arena.status_closed", lang, time=time_str, timestamp=target_timestamp, default=f"🔴 <b>Арена закрыта</b> (откроется <tg-time unix=\"{target_timestamp}\" format=\"r\">{time_str}</tg-time>)")
        search_text = ""

    text = t("arena.menu_info", lang, 
             status_info=status_text,
             search_info=search_text,
             solo_count=solo_count, 
             group_count=group_count, 
             free_left=free_left, 
             free_total=free_total,
             elo_solo=player.elo_solo,
             elo_group=player.elo_group,
             tickets_left=tickets_left,
             tickets_count=tickets_count,
             default=f"🏟 <b>PvP Арена</b>\n\n{status_text}\n\nВаш рейтинг клыков {{custom_emoji:silver_fang}}:\n👤 Соло: {player.elo_solo} {{custom_emoji:silver_fang}}\n👥 Групповой: {player.elo_group} {{custom_emoji:silver_fang}}{search_text}\n\n🎟️ Осталось бесплатных участий: {free_left} / {free_total}\n🎫 Билетов в наличии: {tickets_left} / {tickets_count}\n\nПрисоединяйтесь к сражениям, повышайте свой рейтинг клыков и выигрывайте сезонные награды!")
    
    # Inline buttons for Arena rules
    buttons = [
        [
            {"text": t("arena.btn_rules", lang, default="📜 Правила"), "callback_data": "arena:rules"}
        ]
    ]
    inline_markup = list_to_inline(buttons)

    if callback:
        try:
            from bot.modules.images_save import edit_SmartPhoto
            await edit_SmartPhoto(callback.message.chat.id, callback.message.message_id, 'images/arena/arena_placeholder.png', caption=text, parse_mode="html", reply_markup=inline_markup)
            return
        except Exception:
            try:
                await callback.message.edit_text(text, reply_markup=inline_markup, parse_mode="html")
                return
            except Exception:
                pass

    from bot.modules.images_save import send_SmartPhoto
    reply_markup = await m(userid, 'arena_menu', lang)
    await bot.send_message(chatid, t("arena.welcome_keyboard", lang, default="🏟️ Открыто меню Арены."), reply_markup=reply_markup)
    await send_SmartPhoto(chatid, 'images/arena/arena_placeholder.png', caption=text, parse_mode="html", reply_markup=inline_markup)

@main_router.callback_query(IsPrivateChat(), F.data == "arena:main")
async def show_arena_menu_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id

    await show_arena_menu(chatid, userid, lang, callback=callback)
    await callback.answer()

async def show_queue_dinos_page(chatid: int, userid: int, lang: str, page: int = 1, callback: CallbackQuery = None):
    entry = await ArenaQueueModel.find_one(ArenaQueueModel.userid == userid)

    if not entry:
        text = t("arena.queue_dinos_empty", lang, 
        default="📭 У вас сейчас нет динозавров в очереди поиска.")

        if callback:
            try:
                await callback.message.edit_text(text, parse_mode="html")
            except Exception:
                await bot.send_message(chatid, text, parse_mode="html")
        else:
            await bot.send_message(chatid, text, parse_mode="html")
        return

    n_dinos = len(entry.dino_ids)
    if page < 1:
        page = 1
    elif page > n_dinos:
        page = n_dinos
        
    dino_id = entry.dino_ids[page - 1]
    dino = Dino()
    dino_name = "Неизвестный динозавр"
    if await dino.create(str(dino_id)):
        dino_name = dino.name
        
    category_name = t("arena.btn_solo", lang, default="👤 Соло") if entry.category == 'solo' else t("arena.btn_group", lang, default="👥 Групповой")
    
    # Place the dino info in a blockquote citation (HTML <blockquote>)
    dino_quote = f"<blockquote>🦕 <b>{dino_name}</b>\nРейтинг клыков: {entry.elo} {{custom_emoji:silver_fang}}\nКатегория: {category_name}</blockquote>"
    
    text = t("arena.queue_dinos_info_page", lang,
             page=page,
             total=n_dinos,
             dino_quote=dino_quote,
             default=f"🦖 <b>Ваши динозавры в очереди:</b> (Страница {page}/{n_dinos})\n\n{dino_quote}\n\nВы можете отменить поиск и вернуть динозавров и все взятые ресурсы.")
             
    buttons = []
    
    # Cancel search button with the name of the dinosaur
    cancel_text = t("arena.btn_cancel_dino", lang, name=dino_name, default=f"❌ Отменить {dino_name}")
    buttons.append([{"text": cancel_text, "callback_data": "arena:search_cancel"}])
    
    # Pagination
    if n_dinos > 1:
        nav_row = []
        prev_page = page - 1 if page > 1 else n_dinos
        nav_row.append({"text": "⬅️", "callback_data": f"arena:queue_page:{prev_page}"})
        next_page = page + 1 if page < n_dinos else 1
        nav_row.append({"text": "➡️", "callback_data": f"arena:queue_page:{next_page}"})
        buttons.append(nav_row)
        
    markup = list_to_inline(buttons)
    
    if callback:
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
        except Exception:
            await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")
    else:
        await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")

@main_router.callback_query(IsPrivateChat(), F.data == "arena:queue_dinos")
async def arena_queue_dinos_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    
    await show_queue_dinos_page(chatid, userid, lang, page=1, callback=callback)
    await callback.answer()

@main_router.callback_query(IsPrivateChat(), F.data.startswith("arena:queue_page:"))
async def arena_queue_page_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    
    parts = callback.data.split(":")
    page = int(parts[2]) if len(parts) > 2 else 1
    
    await show_queue_dinos_page(chatid, userid, lang, page=page, callback=callback)
    await callback.answer()

@main_router.message(IsPrivateChat(), Text('commands_name.arena.queue_dinos'), IsAuthorizedUser())
async def arena_queue_dinos_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    chatid = message.chat.id
    
    await show_queue_dinos_page(chatid, userid, lang, page=1)

@main_router.callback_query(IsPrivateChat(), F.data == "arena:back_to_map")
async def arena_back_to_map(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    await bot.send_message(chatid, t('map.text', lang), reply_markup=await m(userid, 'map_menu', lang))
    await callback.answer()

# Message handlers for reply keyboard buttons
@main_router.message(IsPrivateChat(), Text('commands_name.arena.search'), IsAuthorizedUser())
async def arena_search_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    chatid = message.chat.id

    from bot.tasks.arena_tasks import get_arena_status
    is_open, _ = get_arena_status()
    if not is_open:
        await message.answer(t("arena.closed_error", lang, default="🔴 Арена в данный момент закрыта! Попробуйте позже."))
        return

    user = await User.find_one(User.userid == userid)
    if not user or user.lvl < 10:
        await message.answer(t('arena.level_restriction_error', lang, default="⚠️ Арена доступна только для аккаунтов от 10 уровня и выше!"))
        return

    player = await get_player_or_create(userid)
    if player.ban_end_time > int(time.time()):
        time_left = seconds_to_str(player.ban_end_time - int(time.time()), lang)
        await message.answer(t('arena.ban_warning', lang, time_left=time_left, default=f"❌ Поиск временно заблокирован. Осталось: {time_left}"))
        return

    is_premium = await user.premium if user else False
    arena_cfg = GAME_SETTINGS.get('arena', {})
    free_limit = arena_cfg.get('free_limit_premium', 10) if is_premium else arena_cfg.get('free_limit_standard', 3)
    ticket_limit = arena_cfg.get('ticket_limit_premium', 10) if is_premium else arena_cfg.get('ticket_limit_standard', 7)

    if player.free_battles_used >= free_limit and player.tickets_used >= ticket_limit:
        await message.answer(t("arena.limit_reached_error", lang, default="❌ Вы превысили дневной лимит боёв на Арене!"))
        return

    # Category choose
    solo_count = 0
    group_count = 0
    async for entry in ArenaQueueModel.find(ArenaQueueModel.userid != userid):
        if entry.category == 'solo':
            solo_count += len(entry.dino_ids)
        elif entry.category == 'group':
            group_count += len(entry.dino_ids)

    is_premium = await user.premium if user else False
    arena_cfg = GAME_SETTINGS.get('arena', {})
    free_limit = arena_cfg.get('free_limit_premium', 10) if is_premium else arena_cfg.get('free_limit_standard', 3)
    
    ticket_warning = ""
    if player.free_battles_used >= free_limit:
        ticket_name = get_name("wornoutticket", lang, with_emoji=True, html=True)
        ticket_warning = t("arena.ticket_warning_note", lang, ticket_name=ticket_name, default=f"\n\n⚠️ <b>Внимание:</b> ваши бесплатные попытки исчерпаны. Для участия будет использован <b>{ticket_name}</b>.")

    text = t("arena.choose_category", lang, 
             solo_count=solo_count, 
             group_count=group_count, 
             ticket_warning=ticket_warning,
             default=f"⚔ <b>Выберите категорию:</b>\n\n👤 Соло — 1 динозавр (В поиске: {solo_count} дино)\n👥 Групповой — от 2 до 4 динозавров (В поиске: {group_count} дино){ticket_warning}")
    buttons = [
        [
            {"text": t("arena.btn_solo", lang, default="👤 Соло"), "callback_data": "arena:search_category:solo"},
            {"text": t("arena.btn_group", lang, default="👥 Групповой"), "callback_data": "arena:search_category:group"}
        ]
    ]
    markup = list_to_inline(buttons)
    await message.answer(text, reply_markup=markup, parse_mode="html")

async def show_history_page(chatid: int, userid: int, lang: str, 
                            page: int = 1, callback: CallbackQuery = None):
    # Query last 25 battles
    battles = await ArenaBattleModel.find(
        {"$or": [{"userid_a": userid}, {"userid_b": userid}]}
    ).sort([("battle_time", -1)]).limit(25).to_list()

    if not battles:
        text = t("arena.no_battles_history", lang,
                  default="📭 У вас пока не было боёв на Арене.")
        buttons = [[{"text": t("buttons_name.back", lang),
                      "callback_data": "arena:main"}]]
        markup = list_to_inline(buttons)
        if callback:
            try:
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
            except Exception:
                await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")
        else:
            await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")
        return

    # Calculate streaks & streak breaks
    ordered_battles = list(reversed(battles))
    streak_breaks = {}
    current_type = None
    streak_len = 0
    for b in ordered_battles:
        is_win = b.winner_id == userid
        is_draw = b.winner_id == 0
        res = "win" if is_win else ("draw" if is_draw else "loss")
        
        if current_type is None:
            current_type = res
            if res != "draw":
                streak_len = 1
        else:
            if res == current_type:
                if res != "draw":
                    streak_len += 1
            else:
                if current_type == "win" and streak_len >= 3:
                    streak_breaks[b.id] = t("arena.streak_win_broken", lang, count=streak_len, default=f"💔 Прервана серия из {streak_len} побед")
                elif current_type == "loss" and streak_len >= 3:
                    streak_breaks[b.id] = t("arena.streak_loss_broken", lang, count=streak_len, default=f"❤️ Прервана серия из {streak_len} поражений")
                
                current_type = res
                if res != "draw":
                    streak_len = 1
                else:
                    streak_len = 0

    # Calculate current streak
    first_result = None
    streak_count = 0
    for b in battles:
        is_win = b.winner_id == userid
        is_draw = b.winner_id == 0
        if is_draw:
            break
        
        if first_result is None:
            first_result = "win" if is_win else "loss"
            streak_count = 1
        else:
            current_res = "win" if is_win else "loss"
            if current_res == first_result:
                streak_count += 1
            else:
                break

    streak_text = ""
    if first_result == "win":
        streak_text = t("arena.current_streak_win", lang, 
            count=streak_count, default=f"🔥 Текущая серия побед: {streak_count}")
    elif first_result == "loss":
        streak_text = t("arena.current_streak_loss", lang, count=streak_count, 
            default=f"❄️ Текущая серия поражений: {streak_count}")

    # Paginate (5 per page)
    n_battles = len(battles)
    per_page = 5
    total_pages = (n_battles - 1) // per_page + 1
    page = max(1, min(page, total_pages))

    min_ind = (page - 1) * per_page
    max_ind = page * per_page
    page_battles = battles[min_ind:max_ind]

    lines = []
    fang_emoji = "{custom_emoji:silver_fang}"
    for b in page_battles:
        if b.userid_a == userid:
            opp = b.username_b
            change = b.elo_change_a
            is_win = b.winner_id == userid
            my_dinos = b.dinos_a
            opp_dinos = b.dinos_b
        else:
            opp = b.username_a
            change = b.elo_change_b
            is_win = b.winner_id == userid
            my_dinos = b.dinos_b
            opp_dinos = b.dinos_a

        res_lbl = t("arena.history_win", lang, default="✅ Победа") if is_win else (t("arena.history_loss", lang, default="❌ Поражение") if b.winner_id != 0 else t("arena.history_draw", lang, default="🤝 Ничья"))
        sign = "+" if change >= 0 else ""
        
        dinos_str = ""
        if my_dinos and opp_dinos:
            dinos_str = f"\n🦕 {', '.join(my_dinos)} vs {', '.join(opp_dinos)}"

        break_str = ""
        if b.id in streak_breaks:
            break_str = f"\n{streak_breaks[b.id]}"

        date_str = datetime.fromtimestamp(b.battle_time).strftime("%d.%m.%Y %H:%M")

        item_text = t(
            "arena.history_item", lang,
            res_lbl=res_lbl,
            opp=opp,
            category=b.category.upper(),
            sign=sign,
            change=change,
            fang_emoji=fang_emoji,
            dinos_str=dinos_str,
            break_str=break_str,
            date_str=date_str,
            default=f"<blockquote>{res_lbl} против <b>{opp}</b> ({b.category.upper()}):\nРезультат: {sign}{change} {fang_emoji}{dinos_str}{break_str}\n🕒 {date_str}</blockquote>"
        )
        lines.append(item_text + "\n")

    title_text = t("arena.history_title_page", lang, page=page, total=total_pages, default=f"📜 <b>История боёв</b> (Страница {page}/{total_pages}):")
    text = title_text + "\n\n"
    if streak_text:
        text += streak_text + "\n\n"
    text += "\n".join(lines)

    text = resolve_custom_emojis(text)

    buttons = []
    
    # Navigation
    if total_pages > 1:
        nav_row = []
        prev_page = page - 1 if page > 1 else total_pages
        nav_row.append({"text": "⬅️", "callback_data": f"arena:history_page:{prev_page}"})
        next_page = page + 1 if page < total_pages else 1
        nav_row.append({"text": "➡️", "callback_data": f"arena:history_page:{next_page}"})
        buttons.append(nav_row)
        
    markup = list_to_inline(buttons)

    if callback:
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
        except Exception:
            await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")
    else:
        await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")

@main_router.message(IsPrivateChat(), Text('commands_name.arena.history'), IsAuthorizedUser())
async def arena_history_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    chatid = message.chat.id
    await show_history_page(chatid, userid, lang, page=1)

@main_router.message(IsPrivateChat(), Text('commands_name.arena.season'), IsAuthorizedUser())
async def arena_season_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)

    season = await ArenaSeasonModel.find_one()
    if not season:
        days_left = 30
        hours_left = 0
    else:
        time_left = max(0, season.end_time - int(time.time()))
        days_left = time_left // (24 * 3600)
        hours_left = (time_left % (24 * 3600)) // 3600

    rewards_desc = await get_rewards_details_text(lang)

    text = t("arena.season_info", lang, days=days_left, hours=hours_left, rewards=rewards_desc, default=f"🏆 <b>Текущий PvP сезон</b>\n\nДо конца сезона осталось: {days_left} дней и {hours_left} часов.\n\n{rewards_desc}\n\n👉 Для быстрого просмотра глобального рейтинга арен используйте команду: /rating")

    buttons = [[{"text": t("arena.btn_rules", lang, default="📜 Правила"), "callback_data": "arena:rules"}]]
    markup = list_to_inline(buttons)
    await message.answer(text, reply_markup=markup, parse_mode="html")

@main_router.callback_query(IsPrivateChat(), F.data == "arena:search_start")
async def arena_search_start(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id

    from bot.tasks.arena_tasks import get_arena_status
    is_open, _ = get_arena_status()
    if not is_open:
        await callback.answer(t("arena.closed_error", lang, default="🔴 Арена в данный момент закрыта! Попробуйте позже."), show_alert=True)
        return

    user = await User.find_one(User.userid == userid)
    if not user or user.lvl < 10:
        await callback.answer(t('arena.level_restriction_error', lang, default="⚠️ Арена доступна только для аккаунтов от 10 уровня и выше!"), show_alert=True)
        return

    player = await get_player_or_create(userid)
    if player.ban_end_time > int(time.time()):
        time_left = seconds_to_str(player.ban_end_time - int(time.time()), lang)
        await callback.answer(t('arena.ban_warning', lang, time_left=time_left, default=f"❌ Поиск временно заблокирован. Осталось: {time_left}"), show_alert=True)
        return

    # Category choose
    solo_count = 0
    group_count = 0
    async for entry in ArenaQueueModel.find(ArenaQueueModel.userid != userid):
        if entry.category == 'solo':
            solo_count += len(entry.dino_ids)
        elif entry.category == 'group':
            group_count += len(entry.dino_ids)

    is_premium = await user.premium if user else False
    arena_cfg = GAME_SETTINGS.get('arena', {})
    free_limit = arena_cfg.get('free_limit_premium', 10) if is_premium else arena_cfg.get('free_limit_standard', 3)
    
    ticket_warning = ""
    if player.free_battles_used >= free_limit:
        ticket_name = get_name("wornoutticket", lang, with_emoji=True, html=True)
        ticket_warning = t("arena.ticket_warning_note", lang, ticket_name=ticket_name, default=f"\n\n⚠️ <b>Внимание:</b> ваши бесплатные попытки исчерпаны. Для участия будет использован <b>{ticket_name}</b>.")

    text = t("arena.choose_category", lang, 
             solo_count=solo_count, 
             group_count=group_count, 
             ticket_warning=ticket_warning,
             default=f"⚔ <b>Выберите категорию:</b>\n\n👤 Соло — 1 динозавр (В поиске: {solo_count} дино)\n👥 Групповой — от 2 до 4 динозавров (В поиске: {group_count} дино){ticket_warning}")
    buttons = [
        [
            {"text": t("arena.btn_solo", lang, default="👤 Соло"), "callback_data": "arena:search_category:solo"},
            {"text": t("arena.btn_group", lang, default="👥 Групповой"), "callback_data": "arena:search_category:group"}
        ],
        [
            {"text": t("buttons_name.back", lang), "callback_data": "arena:main"}
        ]
    ]
    markup = list_to_inline(buttons)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
    await callback.answer()

@main_router.callback_query(IsPrivateChat(), F.data.startswith("arena:search_category:"))
async def search_category_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    category = callback.data.split(":")[2]

    from bot.tasks.arena_tasks import get_arena_status
    is_open, _ = get_arena_status()
    if not is_open:
        await callback.answer(t("arena.closed_error", lang, default="🔴 Арена в данный момент закрыта! Попробуйте позже."), show_alert=True)
        return

    if category == 'solo':
        # Simple dinosaur selection for Solo
        handler = ChooseDinoHandler(
            function=arena_solo_dino_selection_callback,
            userid=userid,
            chatid=chatid,
            lang=lang,
            add_egg=False,
            all_dinos=True,
            status_filter=DinoStatus.PASS,
            transmitted_data={'category': category}
        )
    else:
        # Group dinosaur selection
        min_dinos = 2
        max_dinos = 4
        handler = ChooseDinoListHandler(
            function=arena_dino_selection_callback,
            userid=userid,
            chatid=chatid,
            lang=lang,
            min_dinos=min_dinos,
            max_dinos=max_dinos,
            status_filter=DinoStatus.PASS,
            cancel_callback='arena_menu',
            transmitted_data={'category': category}
        )
    await handler.start()
    await callback.answer()

async def show_arena_menu_callback_data(callback: CallbackQuery):
    await show_arena_menu_callback(callback)

async def arena_solo_dino_selection_callback(selected_dino_id: ObjectId, transmitted_data: dict):
    await arena_dino_selection_callback([str(selected_dino_id)], transmitted_data)

async def arena_dino_selection_callback(selected_dino_ids: list, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    category = transmitted_data['category']

    # Proceed to bag assembly via ChooseStepHandler
    state = await get_state(userid, chatid)
    await state.update_data(selected_dino_ids=selected_dino_ids, category=category)

    inventory, _ = await User.get_inventory(userid, [])

    dino_db_ids = []
    for d_val in selected_dino_ids:
        dino_obj = Dino()
        if await dino_obj.create(d_val):
            dino_db_ids.append(dino_obj.id)

    backpack_cap = 0
    for dino_id in dino_db_ids:
        accs = await Item.find_accessory(dino_id, 'backpack')
        backpack_cap += sum(get_item_capacity(acc.items_data) for acc in accs)

    base_cap = 10 * len(selected_dino_ids)
    bag_limit = base_cap + backpack_cap

    steps = [
        MultiInventoryStepData('bag_items', StepMessage(
            text=t('journey_setup.bag_title_fabric', lang, default="🎒 *Сбор сумки*\n\nВыберите любые предметы из инвентаря, которые хотите взять с собой на бой:"),
            translate_message=False
        ), inventory=inventory,
           cancel_text_key='cancel_bag_assembly_journey',
           limit=bag_limit,
           limit_type='journey_bag',
           empty_allowed=True,
           filter_interact=False,
           filter_cant_sell=False
        )
    ]

    transmitted_data_bag = {
        'selected_dino_ids': selected_dino_ids,
        'category': category
    }

    await ChooseStepHandler(arena_bag_callback, userid,
                            chatid, lang, steps,
                            transmitted_data_bag).start()

async def arena_bag_callback(return_data: dict, trans_data: dict):
    userid = trans_data['userid']
    chatid = trans_data['chatid']
    lang = trans_data['lang']
    selected_dinos = trans_data['selected_dino_ids']
    category = trans_data['category']
    chosen_items = return_data.get('bag_items', [])

    from bot.tasks.arena_tasks import get_arena_status
    is_open, _ = get_arena_status()
    if not is_open:
        await bot.send_message(chatid, t("arena.closed_error", lang, default="🔴 Арена в данный момент закрыта! Попробуйте позже."), reply_markup=await m(userid, 'last_menu', lang))
        return

    # Validate limits
    user = await User.find_one(User.userid == userid)
    is_premium = await user.premium if user else False
    
    arena_cfg = GAME_SETTINGS.get('arena', {})
    free_limit = arena_cfg.get('free_limit_premium', 10) if is_premium else arena_cfg.get('free_limit_standard', 3)
    ticket_limit = arena_cfg.get('ticket_limit_premium', 10) if is_premium else arena_cfg.get('ticket_limit_standard', 7)

    player = await get_player_or_create(userid)
    is_free_attempt = True
    
    if player.free_battles_used < free_limit:
        player.free_battles_used += 1
    elif player.tickets_used < ticket_limit:
        # Check wornoutticket
        items = await Item.find({"owner": userid, "items_data.item_id": "wornoutticket"}).to_list()
        total_tickets = sum(it.count for it in items)
        if total_tickets < 1:
            ticket_name = get_name("wornoutticket", lang, with_emoji=True, html=True)
            await bot.send_message(chatid, t("arena.no_tickets_error", lang, ticket_name=ticket_name, default="❌ Недостаточно бесплатных попыток на сегодня! Требуется 🎟️ Потрепанный билет (wornoutticket) для участия."), reply_markup=await m(userid, 'last_menu', lang))
            return
        
        # Deduct ticket
        await Item.remove(userid, "wornoutticket", 1)
        player.tickets_used += 1
        is_free_attempt = False
    else:
        await bot.send_message(chatid, t("arena.limit_reached_error", lang, default="❌ Вы превысили дневной лимит боёв на Арене!"), reply_markup=await m(userid, 'last_menu', lang))
        return

    await player.save()

    # Subtract selected items from inventory
    bag_items = []
    for item in chosen_items:
        item_id = item['item_id']
        count = item['count']
        if count > 0:
            items_to_remove = await Item.find(Item.owner_id == userid, {"items_data.item_id": item_id}).to_list()
            item_abilities = {}
            if items_to_remove:
                item_abilities = items_to_remove[0].abilities
                
            bag_items.append({
                "item_id": item_id,
                "abilities": item_abilities,
                "count": count
            })
            await Item.remove(userid, item_id, count)

    # Insert into search queue
    dino_ids = [ObjectId(d_id) for d_id in selected_dinos]
    elo = player.elo_solo if category == 'solo' else player.elo_group
    
    # Ensure no duplicate queue entries
    await ArenaQueueModel.find(ArenaQueueModel.userid == userid).delete()
    
    queue_entry = ArenaQueueModel(
        userid=userid,
        dino_ids=dino_ids,
        category=category,
        joined_time=int(time.time()),
        elo=elo,
        bag_items=bag_items,
        is_free_attempt=is_free_attempt
    )
    await queue_entry.insert()

    # Show search view
    category_name = t("arena.btn_solo", lang, default="👤 Соло") if category == 'solo' else t("arena.btn_group", lang, default="👥 Групповой")
    text = t("arena.searching_opponent", lang, 
             category=category_name,
             elo=elo, 
             default=f"🔎 <b>Поиск противника начат!</b>\n\nВы добавлены в очередь поиска.\nКатегория: {category_name}\nВаш Elo рейтинг: {elo}\n\nКак только подходящий противник будет найден, вам придет уведомление. Вы можете продолжать игру!")
    
    state = await get_state(userid, chatid)
    await state.clear()
    
    buttons = [[{"text": t("arena.btn_cancel_search", lang, default="Отменить поиск"), "callback_data": "arena:search_cancel"}]]
    inline_markup = list_to_inline(buttons)
    await bot.send_message(chatid, text, reply_markup=inline_markup, parse_mode="html")

    reply_markup = await m(userid, 'arena_menu', lang)
    await bot.send_message(chatid, t("arena.welcome_keyboard", lang, default="🏟️ Открыто меню Арены."), reply_markup=reply_markup)

@main_router.callback_query(IsPrivateChat(), F.data == "arena:search_cancel")
async def search_cancel_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id

    entry = await ArenaQueueModel.find_one(ArenaQueueModel.userid == userid)
    if not entry:
        await callback.answer(t("arena.not_in_search", lang, default="Вы не находитесь в поиске."), show_alert=True)
        await show_arena_menu_callback(callback)
        return

    # Delete queue entry
    await entry.delete()

    # Refund attempts
    player = await get_player_or_create(userid)
    if entry.is_free_attempt:
        player.free_battles_used = max(0, player.free_battles_used - 1)
    else:
        player.tickets_used = max(0, player.tickets_used - 1)
        await Item.add(userid, "wornoutticket", 1)
    await player.save()

    # Refund items
    for item in entry.bag_items:
        await Item.add(userid, item["item_id"], item["count"], item.get("abilities", {}))

    # Clear state
    state = await get_state(userid, chatid)
    await state.clear()

    await callback.answer(t("arena.search_cancelled", lang, default="Поиск отменен. Все ресурсы возвращены!"), show_alert=True)
    await show_arena_menu_callback(callback)

@main_router.callback_query(IsPrivateChat(), F.data.startswith("arena_confirm:"))
async def arena_confirm_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    
    parts = callback.data.split(":")
    action = parts[1]
    match_id = parts[2]

    match = await ArenaMatchModel.find_one(ArenaMatchModel.id == ObjectId(match_id))
    if not match:
        await callback.answer(t("arena.match_expired_or_not_found", lang, default="Матч не найден или уже истек."), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    # Enforce only player_a or player_b can interact
    if userid == match.player_a_id:
        is_player_a = True
    elif userid == match.player_b_id:
        is_player_a = False
    else:
        await callback.answer("❌ Вы не являетесь участником этого матча.", show_alert=True)
        return

    if action == "ready":
        if is_player_a:
            match.player_a_ready = True
        else:
            match.player_b_ready = True
        await match.save()
        
        await callback.message.edit_text(t("arena.waiting_other_confirm", lang, default="⏳ Ожидаем подтверждения от соперника..."), reply_markup=None)
        await callback.answer()

        # Check if both are ready
        refetched_match = await ArenaMatchModel.find_one(ArenaMatchModel.id == match.id)
        if refetched_match and refetched_match.player_a_ready is True and refetched_match.player_b_ready is True:
            # Delete match document from database to avoid race conditions
            await refetched_match.delete()
            # Start battle asynchronously
            asyncio.create_task(run_and_animate_combat(refetched_match))
            
    elif action == "decline":
        # Decline! Set search ban for decliner, refund both
        if is_player_a:
            match.player_a_ready = False
        else:
            match.player_b_ready = False
        await match.save()
        
        await callback.answer(t("arena.declined_self", lang, default="Вы отклонили участие. Поиск заблокирован на 5 минут."), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Match tasks will clean up and apply bans/refunds dynamically
        # But let's trigger cleanup immediately for speed
        from bot.tasks.arena_tasks import handle_declined_match
        await handle_declined_match(match.id)

async def run_and_animate_combat(match: ArenaMatchModel):
    # Retrieve participants
    from bot.models.dinosaur import Dino
    
    player_a_id = match.player_a_id
    player_b_id = match.player_b_id
    lang_a = await get_lang(player_a_id)
    lang_b = await get_lang(player_b_id)

    # Load dinosaurs and image paths
    from bot.const import DINOS
    dinos_elements = DINOS.get('elements', {})

    team_x = []
    team_x_img_paths = []
    for d_id in match.player_a_dinos:
        dino = await Dino.find_one(Dino.id == d_id)
        if dino:
            part = await CombatParticipant.from_dino(dino, [])
            part.hp = part.max_hp
            part.energy = part.max_energy
            # Pack bag items
            part.inventory = []
            for item in match.player_a_bag:
                part.inventory.append({
                    "_id": ObjectId(),
                    "item_id": item["item_id"],
                    "items_data": get_item_data(item["item_id"]) or {},
                    "count": item["count"]
                })
            team_x.append(part)
            
            d_info = dinos_elements.get(str(dino.data_id), {})
            d_img = d_info.get('image', '')
            if d_img:
                team_x_img_paths.append(d_img)

            # Add to collections of both players
            from bot.models.user import DinoCollection
            await DinoCollection.add_to_collection(player_a_id, dino.data_id)
            await DinoCollection.add_to_collection(player_b_id, dino.data_id)

    team_y = []
    team_y_img_paths = []
    for d_id in match.player_b_dinos:
        dino = await Dino.find_one(Dino.id == d_id)
        if dino:
            part = await CombatParticipant.from_dino(dino, [])
            part.hp = part.max_hp
            part.energy = part.max_energy
            part.inventory = []
            for item in match.player_b_bag:
                part.inventory.append({
                    "_id": ObjectId(),
                    "item_id": item["item_id"],
                    "items_data": get_item_data(item["item_id"]) or {},
                    "count": item["count"]
                })
            team_y.append(part)
            
            d_info = dinos_elements.get(str(dino.data_id), {})
            d_img = d_info.get('image', '')
            if d_img:
                team_y_img_paths.append(d_img)

            # Add to collections of both players
            from bot.models.user import DinoCollection
            await DinoCollection.add_to_collection(player_a_id, dino.data_id)
            await DinoCollection.add_to_collection(player_b_id, dino.data_id)

    if not team_x or not team_y:
        # Match error
        await bot.send_message(player_a_id, "❌ Не удалось загрузить состав команд для боя.")
        await bot.send_message(player_b_id, "❌ Не удалось загрузить состав команд для боя.")
        return

    # Generate arena battle image
    from bot.modules.images_creators.arena_image import generate_arena_battle_image
    from bot.modules.images_save import send_SmartPhoto

    arena_img = generate_arena_battle_image(team_x_img_paths, team_y_img_paths)
    has_arena_img = arena_img is not None

    # Suffix team names
    for p in team_x:
        p.name = f"{p.name} (X)"
    for p in team_y:
        p.name = f"{p.name} (Y)"

    # Run combat
    combat = AutoCombat(team_x, team_y)
    result = combat.run()

    # Log battle to Redis formatted for viewer (TTL based on user premium status)
    raw_log_id = uuid.uuid4().hex
    combat_log_id = f"combat_log:{raw_log_id}"

    # Premium status for TTL
    from bot.modules.user.premium import premium
    is_prem_a = await premium(player_a_id)
    is_prem_b = await premium(player_b_id)
    
    ttl_a = 7776000 if is_prem_a else 604800
    ttl_b = 7776000 if is_prem_b else 604800
    max_battles_a = 1000 if is_prem_a else 200
    max_battles_b = 1000 if is_prem_b else 200
    
    history_ttl = max(ttl_a, ttl_b)

    from bot.redismanager import redis_set
    await redis_set(combat_log_id, result, ex=history_ttl)

    # Save battle record summary to dinosaurs' page histories in Redis
    import json
    from bot.redismanager import get_redis
    r_redis = get_redis()
    
    mobs_for_a = [p.name.replace(" (Y)", "") for p in team_y]
    summary_a = {
        "battle_id": combat_log_id,
        "winner": result["winner"],
        "mobs": mobs_for_a,
        "time": int(time.time()),
        "location": "arena"
    }

    mobs_for_b = [p.name.replace(" (X)", "") for p in team_x]
    winner_for_b = "X" if result["winner"] == "Y" else ("Y" if result["winner"] == "X" else result["winner"])
    summary_b = {
        "battle_id": combat_log_id,
        "winner": winner_for_b,
        "mobs": mobs_for_b,
        "time": int(time.time()),
        "location": "arena"
    }

    for d_id in match.player_a_dinos:
        dino_battles_key = f"dino_battles:{d_id}"
        await r_redis.lpush(dino_battles_key, json.dumps(summary_a, default=str))
        await r_redis.ltrim(dino_battles_key, 0, max_battles_a)
        await r_redis.expire(dino_battles_key, ttl_a)

    for d_id in match.player_b_dinos:
        dino_battles_key = f"dino_battles:{d_id}"
        await r_redis.lpush(dino_battles_key, json.dumps(summary_b, default=str))
        await r_redis.ltrim(dino_battles_key, 0, max_battles_b)
        await r_redis.expire(dino_battles_key, ttl_b)

    # Localized logs (omit generic battle_end header since arena has custom outcome summary)
    logs_a = AutoCombat.group_and_format_log(result, lang_a, perspective_team="X", include_battle_end=False)
    logs_b = AutoCombat.group_and_format_log(result, lang_b, perspective_team="Y", include_battle_end=False)

    # Start messaging
    text_start_a = t("arena.battle_started_title", lang_a, default="⚔️ <b>Битва началась!</b>\n\n")
    text_start_b = t("arena.battle_started_title", lang_b, default="⚔️ <b>Битва началась!</b>\n\n")

    if match.player_a_msg_id:
        try:
            await bot.delete_message(player_a_id, match.player_a_msg_id)
        except Exception:
            pass

    if match.player_b_msg_id:
        try:
            await bot.delete_message(player_b_id, match.player_b_msg_id)
        except Exception:
            pass

    if has_arena_img:
        msg_a = await send_SmartPhoto(player_a_id, arena_img, caption=text_start_a, parse_mode="html")
        msg_b = await send_SmartPhoto(player_b_id, arena_img, caption=text_start_b, parse_mode="html")
    else:
        msg_a = await bot.send_message(player_a_id, text_start_a, parse_mode="html")
        msg_b = await bot.send_message(player_b_id, text_start_b, parse_mode="html")

    def split_round_into_turns(lines: List[str]):
        header = []
        turns = []
        current_turn = []
        for line in lines:
            if line.startswith("🟢") or line.startswith("🔴"):
                if current_turn:
                    turns.append("\n".join(current_turn))
                    current_turn = []
                current_turn.append(line)
            elif current_turn:
                current_turn.append(line)
            else:
                header.append(line)
        if current_turn:
            turns.append("\n".join(current_turn))
        return "\n".join(header), turns

    rounds_count = max(list(logs_a.keys()) + list(logs_b.keys())) if (logs_a or logs_b) else 0
    rounds_shown_a = []
    rounds_shown_b = []

    for r in range(1, rounds_count + 1):
        raw_log_a = logs_a.get(r, [])
        raw_log_b = logs_b.get(r, [])

        round_log_lines_a = [re.sub(r'\*(.*?)\*', r'<b>\1</b>', line) for line in raw_log_a]
        round_log_lines_b = [re.sub(r'\*(.*?)\*', r'<b>\1</b>', line) for line in raw_log_b]

        header_a, turns_a = split_round_into_turns(round_log_lines_a)
        header_b, turns_b = split_round_into_turns(round_log_lines_b)

        total_turn_steps = max(len(turns_a), len(turns_b), 1)

        def fit_turn_caption(round_num: int, header: str, turns_list: List[str]) -> str:
            curr_turns = list(turns_list)
            while True:
                body = (header + "\n" if header else "") + "\n".join(curr_turns)
                res = resolve_custom_emojis(f"⚔️ <b>Битва идет...</b>\n\n🔹 <b>Раунд {round_num}</b>\n{body}")
                if len(res) <= 980 or not curr_turns:
                    break
                curr_turns.pop(0)

            if len(res) > 980:
                header_lines = header.split("\n")
                while len(header_lines) > 1 and len(res) > 980:
                    header_lines.pop(0)
                    body = "\n".join(header_lines)
                    res = resolve_custom_emojis(f"⚔️ <b>Битва идет...</b>\n\n🔹 <b>Раунд {round_num}</b>\n{body}")

            if len(res) > 980:
                res = res[:975] + "..."
            return res

        for t_idx in range(total_turn_steps):
            await asyncio.sleep(1.2)

            curr_turns_a = turns_a[:t_idx + 1] if turns_a else []
            curr_turns_b = turns_b[:t_idx + 1] if turns_b else []

            text_a = fit_turn_caption(r, header_a, curr_turns_a)
            text_b = fit_turn_caption(r, header_b, curr_turns_b)

            if has_arena_img:
                try:
                    await bot.edit_message_caption(chat_id=player_a_id, message_id=msg_a.message_id, caption=text_a, parse_mode="html")
                except Exception as e:
                    log(f"Error editing combat turn caption A: {e}", lvl=3, prefix="arena")

                try:
                    await bot.edit_message_caption(chat_id=player_b_id, message_id=msg_b.message_id, caption=text_a if player_a_id == player_b_id else text_b, parse_mode="html")
                except Exception as e:
                    log(f"Error editing combat turn caption B: {e}", lvl=3, prefix="arena")
            else:
                try:
                    await bot.edit_message_text(text_a, chat_id=player_a_id, message_id=msg_a.message_id, parse_mode="html")
                except Exception:
                    pass
                try:
                    await bot.edit_message_text(text_b, chat_id=player_b_id, message_id=msg_b.message_id, parse_mode="html")
                except Exception:
                    pass


    # Calculation Elo changes
    player_a = await get_player_or_create(player_a_id)
    player_b = await get_player_or_create(player_b_id)

    cat = match.category
    r_a = player_a.elo_solo if cat == 'solo' else player_a.elo_group
    r_b = player_b.elo_solo if cat == 'solo' else player_b.elo_group

    # Standard ELO formula
    e_a = 1 / (1 + 10 ** ((r_b - r_a) / 400))
    e_b = 1 / (1 + 10 ** ((r_a - r_b) / 400))

    winner_team = result["winner"]  # 'X' or 'Y' or 'Draw'
    
    if winner_team == "X":
        outcome_a = 1.0
        outcome_b = 0.0
        winner_id = player_a_id
    elif winner_team == "Y":
        outcome_a = 0.0
        outcome_b = 1.0
        winner_id = player_b_id
    else:
        outcome_a = 0.5
        outcome_b = 0.5
        winner_id = 0

    arena_cfg = GAME_SETTINGS.get('arena', {})
    k_factor = arena_cfg.get('elo_k_factor', 40)
    change_a = int(round(k_factor * (outcome_a - e_a)))
    change_b = int(round(k_factor * (outcome_b - e_b)))

    # Novice league thresholds
    novice_thr = arena_cfg.get('novice_league_threshold', 1200)
    novice_loss = arena_cfg.get('novice_max_loss', 5)

    if winner_team == "Y" or winner_team == "Draw":
        if r_a < novice_thr and change_a < 0:
            change_a = max(change_a, -novice_loss)
    if winner_team == "X" or winner_team == "Draw":
        if r_b < novice_thr and change_b < 0:
            change_b = max(change_b, -novice_loss)

    # Win streak bonuses
    streak_bonuses = arena_cfg.get('win_streak_bonuses', {"3": 5, "4": 10, "5": 15})
    
    if winner_team == "X":
        if cat == 'solo':
            player_a.win_streak_solo += 1
            player_b.win_streak_solo = 0
            streak_a = player_a.win_streak_solo
        else:
            player_a.win_streak_group += 1
            player_b.win_streak_group = 0
            streak_a = player_a.win_streak_group
            
        bonus = 0
        if streak_a >= 3:
            bonus = streak_bonuses.get(str(streak_a), 15)
        change_a += bonus
        
    elif winner_team == "Y":
        if cat == 'solo':
            player_b.win_streak_solo += 1
            player_a.win_streak_solo = 0
            streak_b = player_b.win_streak_solo
        else:
            player_b.win_streak_group += 1
            player_a.win_streak_group = 0
            streak_b = player_b.win_streak_group
            
        bonus = 0
        if streak_b >= 3:
            bonus = streak_bonuses.get(str(streak_b), 15)
        change_b += bonus
        
    else:
        # Draw resets streaks
        if cat == 'solo':
            player_a.win_streak_solo = 0
            player_b.win_streak_solo = 0
        else:
            player_a.win_streak_group = 0
            player_b.win_streak_group = 0

    # Apply ELO limits
    new_elo_a = max(0, r_a + change_a)
    new_elo_b = max(0, r_b + change_b)
    
    # Recalculate actual changes
    change_a = new_elo_a - r_a
    change_b = new_elo_b - r_b

    # Update player stats
    if cat == 'solo':
        player_a.elo_solo = new_elo_a
        player_b.elo_solo = new_elo_b
        if winner_team == "X":
            player_a.wins_solo += 1
            player_b.losses_solo += 1
        elif winner_team == "Y":
            player_b.wins_solo += 1
            player_a.losses_solo += 1
    else:
        player_a.elo_group = new_elo_a
        player_b.elo_group = new_elo_b
        if winner_team == "X":
            player_a.wins_group += 1
            player_b.losses_group += 1
        elif winner_team == "Y":
            player_b.wins_group += 1
            player_a.losses_group += 1

    player_a.last_battle_time = int(time.time())
    player_b.last_battle_time = int(time.time())

    await player_a.save()
    await player_b.save()

    # Trigger achievements check for the winner
    if winner_id > 0:
        try:
            from bot.modules.user.achievements import check_achievements
            winner_dinos_count = len(match.player_a_dinos) if winner_id == player_a_id else len(match.player_b_dinos)
            loser_dinos_count = len(match.player_b_dinos) if winner_id == player_a_id else len(match.player_a_dinos)
            await check_achievements(winner_id, "arena_win", data={
                "category": cat,
                "my_dinos_count": winner_dinos_count,
                "opp_dinos_count": loser_dinos_count
            })
        except Exception as e:
            log(f"Error checking arena achievements: {e}", lvl=3)

    # Log battle to history database
    dinos_a_names = [p.name.replace(" (X)", "") for p in team_x]
    dinos_b_names = [p.name.replace(" (Y)", "") for p in team_y]

    battle_log = ArenaBattleModel(
        userid_a=player_a_id,
        userid_b=player_b_id,
        username_a=match.player_a_name,
        username_b=match.player_b_name,
        category=cat,
        winner_id=winner_id,
        elo_change_a=change_a,
        elo_change_b=change_b,
        battle_time=int(time.time()),
        dinos_a=dinos_a_names,
        dinos_b=dinos_b_names
    )
    await battle_log.insert()

    # Final messages
    await asyncio.sleep(2.0)
    
    w_name_a = t("arena.win_you", lang_a, default="Вы победили!") if winner_team == "X" else (t("arena.win_opponent", lang_a, name=match.player_b_name, default=f"Победил {match.player_b_name}!") if winner_team == "Y" else t("arena.win_draw", lang_a, default="Ничья!"))
    w_name_b = t("arena.win_you", lang_b, default="Вы победили!") if winner_team == "Y" else (t("arena.win_opponent", lang_b, name=match.player_a_name, default=f"Победил {match.player_a_name}!") if winner_team == "X" else t("arena.win_draw", lang_b, default="Ничья!"))

    rounds_joined_a = rounds_shown_a[-1] if rounds_shown_a else ""
    rounds_joined_b = rounds_shown_b[-1] if rounds_shown_b else ""

    change_a_str = f"+{change_a}" if change_a >= 0 else str(change_a)
    change_b_str = f"+{change_b}" if change_b >= 0 else str(change_b)

    text_end_a = t("arena.battle_end_message", lang_a,
                   rounds=rounds_joined_a,
                   winner_text=w_name_a,
                   category=cat.upper(),
                   my_elo=r_a,
                   my_new_elo=new_elo_a,
                   my_change=change_a_str,
                   opp_elo=r_b,
                   opp_new_elo=new_elo_b,
                   opp_change=change_b_str,
                   default=f"⚔️ <b>Битва завершена!</b>\n\n{rounds_joined_a}\n\n🏆 <b>{w_name_a}</b>\n\n📊 Изменение рейтинга клыков {{custom_emoji:silver_fang}} ({cat.upper()}):\n⭐ Вы: {r_a} {{custom_emoji:silver_fang}} ➔ {new_elo_a} {{custom_emoji:silver_fang}} ({change_a_str})\n👤 Соперник: {r_b} {{custom_emoji:silver_fang}} ➔ {new_elo_b} {{custom_emoji:silver_fang}} ({change_b_str})"
                  )
    text_end_a = resolve_custom_emojis(text_end_a)

    text_end_b = t("arena.battle_end_message", lang_b,
                   rounds=rounds_joined_b,
                   winner_text=w_name_b,
                   category=cat.upper(),
                   my_elo=r_b,
                   my_new_elo=new_elo_b,
                   my_change=change_b_str,
                   opp_elo=r_a,
                   opp_new_elo=new_elo_a,
                   opp_change=change_a_str,
                   default=f"⚔️ <b>Битва завершена!</b>\n\n{rounds_joined_b}\n\n🏆 <b>{w_name_b}</b>\n\n📊 Изменение рейтинга клыков {{custom_emoji:silver_fang}} ({cat.upper()}):\n⭐ Вы: {r_b} {{custom_emoji:silver_fang}} ➔ {new_elo_b} {{custom_emoji:silver_fang}} ({change_b_str})\n👤 Соперник: {r_a} {{custom_emoji:silver_fang}} ➔ {new_elo_a} {{custom_emoji:silver_fang}} ({change_a_str})"
                  )
    text_end_b = resolve_custom_emojis(text_end_b)

    if has_arena_img:
        text_end_a = t("arena.battle_end_caption", lang_a,
                       winner_text=w_name_a,
                       category=cat.upper(),
                       my_elo=r_a,
                       my_new_elo=new_elo_a,
                       my_change=change_a_str,
                       opp_elo=r_b,
                       opp_new_elo=new_elo_b,
                       opp_change=change_b_str,
                       default=f"🏆 <b>{w_name_a}</b>\n\n📊 Изменение рейтинга клыков {{custom_emoji:silver_fang}} ({cat.upper()}):\n⭐ Вы: {r_a} {{custom_emoji:silver_fang}} ➔ {new_elo_a} {{custom_emoji:silver_fang}} ({change_a_str})\n👤 Соперник: {r_b} {{custom_emoji:silver_fang}} ➔ {new_elo_b} {{custom_emoji:silver_fang}} ({change_b_str})"
                      )
        text_end_a = resolve_custom_emojis(text_end_a)

        text_end_b = t("arena.battle_end_caption", lang_b,
                       winner_text=w_name_b,
                       category=cat.upper(),
                       my_elo=r_b,
                       my_new_elo=new_elo_b,
                       my_change=change_b_str,
                       opp_elo=r_a,
                       opp_new_elo=new_elo_a,
                       opp_change=change_a_str,
                       default=f"🏆 <b>{w_name_b}</b>\n\n📊 Изменение рейтинга клыков {{custom_emoji:silver_fang}} ({cat.upper()}):\n⭐ Вы: {r_b} {{custom_emoji:silver_fang}} ➔ {new_elo_b} {{custom_emoji:silver_fang}} ({change_b_str})\n👤 Соперник: {r_a} {{custom_emoji:silver_fang}} ➔ {new_elo_a} {{custom_emoji:silver_fang}} ({change_a_str})"
                      )
        text_end_b = resolve_custom_emojis(text_end_b)

    buttons_a = [[{"text": t("arena.btn_view_combat_log", lang_a, default="👁️ Посмотреть лог боя"), "callback_data": f"clv {raw_log_id} 0"}]]
    buttons_b = [[{"text": t("arena.btn_view_combat_log", lang_b, default="👁️ Посмотреть лог боя"), "callback_data": f"clv {raw_log_id} 0"}]]
    markup_a = list_to_inline(buttons_a)
    markup_b = list_to_inline(buttons_b)

    if has_arena_img:
        try:
            await bot.edit_message_caption(chat_id=player_a_id, message_id=msg_a.message_id, caption=text_end_a, parse_mode="html", reply_markup=markup_a)
        except Exception as e:
            log(f"Error editing final arena caption A: {e}", lvl=3, prefix="arena")

        try:
            await bot.edit_message_caption(chat_id=player_b_id, message_id=msg_b.message_id, caption=text_end_b, parse_mode="html", reply_markup=markup_b)
        except Exception as e:
            log(f"Error editing final arena caption B: {e}", lvl=3, prefix="arena")
    else:
        try:
            await bot.edit_message_text(text_end_a, chat_id=player_a_id, message_id=msg_a.message_id, parse_mode="html", reply_markup=markup_a)
        except Exception:
            await bot.send_message(player_a_id, text_end_a, parse_mode="html", reply_markup=markup_a)

        try:
            await bot.edit_message_text(text_end_b, chat_id=player_b_id, message_id=msg_b.message_id, parse_mode="html", reply_markup=markup_b)
        except Exception:
            await bot.send_message(player_b_id, text_end_b, parse_mode="html", reply_markup=markup_b)

@main_router.callback_query(IsPrivateChat(), F.data == "arena:history")
async def arena_history_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    await show_history_page(chatid, userid, lang, page=1, callback=callback)
    await callback.answer()

@main_router.callback_query(IsPrivateChat(), F.data.startswith("arena:history_page:"))
async def arena_history_page_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    parts = callback.data.split(":")
    page = int(parts[2]) if len(parts) > 2 else 1
    await show_history_page(chatid, userid, lang, page=page, callback=callback)
    await callback.answer()

@main_router.callback_query(IsPrivateChat(), F.data == "arena:season")
async def arena_season_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    
    season = await ArenaSeasonModel.find_one()
    if not season:
        # Fallback time
        days_left = 30
        hours_left = 0
    else:
        time_left = max(0, season.end_time - int(time.time()))
        days_left = time_left // (24 * 3600)
        hours_left = (time_left % (24 * 3600)) // 3600

    rewards_desc = await get_rewards_details_text(lang)

    text = t("arena.season_info", lang, days=days_left, hours=hours_left, rewards=rewards_desc, default=f"🏆 <b>Текущий PvP сезон</b>\n\nДо конца сезона осталось: {days_left} дней и {hours_left} часов.\n\n{rewards_desc}\n\n👉 Для быстрого просмотра глобального рейтинга арен используйте команду: /rating")

    buttons = [[{"text": t("arena.btn_rules", lang, default="📜 Правила"), "callback_data": "arena:rules"}]]
    markup = list_to_inline(buttons)
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
    except Exception:
        await bot.send_message(callback.message.chat.id, text, reply_markup=markup, parse_mode="html")
    await callback.answer()

@main_router.callback_query(IsPrivateChat(), F.data == "arena:rules")
async def arena_rules_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)

    ticket_name = get_name("wornoutticket", lang, with_emoji=True, html=True)
    text = t("arena.rules_info", lang, ticket_name=ticket_name, default="📜 <b>Правила PvP Арены</b>\n\n1️⃣ <b>Elo-рейтинг:</b> Все игроки начинают сезон с 1000 Elo. Соперники подбираются с близким рейтингом.\n\n2️⃣ <b>Лига новичков:</b> Если ваш рейтинг меньше 1200 Elo, при поражении вы теряете не более 5 Elo.\n\n3️⃣ <b>Серии побед:</b> Победы подряд приносят дополнительный Elo: за 3 победы +5, за 4 победы +10, за 5 и более +15.\n\n4️⃣ <b>Участие и билеты:</b> Игрокам ежедневно предоставляется 3 бесплатных участия (10 для Premium-аккаунтов). Дополнительные бои можно сыграть с помощью {ticket_name} — до 7 дополнительных участий в день (10 для Premium).\n\n5️⃣ <b>Ограничение противников:</b> С одним и тем же противником (человеком) можно сражаться не чаще одного раза в 30 минут.\n\n6️⃣ <b>Состояние динозавров:</b> В боях на Арене динозавры не теряют очки здоровья (HP), однако используемые во время боя вспомогательные предметы тратятся.\n\n7️⃣ <b>Защита от неактивности (Топ-10):</b> Игроки из Топ-10 рейтинга должны регулярно проводить бои. Если вы не сыграли ни одного боя за 48 часов, ваш Elo будет списываться на 20 очков каждые сутки.\n\n8️⃣ <b>Сброс сезона:</b> Сезон длится 30 дней. По окончании сезона Топ-3 игрока в Соло и Групповом рейтингах получают награды, после чего все рейтинги сбрасываются до 1000 Elo.\n\n9️⃣ <b>Время работы:</b> Арена открыта 4 раза в день на 1 час — каждые 6 часов.")

    buttons = [
        [
            {"text": t("buttons_name.donate_shop", lang, default="⭐ Донат-магазин"), "callback_data": "support main 0"}
        ],
        [
            {"text": t("buttons_name.back", lang), "callback_data": "arena:season"}
        ]
    ]
    markup = list_to_inline(buttons)
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
    except Exception:
        await bot.send_message(callback.message.chat.id, text, reply_markup=markup, parse_mode="html")
    await callback.answer()

# Helper for other routers to call show_arena_menu
async def show_arena_menu_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_arena_menu(chatid, userid, lang)
    await callback.answer()
