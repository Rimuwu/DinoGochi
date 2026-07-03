from time import time
import uuid
import json
from bson import ObjectId
from typing import List, Dict, Any, Optional

from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.exec import main_router, bot
from bot.modules.decorators import HDMessage, HDCallback
from bot.modules.localization import t, get_data, get_lang
from bot.modules.markup import markups_menu as m
from bot.modules.markup import cancel_markup
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.models.user import User
from bot.models.dinosaur import Dino, DinoStatus
from bot.models.activity import JourneyActivity, Activity
from bot.models.items import Item
from bot.redismanager import redis_get, redis_set
from bot.modules.dinosaur.dino_status import check_status
from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.status import DinoPassStatus

class JourneySetupStates(StatesGroup):
    selecting_dinos = State()
    assembling_bag = State()
    selecting_location = State()
    selecting_duration = State()

# Main Activities Menu Hook
@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.actions.journey'))
async def journey_com(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    chatid = message.chat.id

    # Check if there is an active journey for this user
    journey = await JourneyActivity.find_one(JourneyActivity.sended == userid)
    if journey:
        await show_active_journey_menu(chatid, userid, lang, journey)
    else:
        await show_idle_journey_menu(chatid, userid, lang)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.actions.events'))
async def events_com(message: Message):
    await journey_com(message)

async def show_idle_journey_menu(chatid: int, userid: int, lang: str):
    text = t("journey_menu.info", lang, active_count=0)
    buttons = [
        {t("journey_menu.buttons.send", lang): "j_send"},
        {t("journey_menu.buttons.history", lang): "j_hist:1"}
    ]
    markup = list_to_inline(buttons, 1)
    await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")

async def get_active_journey_text_and_markup(journey: JourneyActivity, lang: str, userid: int = 0):
    # Time left
    time_left_sec = max(0, journey.end_time - int(time()))
    time_left = seconds_to_str(time_left_sec, lang)

    # Dinos names
    dino_names = []
    for d_id in journey.dino_ids:
        dino = await Dino.find_one(Dino.id == d_id)
        if dino:
            dino_names.append(dino.name)
    dinos_str = ", ".join(dino_names)

    # Location name
    loc_name = get_data(f"journey_start.locations.{journey.location}", lang).get("name", journey.location)

    # Bag contents
    from bot.modules.items.item import get_name
    bag_lines = []
    for item in journey.bag:
        if item.get("count", 0) > 0:
            bag_lines.append(f"{get_name(item['item_id'], lang)} ({item['count']})")
    bag_str = ", ".join(bag_lines) if bag_lines else t("journey_setup.empty_bag", lang)

    # Last event
    last_event = None
    comp_log = journey.completed_log
    if comp_log:
        last_event = await JourneyActivity.generate_event_message(comp_log[-1], lang, journey.id)

    # Format base info
    text = t("journey_menu.active_info", lang,
             location=loc_name,
             time_left=time_left,
             dinos=dinos_str,
             bag=bag_str,
             events_count=len(comp_log))

    # Append last event if it exists
    if last_event and last_event != "-":
        last_event_lbl = t("journey_menu.last_event_label", lang) or "\n\nПоследнее событие:"
        text += f"{last_event_lbl}\n{last_event}"

    # Admin: append journey ID
    from bot.config import conf
    if userid and userid in conf.bot_devs:
        text += f"\n\n🔧 <code>ID: {journey.id}</code>"

    buttons = [
        [
            InlineKeyboardButton(text=t("journey_menu.buttons.stop", lang), callback_data=f"j_stop:{journey.id}"),
            InlineKeyboardButton(text=t("journey_menu.buttons.logs", lang), callback_data=f"j_active_log:{journey.id}:1")
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, markup

async def show_active_journey_menu(chatid: int, userid: int, lang: str, journey: JourneyActivity):
    text, markup = await get_active_journey_text_and_markup(journey, lang, userid)
    
    dino_species_ids = []
    for d_id in journey.dino_ids:
        d = await Dino.find_one(Dino.id == d_id)
        if d:
            dino_species_ids.append(d.data_id)
            
    from bot.modules.images import dino_journey
    
    # dino_journey returns BufferedInputFile directly — no re-wrapping needed
    photo_input = await dino_journey(dino_species_ids, journey.location)
    
    await bot.send_photo(chatid, photo=photo_input, caption=text, reply_markup=markup, parse_mode="html")


# Back to main menu callback
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data == "j_active_menu")
async def active_menu_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    journey = await JourneyActivity.find_one(JourneyActivity.sended == userid)
    if journey:
        text, markup = await get_active_journey_text_and_markup(journey, lang, userid)
        await callback.message.edit_caption(caption=text, reply_markup=markup, parse_mode="html")
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_idle_journey_menu(callback.message.chat.id, userid, lang)
    await callback.answer()

# Stop/Cancel journey callback
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_stop:"))
async def stop_journey_callback(callback: CallbackQuery):
    journey_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)
    
    journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
    if journey and journey.sended == userid:
        # Load first dino name
        dino = await Dino.find_one(Dino.id == journey.dino_ids[0])
        dino_name = dino.name if dino else "динозавр"
        
        # End journey in model
        await JourneyActivity.end(journey.dino_ids[0])
        
        log_text = t("journey_log", lang, coins=journey.coins, items=len(journey.items), time=seconds_to_str(int(time()) - journey.start_time, lang), col=len(journey.completed_log), name=dino_name)
        try:
            await callback.message.edit_caption(caption=log_text, reply_markup=log_markup, parse_mode="html")
        except Exception:
            try:
                await callback.message.edit_text(log_text, reply_markup=log_markup, parse_mode="html")
            except Exception:
                pass
        await callback.message.answer(t("journey_start.start_2", lang), reply_markup=await m(userid, 'actions_menu', lang))
    await callback.answer()

# Log Pagination Callback
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_active_log:"))
async def active_log_pagination(callback: CallbackQuery):
    parts = callback.data.split(":")
    journey_id = parts[1]
    page = int(parts[2])
    userid = callback.from_user.id
    lang = await get_lang(userid)

    journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
    if not journey:
        await callback.answer(t("not_found_key", lang), show_alert=True)
        return

    log_list = journey.completed_log
    if not log_list:
        await callback.message.edit_caption(caption="📭 Событий пока не произошло.", reply_markup=list_to_inline([{t("journey_menu.buttons.back", lang): "j_active_menu"}]), parse_mode="html")
        await callback.answer()
        return

    # Paginate: 5 events per page
    page_size = 5
    total_pages = (len(log_list) + page_size - 1) // page_size
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = page * page_size
    page_events = log_list[start_idx:end_idx]

    # Count root events before start_idx to keep correct numbering
    root_count = 0
    for i in range(start_idx):
        ev_msg = await JourneyActivity.generate_event_message(log_list[i], lang, journey.id)
        if not ev_msg.strip().startswith("↳"):
            root_count += 1

    lines = []
    for ev in page_events:
        ev_msg = await JourneyActivity.generate_event_message(ev, lang, journey.id)
        if ev_msg.strip().startswith("↳"):
            lines.append(ev_msg)
        else:
            root_count += 1
            lines.append(f"🔹 <b>{root_count}.</b> {ev_msg}")
    
    text = t("journey_menu.log_title", lang, page=page, pages=total_pages) + "\n\n" + "\n\n".join(lines)

    # Nav buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀ Пред.", callback_data=f"j_active_log:{journey_id}:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="След. ▶", callback_data=f"j_active_log:{journey_id}:{page + 1}"))

    buttons = [nav_buttons] if nav_buttons else []
    buttons.append([InlineKeyboardButton(text=t("journey_menu.buttons.back_to_journey", lang), callback_data="j_active_menu")])

    await callback.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")
    await callback.answer()

async def _render_history_list(message, userid: int, lang: str, page: int = 1):
    """Shared helper: render the journey history list into a message."""
    from bot.modules.user.premium import premium
    is_prem = await premium(userid)
    history_ttl = 7776000 if is_prem else 604800

    user_journeys_key = f"user_journeys:{userid}"
    history_list = await redis_get(user_journeys_key) or []
    current_time = int(time())
    history_list = [h for h in history_list if current_time - h.get("time_end", 0) < history_ttl]
    history_list.reverse()

    if not history_list:
        try:
            await message.edit_text(t("journey_menu.history_empty", lang), reply_markup=list_to_inline([{t("journey_menu.buttons.back", lang): "j_active_menu"}]))
        except Exception:
            await message.edit_caption(caption=t("journey_menu.history_empty", lang), reply_markup=list_to_inline([{t("journey_menu.buttons.back", lang): "j_active_menu"}]))
        return

    page_size = 5
    total_pages = (len(history_list) + page_size - 1) // page_size
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = page * page_size
    page_items = history_list[start_idx:end_idx]

    buttons = []
    for idx, item in enumerate(page_items):
        loc_name = get_data(f"journey_start.locations.{item['location']}", lang).get("name", item['location'])
        duration = seconds_to_str(item["duration"], lang)
        btn_text = t("journey_menu.history_item", lang, index=start_idx + idx + 1, location=loc_name, duration=duration, coins=item["coins"], items=item["items_count"])
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"j_hdetails:{item['id']}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◄ Назад", callback_data=f"j_hist:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Далее ►", callback_data=f"j_hist:{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text=t("journey_menu.buttons.back", lang), callback_data="j_active_menu")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await message.edit_text(t("journey_menu.history_title", lang), reply_markup=markup, parse_mode="html")
    except Exception:
        await message.edit_caption(caption=t("journey_menu.history_title", lang), reply_markup=markup, parse_mode="html")

# Completed Journey History Callback (from Redis)
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_hist:"))
async def journey_history_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    userid = callback.from_user.id
    lang = await get_lang(userid)
    await _render_history_list(callback.message, userid, lang, page)
    await callback.answer()

# Completed Journey Details Callback
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_hdetails:"))
async def journey_history_details(callback: CallbackQuery):
    journey_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    details = await redis_get(f"journey_details:{journey_id}")
    if not details:
        await callback.answer(t("not_found_key", lang), show_alert=True)
        return

    loc_name = get_data(f"journey_start.locations.{details['location']}", lang).get("name", details['location'])
    duration = seconds_to_str(details["duration"], lang)
    from bot.modules.items.item import counts_items
    items_text = counts_items(details["items"], lang) if details["items"] else "-"

    text = t("journey_menu.details", lang,
             location=loc_name,
             duration=duration,
             dinos=details["dinos"],
             coins=details["coins"],
             items=items_text,
             events_count=len(details["journey_log"]))

    buttons = [
        [InlineKeyboardButton(text=t("journey_menu.buttons.logs", lang), callback_data=f"j_hlog:{journey_id}:1")],
        [
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"j_hdelete:{journey_id}"),
            InlineKeyboardButton(text="◀ Назад к списку", callback_data="j_hist:1")
        ]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")
    await callback.answer()

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_hdelete:"))
async def delete_journey_history(callback: CallbackQuery):
    journey_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    from bot.redismanager import redis_del, redis_set, redis_get
    from bot.modules.user.premium import premium
    is_prem = await premium(userid)
    history_ttl = 7776000 if is_prem else 604800

    # Delete details key
    await redis_del(f"journey_details:{journey_id}")

    # Remove from history list
    user_journeys_key = f"user_journeys:{userid}"
    history_list = await redis_get(user_journeys_key) or []
    history_list = [h for h in history_list if h.get("id") != journey_id]
    await redis_set(user_journeys_key, history_list, ex=history_ttl)

    await callback.answer(t("journey_menu.deleted_success", lang, default="История путешествия успешно удалена."), show_alert=True)

    # Render history list directly (cannot mutate frozen CallbackQuery.data)
    await _render_history_list(callback.message, userid, lang, page=1)

# Completed Journey Log Pagination Callback
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_hlog:"))
async def journey_history_log_pagination(callback: CallbackQuery):
    parts = callback.data.split(":")
    journey_id = parts[1]
    page = int(parts[2])
    userid = callback.from_user.id
    lang = await get_lang(userid)

    details = await redis_get(f"journey_details:{journey_id}")
    if not details:
        await callback.answer(t("not_found_key", lang), show_alert=True)
        return

    log_list = details["journey_log"]
    if not log_list:
        await callback.message.edit_text("📭 Событий не происходило.", reply_markup=list_to_inline([{"◀ Назад": f"j_hdetails:{journey_id}"}]))
        await callback.answer()
        return

    page_size = 5
    total_pages = (len(log_list) + page_size - 1) // page_size
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = page * page_size
    page_events = log_list[start_idx:end_idx]

    # Count root events before start_idx to keep correct numbering
    root_count = 0
    for i in range(start_idx):
        ev_msg = await JourneyActivity.generate_event_message(log_list[i], lang, ObjectId(journey_id))
        if not ev_msg.startswith("   ↳ "):
            root_count += 1

    lines = []
    for ev in page_events:
        ev_msg = await JourneyActivity.generate_event_message(ev, lang, ObjectId(journey_id))
        if ev_msg.startswith("   ↳ "):
            lines.append(ev_msg)
        else:
            root_count += 1
            lines.append(f"🔹 <b>{root_count}.</b> {ev_msg}")
    
    text = t("journey_menu.log_title", lang, page=page, pages=total_pages) + "\n\n" + "\n\n".join(lines)

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀ Пред.", callback_data=f"j_hlog:{journey_id}:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="След. ▶", callback_data=f"j_hlog:{journey_id}:{page + 1}"))

    buttons = [nav_buttons] if nav_buttons else []
    buttons.append([InlineKeyboardButton(text=t("journey_menu.buttons.back", lang), callback_data=f"j_hdetails:{journey_id}")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")
    await callback.answer()


# =====================================================================
# WIZARD: dinosaur selection & bag assembly
# =====================================================================

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data == "j_send")
async def start_wizard_dino_selection(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)

    # Clear FSM State first
    await state.clear()

    # Load dinosaurs
    user = await User().create(userid)
    dinos = await user.get_dinos()
    free_dinos = []
    for d in dinos:
        status = await check_status(d.id)
        if status == DinoStatus.PASS:
            free_dinos.append(d)

    if not free_dinos:
        await callback.answer(t("journey_setup.no_dinos", lang), show_alert=True)
        return

    # Set state
    await state.set_state(JourneySetupStates.selecting_dinos)
    await state.update_data(free_dino_ids=[str(d.id) for d in free_dinos], selected_dino_ids=[])

    await render_dino_selection_screen(callback.message, free_dinos, [], lang)
    await callback.answer()

async def render_dino_selection_screen(message: Message, free_dinos: list, selected_ids: list, lang: str):
    text = t("journey_setup.select_dinos", lang, selected_count=len(selected_ids))
    buttons = []

    for dino in free_dinos:
        dino_id_str = str(dino.id)
        is_selected = dino_id_str in selected_ids
        checkbox = "✅ " if is_selected else "⬜ "
        btn_text = checkbox + dino.name + f" (HP: {int(dino.stats.get('heal', 100))})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"w_dino_toggle:{dino_id_str}")])

    # Bottom buttons
    nav_row = [
        InlineKeyboardButton(text="◀ Назад", callback_data="j_active_menu"),
        InlineKeyboardButton(text="Далее ▶", callback_data="w_dino_done")
    ]
    buttons.append(nav_row)

    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")

@HDCallback
@main_router.callback_query(JourneySetupStates.selecting_dinos, F.data.startswith("w_dino_toggle:"))
async def toggle_dino_selection(callback: CallbackQuery, state: FSMContext):
    dino_id_str = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    selected = list(state_data.get("selected_dino_ids", []))
    free_ids = state_data.get("free_dino_ids", [])

    if dino_id_str in selected:
        selected.remove(dino_id_str)
    else:
        if len(selected) >= 6:
            await callback.answer(t("journey_setup.max_dinos", lang, default="Вы можете отправить максимум 6 динозавров!"), show_alert=True)
            return
        selected.append(dino_id_str)

    await state.update_data(selected_dino_ids=selected)

    # Re-load dinosaur objects
    free_dinos = []
    for d_id in free_ids:
        d = await Dino.find_one(Dino.id == ObjectId(d_id))
        if d:
            free_dinos.append(d)

    await render_dino_selection_screen(callback.message, free_dinos, selected, lang)
    await callback.answer()

@HDCallback
@main_router.callback_query(JourneySetupStates.selecting_dinos, F.data == "w_dino_done")
async def finish_dino_selection(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    selected = state_data.get("selected_dino_ids", [])

    if not selected:
        await callback.answer("Выберите хотя бы одного динозавра!", show_alert=True)
        return

    # Proceed to bag assembly
    await state.set_state(JourneySetupStates.assembling_bag)
    await state.update_data(bag_selections={}) # item_id -> count

    await render_bag_assembly_screen(callback.message, userid, {}, lang, state)
    await callback.answer()

async def render_bag_assembly_screen(message: Message, userid: int, bag_selections: dict, lang: str, state: FSMContext):
    # Fetch player inventory
    from bot.modules.items.item import get_data as get_item_data, get_name
    inv = await Item.find(Item.owner_id == userid).to_list()

    eligible_items = []
    for item in inv:
        data_item = item.data
        item_type = data_item.get("type")
        item_id = item.item_id
        
        if item_id.startswith("SYSTEM_ITEM_"):
            continue
            
        is_eligible = (
            item_type in ["eat", "heal", "journey_acs", "dummy"] or
            item_id in ["cloak", "leather_clothing", "hiking_bag", "leather_jacket", "rubik_cube", "bag_goodies", "lock_bag", "skinning_knife"]
        )
        if is_eligible:
            eligible_items.append(item)

    # Calculate capacity
    state_data = await state.get_data()
    selected_dinos = state_data.get("selected_dino_ids", [])
    base_cap = 10 * len(selected_dinos)
    capacity_bonuses = {"hiking_bag": 15, "bag_goodies": 10, "lock_bag": 10}
    bonus_slots = sum(capacity_bonuses.get(k, 0) * count for k, count in bag_selections.items())
    max_capacity = base_cap + bonus_slots
    current_total = sum(bag_selections.values())

    # Build bag contents text
    bag_lines = []
    for item_id, count in bag_selections.items():
        if count > 0:
            bag_lines.append(t("journey_setup.bag_item_line", lang, name=get_name(item_id, lang), count=count))
            
    capacity_text = f"🎒 <b>Заполненность сумки:</b> {current_total}/{max_capacity} предметов\n\n"
    bag_contents = capacity_text + ("\n".join(bag_lines) if bag_lines else "🎒 " + t("journey_setup.empty_bag", lang))

    # Build inventory list text
    inv_lines = []
    buttons = []
    for item in eligible_items:
        item_id = item.item_id
        total_count = item.count
        selected_count = bag_selections.get(item_id, 0)
        
        inv_lines.append(f"• {get_name(item_id, lang)}: {total_count - selected_count} шт.")
        
        # Keyboard control row for this item
        btn_text = f"{get_name(item_id, lang)} ({selected_count}/{total_count})"
        buttons.append([
            InlineKeyboardButton(text="➖", callback_data=f"w_bag_dec:{item_id}"),
            InlineKeyboardButton(text=btn_text, callback_data="none"),
            InlineKeyboardButton(text="➕", callback_data=f"w_bag_inc:{item_id}")
        ])

    inv_contents = "\n".join(inv_lines) if inv_lines else "📭 Нет подходящих предметов."

    text = t("journey_setup.bag_title", lang, bag_contents=bag_contents, inv_contents=inv_contents)

    nav_row = [
        InlineKeyboardButton(text="◀ Назад", callback_data="j_send"),
        InlineKeyboardButton(text=t("journey_setup.ready", lang) + " ▶", callback_data="w_bag_done")
    ]
    buttons.append(nav_row)

    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")

@HDCallback
@main_router.callback_query(JourneySetupStates.assembling_bag, F.data.startswith("w_bag_dec:"))
async def bag_decrement(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    bag = dict(state_data.get("bag_selections", {}))

    if item_id in bag and bag[item_id] > 0:
        bag[item_id] -= 1

    await state.update_data(bag_selections=bag)
    await render_bag_assembly_screen(callback.message, userid, bag, lang, state)
    await callback.answer()

@HDCallback
@main_router.callback_query(JourneySetupStates.assembling_bag, F.data.startswith("w_bag_inc:"))
async def bag_increment(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    # Check total inventory count
    total_inv_count = 0
    inv = await Item.find(Item.owner_id == userid).to_list()
    for item in inv:
        if item.item_id == item_id:
            total_inv_count += item.count

    state_data = await state.get_data()
    bag = dict(state_data.get("bag_selections", {}))
    selected_dinos = state_data.get("selected_dino_ids", [])
    current_selected = bag.get(item_id, 0)

    # Calculate capacity
    base_cap = 10 * len(selected_dinos)
    capacity_bonuses = {"hiking_bag": 15, "bag_goodies": 10, "lock_bag": 10}
    bonus_slots = sum(capacity_bonuses.get(k, 0) * count for k, count in bag.items())
    max_capacity = base_cap + bonus_slots
    current_total = sum(bag.values())

    if current_selected < total_inv_count:
        if current_total < max_capacity or item_id in capacity_bonuses:
            bag[item_id] = current_selected + 1
        else:
            await callback.answer(t("journey_setup.bag_full", lang, default="Сумка заполнена! Выберите рюкзак или уменьшите число предметов."), show_alert=True)
            return

    await state.update_data(bag_selections=bag)
    await render_bag_assembly_screen(callback.message, userid, bag, lang, state)
    await callback.answer()

@HDCallback
async def render_location_selection(message: Message, userid: int, lang: str):
    from bot.modules.user.friends import get_frineds
    friends_data = await get_frineds(userid)
    friends_list = friends_data.get("friends", [])

    content_data = get_data('journey_start', lang)
    text = content_data['ask_loc']
    buttons = []
    
    user = await User().create(userid)
    a = 1
    row = []
    for key, dct in content_data['locations'].items():
        active_journeys = await JourneyActivity.find(JourneyActivity.location == key).to_list()
        friends_count = sum(len(j.dino_ids) for j in active_journeys if j.sended in friends_list)
        friends_text = f"\n👥 *Друзей здесь*: {friends_count}" if friends_count > 0 else ""
        
        text += f"*{a}*. {dct['text']}{friends_text}\n\n"
        if await user.premium or key not in ['magic-forest']:
            row.append(InlineKeyboardButton(text=dct['name'], callback_data=f"w_loc:{key}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        a += 1
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀ Назад", callback_data="w_location_back")])

    try:
        await message.delete()
    except Exception:
        pass

    from aiogram.types import FSInputFile
    photo_input = FSInputFile("images/actions/journey/preview.png")
    await bot.send_photo(
        chat_id=userid,
        photo=photo_input,
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )

@HDCallback
@main_router.callback_query(JourneySetupStates.selecting_location, F.data == "w_location_back")
async def back_to_bag(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    
    await state.set_state(JourneySetupStates.assembling_bag)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    state_data = await state.get_data()
    bag_selections = state_data.get("bag_selections", {})
    
    msg = await bot.send_message(userid, "🎒...")
    await render_bag_assembly_screen(msg, userid, bag_selections, lang, state)
    await callback.answer()

@HDCallback
@main_router.callback_query(JourneySetupStates.assembling_bag, F.data == "w_bag_done")
async def finish_bag_assembly(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    
    await state.set_state(JourneySetupStates.selecting_location)
    await render_location_selection(callback.message, userid, lang)
    await callback.answer()

@HDCallback
@main_router.callback_query(JourneySetupStates.selecting_location, F.data.startswith("w_loc:"))
async def select_location(callback: CallbackQuery, state: FSMContext):
    location = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    await state.update_data(location=location)
    await state.set_state(JourneySetupStates.selecting_duration)

    content_data = get_data('journey_start', lang)
    buttons = []
    row = []
    for key, dct in content_data['time_text'].items():
        row.append(InlineKeyboardButton(text=dct['text'], callback_data=f"w_dur:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀ Назад", callback_data="w_duration_back")])

    await callback.message.edit_caption(
        caption=content_data['time_info'],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="html"
    )
    await callback.answer()

@HDCallback
@main_router.callback_query(JourneySetupStates.selecting_duration, F.data == "w_duration_back")
async def back_to_location(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    
    await state.set_state(JourneySetupStates.selecting_location)
    await render_location_selection(callback.message, userid, lang)
    await callback.answer()

@HDCallback
@main_router.callback_query(JourneySetupStates.selecting_duration, F.data.startswith("w_dur:"))
async def select_duration_and_start(callback: CallbackQuery, state: FSMContext):
    duration_key = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    dino_ids_str = state_data.get("selected_dino_ids", [])
    bag_selections = state_data.get("bag_selections", {})
    location = state_data.get("location")

    content_data = get_data('journey_start', lang)
    duration_data = content_data['time_text'][duration_key]
    duration_seconds = duration_data['time']
    time_text = duration_data['text']

    dino_ids = [ObjectId(d_id) for d_id in dino_ids_str]

    bag_items = []
    for item_id, count in bag_selections.items():
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

    res = await JourneyActivity.start(dino_ids, userid, duration_seconds, location, bag_items)
    
    try:
        await callback.message.delete()
    except Exception:
        pass

    if res:
        loc_name = get_data(f"journey_start.locations.{location}", lang).get("name", location)
        text = t('journey_start.start', lang, loc_name=loc_name, time_text=time_text)
        await bot.send_message(userid, text)
        await bot.send_message(userid, t('journey_start.start_2', lang), reply_markup=await m(userid, 'actions_menu', lang))
    else:
        for bag_item in bag_items:
            await Item.add(userid, bag_item["item_id"], bag_item["count"], bag_item["abilities"])
        await bot.send_message(userid, "❌ Не удалось отправить в путешествие. Возможно, динозавры уже заняты.")

    await state.clear()
    await callback.answer()


# =====================================================================
# CHOICE CALLBACK HANDLER
# =====================================================================

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_choice "))
async def user_choice_callback(callback: CallbackQuery):
    parts = callback.data.split(" ")
    journey_id = parts[1]
    event_idx = int(parts[2])
    option_idx = int(parts[3])
    userid = callback.from_user.id
    lang = await get_lang(userid)

    journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
    if not journey:
        await callback.answer(t("not_found_key", lang), show_alert=True)
        return

    ev = journey.pregenerated_events[event_idx]
    if ev.get("status") != "waiting_choice":
        await callback.answer("Это событие уже завершено!", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    current_time = int(time())
    if current_time >= ev.get("timeout", 0):
        await callback.answer("Время ответа истекло!", show_alert=True)
        # Process expired choice
        try:
            await JourneyActivity.resolve_choice_event(journey, ev, option_idx=0, expired=True, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        except ValueError:
            pass
        return

    # Resolve choice
    try:
        await JourneyActivity.resolve_choice_event(journey, ev, option_idx=option_idx, expired=False, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        await callback.answer()
    except ValueError as e:
        from bot.modules.items.item import get_name
        missing_item_id = str(e)
        missing_item_name = get_name(missing_item_id, lang)
        alert_msg = f"У вас нет необходимого предмета: {missing_item_name}!"
        if lang != "ru":
            alert_msg = f"You do not have the required item: {missing_item_name}!"
        await callback.answer(alert_msg, show_alert=True)