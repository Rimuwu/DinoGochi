from bot.modules.get_state import get_state
from time import time
from bot.config import conf
from bot.models.activity.journey import locations
from bson import ObjectId

from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.exec import main_router, bot
from bot.modules.localization import t, get_data, get_lang
from bot.modules.markup import markups_menu as m
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.models.user import User
from bot.models.dinosaur import Dino, DinoStatus
from bot.models.activity import JourneyActivity
from bot.models.items import Item
from bot.redismanager import redis_get, redis_set

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat

class JourneySetupStates(StatesGroup):
    selecting_dinos = State()
    assembling_bag = State()
    selecting_location = State()
    selecting_duration = State()

# Main Activities Menu Hook
@main_router.message(IsPrivateChat(), Text('commands_name.actions.journey'))
async def journey_com(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    active_dino_id = user.settings.get('last_dino') if user else None

    active_journey = None
    if active_dino_id:
        active_journey = await JourneyActivity.find_one(
            JourneyActivity.userid == userid,
            JourneyActivity.dino_ids == active_dino_id
        )

    if active_journey:
        await show_active_journey_menu(chatid, userid, lang, active_journey, only_this_journey=True)
    elif active_dino_id:
        await show_idle_journey_menu(chatid, userid, lang)
    else:
        active_journeys = await JourneyActivity.find(
            JourneyActivity.userid == userid).to_list()
        if not active_journeys:
            await show_idle_journey_menu(chatid, userid, lang)
        elif len(active_journeys) == 1:
            await show_active_journey_menu(chatid, userid, lang, active_journeys[0])
        else:
            await show_active_journeys_list(chatid, userid, lang, active_journeys)

@main_router.message(IsPrivateChat(), Text('commands_name.actions.events'))
async def events_com(message: Message):
    await journey_com(message)

async def show_idle_journey_menu(chatid: int, userid: int, lang: str):
    active_journeys = await JourneyActivity.find(JourneyActivity.userid == userid).to_list()
    active_count = sum(len(j.dino_ids) for j in active_journeys)
    text = t("journey_menu.info", lang, active_count=active_count)
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
    loc_name = get_data(
        f"journey_start.locations.{journey.location}", lang).get(
            "name", journey.location)

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

async def show_active_journey_menu(chatid: int, userid: int, lang: str, journey: JourneyActivity, only_this_journey: bool = False):
    text, markup = await get_active_journey_text_and_markup(journey, lang, userid)

    dino_species_ids = []
    for d_id in journey.dino_ids:
        d = await Dino.find_one(Dino.id == d_id)
        if d:
            dino_species_ids.append(d.data_id)

    from bot.modules.images import dino_journey
    photo_input = await dino_journey(dino_species_ids, journey.location)
    
    if not only_this_journey:
        inline_kb = markup.inline_keyboard.copy()
        inline_kb.append([
            InlineKeyboardButton(text=t("journey_menu.buttons.send", lang), callback_data="j_send"),
            InlineKeyboardButton(text=t("journey_menu.buttons.history", lang), callback_data="j_hist:1")
        ])
        markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    
    msg = await bot.send_photo(chatid, photo=photo_input, caption=text, reply_markup=markup, parse_mode="html")
    # Save message_id for editing at journey end
    if journey.id:
        try:
            journey.status_message_id = msg.message_id
            await journey.save()
        except Exception:
            pass

async def show_active_journeys_list(chatid: int, userid: int, lang: str, journeys: list):
    text = t("journey_menu.multiple_active", lang, default="🗺 <b>Ваши группы в путешествии</b>\n\nВыберите группу для управления или отправьте новую:")

    buttons = []
    for idx, journey in enumerate(journeys, 1):
        dino_names = []
        for d_id in journey.dino_ids:
            dino = await Dino.find_one(Dino.id == d_id)
            if dino:
                dino_names.append(dino.name)

        loc_name = get_data(
            f"journey_start.locations.{journey.location}", lang).get(
                "name", journey.location)

        btn_text = t("journey_menu.group_button", lang, idx=idx, loc_name=loc_name, count=len(dino_names))
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"j_active_view:{journey.id}")])

    buttons.append([
        InlineKeyboardButton(text=t("journey_menu.buttons.send", lang), callback_data="j_send"),
        InlineKeyboardButton(text=t("journey_menu.buttons.history", lang), callback_data="j_hist:1")
    ])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")

@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_active_view:"))
async def active_journey_view_callback(callback: CallbackQuery):
    journey_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
    if not journey:
        await callback.answer(t("journey_menu.already_ended", lang), show_alert=True)
        await active_list_callback(callback)
        return

    text, markup = await get_active_journey_text_and_markup(journey, lang, userid)

    active_journeys = await JourneyActivity.find(
        JourneyActivity.userid == userid).to_list()

    inline_kb = markup.inline_keyboard.copy()
    if len(active_journeys) > 1:
        inline_kb.append([InlineKeyboardButton(text=t("journey_menu.buttons.to_list", lang), callback_data="j_active_list")])
    else:
        inline_kb.append([
            InlineKeyboardButton(text=t("journey_menu.buttons.send", lang), callback_data="j_send"),
            InlineKeyboardButton(text=t("journey_menu.buttons.history", lang), callback_data="j_hist:1")
        ])
    markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)

    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
    except Exception:
        await callback.message.edit_caption(caption=text, reply_markup=markup, parse_mode="html")

    await callback.answer()

@main_router.callback_query(IsPrivateChat(), F.data == "j_active_list")
async def active_list_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id

    user = await User.find_one(User.userid == userid)
    active_dino_id = user.settings.get('last_dino') if user else None

    active_journey = None
    if active_dino_id:
        active_journey = await JourneyActivity.find_one(
            JourneyActivity.userid == userid,
            JourneyActivity.dino_ids == active_dino_id
        )

    if active_journey:
        text, markup = await get_active_journey_text_and_markup(active_journey, lang, userid)

        dino_species_ids = []
        for d_id in active_journey.dino_ids:
            d = await Dino.find_one(Dino.id == d_id)
            if d:
                dino_species_ids.append(d.data_id)

        from bot.modules.images import dino_journey
        photo_input = await dino_journey(
            dino_species_ids, active_journey.location)

        try:
            await callback.message.delete()
        except Exception:
            pass
        await bot.send_photo(chatid, photo=photo_input, caption=text, reply_markup=markup, parse_mode="html")

    elif active_dino_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_idle_journey_menu(chatid, userid, lang)

    else:
        active_journeys = await JourneyActivity.find(JourneyActivity.userid == userid).to_list()
        if not active_journeys:
            text = t("journey_menu.info", lang, active_count=0)
            buttons = [
                {t("journey_menu.buttons.send", lang): "j_send"},
                {t("journey_menu.buttons.history", lang): "j_hist:1"}
            ]
            markup = list_to_inline(buttons, 1)
            try:
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
            except Exception:
                await callback.message.edit_caption(caption=text, reply_markup=markup, parse_mode="html")

        elif len(active_journeys) == 1:
            text, markup = await get_active_journey_text_and_markup(active_journeys[0], lang, userid)

            dino_species_ids = []
            for d_id in active_journeys[0].dino_ids:
                d = await Dino.find_one(Dino.id == d_id)
                if d:
                    dino_species_ids.append(d.data_id)

            from bot.modules.images import dino_journey
            photo_input = await dino_journey(
                dino_species_ids, active_journeys[0].location)

            inline_kb = markup.inline_keyboard.copy()
            inline_kb.append([
                InlineKeyboardButton(text=t("journey_menu.buttons.send", lang), callback_data="j_send"),
                InlineKeyboardButton(text=t("journey_menu.buttons.history", lang), callback_data="j_hist:1")
            ])
            markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)

            try:
                await callback.message.delete()
            except Exception:
                pass
            await bot.send_photo(chatid, photo=photo_input, caption=text, reply_markup=markup, parse_mode="html")
        else:
            text = t("journey_menu.multiple_active", lang, default="🗺 <b>Ваши группы в путешествии</b>\n\nВыберите группу для управления или отправьте новую:")
            buttons = []
            for idx, j in enumerate(active_journeys, 1):
                dino_names = []
                for d_id in j.dino_ids:
                    dino = await Dino.find_one(Dino.id == d_id)
                    if dino:
                        dino_names.append(dino.name)

                loc_name = get_data(f"journey_start.locations.{j.location}", lang).get("name", j.location)
                btn_text = t("journey_menu.group_button", lang, idx=idx, loc_name=loc_name, count=len(dino_names))
                buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"j_active_view:{j.id}")])

            buttons.append([
                InlineKeyboardButton(text=t("journey_menu.buttons.send", lang), callback_data="j_send"),
                InlineKeyboardButton(text=t("journey_menu.buttons.history", lang), callback_data="j_hist:1")
            ])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            try:
                await callback.message.delete()
            except Exception:
                pass
            await bot.send_message(chatid, text, reply_markup=markup, parse_mode="html")

    await callback.answer()


# Back to main menu callback
@main_router.callback_query(IsPrivateChat(), F.data == "j_active_menu")
async def active_menu_callback(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    chatid = callback.message.chat.id

    user = await User.find_one(User.userid == userid)
    active_dino_id = user.settings.get('last_dino') if user else None

    active_journey = None
    if active_dino_id:
        active_journey = await JourneyActivity.find_one(
            JourneyActivity.userid == userid,
            JourneyActivity.dino_ids == active_dino_id
        )

    if active_journey:
        text, markup = await get_active_journey_text_and_markup(active_journey, lang, userid)
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
        except Exception:
            await callback.message.edit_caption(caption=text, reply_markup=markup, parse_mode="html")
    elif active_dino_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_idle_journey_menu(chatid, userid, lang)
    else:
        journey = await JourneyActivity.find_one(JourneyActivity.userid == userid)
        if journey:
            active_journeys = await JourneyActivity.find(
                JourneyActivity.userid == userid).to_list()
            if len(active_journeys) > 1:
                await active_list_callback(callback)
                return
        
            text, markup = await get_active_journey_text_and_markup(journey, lang, userid)
            inline_kb = markup.inline_keyboard.copy()
            inline_kb.append([
                InlineKeyboardButton(text=t("journey_menu.buttons.send", lang), callback_data="j_send"),
                InlineKeyboardButton(text=t("journey_menu.buttons.history", lang), callback_data="j_hist:1")
            ])
            markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)
            try:
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="html")
            except Exception:
                await callback.message.edit_caption(caption=text, reply_markup=markup, parse_mode="html")
        else:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await show_idle_journey_menu(chatid, userid, lang)

    await callback.answer()

# Stop/Cancel journey callback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_stop:"))
async def stop_journey_callback(callback: CallbackQuery):
    journey_id = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
    if journey and journey.userid == userid:
        # Load all dino names
        dino_names = []
        for d_id in journey.dino_ids:
            dino_obj = await Dino.find_one(Dino.id == d_id)
            if dino_obj:
                dino_names.append(dino_obj.name)
        dinos_str = ", ".join(dino_names) if dino_names else "динозавр"

        # End journey in model (clear status_message_id so end() won't double-edit)
        journey.end_time = int(time())
        journey.status_message_id = None
        await journey.save()
        journey_id_str = str(journey.id)
        await JourneyActivity.end(journey.id)

        log_markup = list_to_inline([
            {t("journey_menu.buttons.logs", lang): f"j_hlog:{journey_id_str}:1"}
        ])

        from bot.modules.items.item import counts_items
        from bot.modules.localization import get_data as _get_data
        items_str_raw = counts_items(journey.items, lang) if journey.items else "-"
        def wrap_text_in_code(p: str) -> str:
            import re
            prefix_parts = []
            rest = p
            while True:
                m_custom = re.match(r'^(!\[.*?\]\(tg://emoji\?id=\d+\)\s*)', rest)
                if m_custom:
                    prefix_parts.append(m_custom.group(1))
                    rest = rest[len(m_custom.group(1)):]
                    continue
                m_std = re.match(r'^([\u2600-\u27BF\U0001f300-\U0001f64F\U0001f680-\U0001f6FF\U0001f900-\U0001f9FF\U0001f1e0-\U0001f1ff]\s*)', rest)
                if m_std:
                    prefix_parts.append(m_std.group(1))
                    rest = rest[len(m_std.group(1)):]
                    continue
                m_sym = re.match(r'^([↳🔹⛺🐊🏛️❓🪨📍⏱🦖🪙🎒⏱]\s*)', rest)
                if m_sym:
                    prefix_parts.append(m_sym.group(1))
                    rest = rest[len(m_sym.group(1)):]
                    continue
                break
            prefix = "".join(prefix_parts)
            return f"{prefix}`{rest}`" if rest else prefix

        if journey.items:
            items_parts = [p.strip() for p in items_str_raw.split(',') if p.strip()]
            items_str = ", ".join(wrap_text_in_code(p) for p in items_parts)
        else:
            items_str = "-"
        log_key = "journey_log_plural" if len(dino_names) > 1 else "journey_log"
        log_text = t(log_key, lang, coins=journey.coins, items=items_str, time=seconds_to_str(int(time()) - journey.start_time, lang), col=len(journey.completed_log), name=dinos_str)

        # Append route map
        map_lines = []
        for node in getattr(journey, 'route_path', []):
            node_type = node.get("type")
            node_name = node.get("name")
            depth = node.get("depth", 0)
            indent = "  " * depth
            if node_type == "location":
                loc_data = _get_data(f"journey_start.locations.{node_name}", lang)
                loc_lbl = loc_data.get("name", node_name) if isinstance(loc_data, dict) else node_name
                map_lines.append(f"{indent}📍 {loc_lbl}")
            elif node_type == "sub_location":
                sub_data = _get_data(f"journey_start.sub_locations.{node_name}", lang)
                sub_lbl = sub_data.get("name", node_name) if isinstance(sub_data, dict) else node_name
                sub_emoji = sub_data.get("emoji", "🕳️") if isinstance(sub_data, dict) else "🕳️"
                map_lines.append(f"{indent}↳ {sub_emoji} {sub_lbl}")
            elif node_type == "choice":
                choice_data = _get_data(f"journey_choices.{node_name}", lang)
                choice_lbl = choice_data.get("name", node_name) if isinstance(choice_data, dict) else node_name
                map_lines.append(f"  {indent}↳ ❓ {choice_lbl}")
        if map_lines:
            log_text += f"\n\n{t('journey.route_map', lang, default='🗺️ <b>Journey Map:</b>')}\n" + "\n".join(map_lines)

        try:
            await callback.message.edit_caption(caption=log_text, reply_markup=log_markup, parse_mode="html")
        except Exception:
            try:
                await callback.message.edit_text(log_text, reply_markup=log_markup, parse_mode="html")
            except Exception:
                pass

    await callback.answer()

# Log Pagination Callback
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_active_log:"))
async def active_log_pagination(callback: CallbackQuery):
    parts = callback.data.split(":")
    journey_id = parts[1]
    page = int(parts[2])
    userid = callback.from_user.id
    lang = await get_lang(userid)

    journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
    if not journey:
        await callback.answer(t("journey_menu.already_ended", lang), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
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
        nav_buttons.append(InlineKeyboardButton(text="◀", callback_data=f"j_active_log:{journey_id}:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶", callback_data=f"j_active_log:{journey_id}:{page + 1}"))

    buttons = [nav_buttons] if nav_buttons else []
    buttons.append([
        InlineKeyboardButton(
            text=t("journey_menu.buttons.back_to_journey", lang), 
            callback_data="j_active_menu")])

    try:
        await callback.message.edit_caption(
            caption=text, reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons), parse_mode="html")
    except Exception:
        await callback.message.edit_text(
            text=text, reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons), parse_mode="html")
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
        nav_buttons.append(InlineKeyboardButton(text=t("journey_menu.buttons.prev_page", lang, default="◄ Назад"), callback_data=f"j_hist:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text=t("journey_menu.buttons.next_page", lang, default="Далее ►"), callback_data=f"j_hist:{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text=t("journey_menu.buttons.back", lang), callback_data="j_active_menu")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await message.edit_text(t("journey_menu.history_title", lang), reply_markup=markup, parse_mode="html")
    except Exception:
        await message.edit_caption(caption=t("journey_menu.history_title", lang), reply_markup=markup, parse_mode="html")

# Completed Journey History Callback (from Redis)
@main_router.callback_query(IsPrivateChat(), F.data.startswith("j_hist:"))
async def journey_history_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    userid = callback.from_user.id
    lang = await get_lang(userid)
    await _render_history_list(callback.message, userid, lang, page)
    await callback.answer()

# Completed Journey Details Callback
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
    def wrap_text_in_code(p: str) -> str:
        import re
        prefix_parts = []
        rest = p
        while True:
            m_custom = re.match(r'^(!\[.*?\]\(tg://emoji\?id=\d+\)\s*)', rest)
            if m_custom:
                prefix_parts.append(m_custom.group(1))
                rest = rest[len(m_custom.group(1)):]
                continue
            m_std = re.match(r'^([\u2600-\u27BF\U0001f300-\U0001f64F\U0001f680-\U0001f6FF\U0001f900-\U0001f9FF\U0001f1e0-\U0001f1ff]\s*)', rest)
            if m_std:
                prefix_parts.append(m_std.group(1))
                rest = rest[len(m_std.group(1)):]
                continue
            m_sym = re.match(r'^([↳🔹⛺🐊🏛️❓🪨📍⏱🦖🪙🎒⏱]\s*)', rest)
            if m_sym:
                prefix_parts.append(m_sym.group(1))
                rest = rest[len(m_sym.group(1)):]
                continue
            break
        prefix = "".join(prefix_parts)
        return f"{prefix}`{rest}`" if rest else prefix

    if details["items"]:
        items_str_raw = counts_items(details["items"], lang)
        items_parts = [p.strip() for p in items_str_raw.split(',') if p.strip()]
        items_text = ", ".join(wrap_text_in_code(p) for p in items_parts)
    else:
        items_text = "-"

    text = t("journey_menu.details", lang,
             location=loc_name,
             duration=duration,
             dinos=details["dinos"],
             coins=details["coins"],
             items=items_text,
             events_count=len(details["journey_log"]))

    # Append journey route map
    map_lines = []
    for node in details.get("route_path", []):
        node_type = node.get("type")
        node_name = node.get("name")
        depth = node.get("depth", 0)
        indent = "  " * depth
        if node_type == "location":
            loc_data = get_data(f"journey_start.locations.{node_name}", lang)
            loc_lbl = loc_data.get("name", node_name) if isinstance(loc_data, dict) else node_name
            map_lines.append(f"{indent}📍 {loc_lbl}")

        elif node_type == "sub_location":
            sub_data = get_data(f"journey_start.sub_locations.{node_name}", lang)
            sub_lbl = sub_data.get("name", node_name) if isinstance(sub_data, dict) else node_name
            sub_emoji = sub_data.get("emoji", "🕳️") if isinstance(sub_data, dict) else "🕳️"
            map_lines.append(f"{indent}↳ {sub_emoji} {sub_lbl}")

        elif node_type == "choice":
            choice_data = get_data(f"journey_choices.{node_name}", lang)
            choice_lbl = choice_data.get("name", node_name) if isinstance(choice_data, dict) else node_name
            if "no_text_key" in str(choice_lbl):
                choice_lbl = t(f"journey_choices.{node_name}.text", lang)[:20] + "..."
            choice_indent = "  " * (depth + 1)
            map_lines.append(f"{choice_indent}↳ ❓ {choice_lbl}")

    route_map_str = "\n".join(map_lines)
    if route_map_str:
        text += t("journey_menu.route_map", lang, route=route_map_str)

    buttons = [
        [InlineKeyboardButton(text=t("journey_menu.buttons.logs", lang), callback_data=f"j_hlog:{journey_id}:1")],
        [
            InlineKeyboardButton(text=t("journey_menu.buttons.delete_history", lang), callback_data=f"j_hdelete:{journey_id}"),
            InlineKeyboardButton(text=t("journey_menu.buttons.back_to_list", lang), callback_data="j_hist:1")
        ]
    ]

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")
    except Exception:
        await callback.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")

    await callback.answer()

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
        await callback.message.edit_text(t("journey_menu.no_events", lang), reply_markup=list_to_inline([{t("journey_menu.buttons.back", lang): f"j_hdetails:{journey_id}"}]))
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
        if not ev_msg.strip().startswith("↳"):
            root_count += 1

    lines = []
    for ev in page_events:
        ev_msg = await JourneyActivity.generate_event_message(ev, lang, ObjectId(journey_id))
        if ev_msg.strip().startswith("↳"):
            lines.append(ev_msg)
        else:
            root_count += 1
            lines.append(f"🔹 <b>{root_count}.</b> {ev_msg}")
    
    text = t("journey_menu.log_title", lang, page=page, pages=total_pages) + "\n\n" + "\n\n".join(lines)

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text=t("journey_menu.buttons.prev", lang), callback_data=f"j_hlog:{journey_id}:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text=t("journey_menu.buttons.next", lang), callback_data=f"j_hlog:{journey_id}:{page + 1}"))

    buttons = [nav_buttons] if nav_buttons else []
    buttons.append([InlineKeyboardButton(text=t("journey_menu.buttons.back", lang), callback_data=f"j_hdetails:{journey_id}")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")
    except Exception:
        await callback.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")
    await callback.answer()


# =====================================================================
# WIZARD: dinosaur selection & bag assembly
# =====================================================================

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
        status = await d.check_status()
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
        InlineKeyboardButton(text=t("journey_setup.back", lang, default="◀ Назад"), callback_data="j_active_menu"),
        InlineKeyboardButton(text=t("journey_setup.next", lang, default="Далее ▶"), callback_data="w_dino_done")
    ]
    buttons.append(nav_row)

    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="html")

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

async def bag_assembly_fabric_callback(return_data: dict, trans_data: dict):
    userid = trans_data['userid']
    chatid = trans_data['chatid']
    lang = trans_data['lang']
    selected_dinos = trans_data['selected_dino_ids']
    chosen_items = return_data.get('bag_items', [])

    # Calculate capacity: 10 per dino + equipped backpacks + packed journey bags
    from bot.models.dinosaur import Dino
    from bot.models.items import Item
    from bot.modules.items.item import get_item_capacity, get_data as get_item_data_

    dino_db_ids = []
    for d_val in selected_dinos:
        dino_obj = Dino()
        if await dino_obj.create(d_val):
            dino_db_ids.append(dino_obj.id)

    backpack_cap = 0
    for dino_id in dino_db_ids:
        accs = await Item.find_accessory(dino_id, 'backpack')
        backpack_cap += sum(get_item_capacity(acc.items_data) for acc in accs)

    base_cap = 10 * len(selected_dinos)

    # Sum capacity of journey bags packed in chosen_items
    journey_cap = sum(get_item_capacity(item) * item.get('count', 0)
                      for item in chosen_items
                      if get_item_data_(item.get('item_id', '')).get('type') == 'journey')

    max_capacity = base_cap + backpack_cap + journey_cap
    current_total = sum(item['count'] for item in chosen_items)

    if current_total > max_capacity:
        from bot.modules.markup import markups_menu as m
        await bot.send_message(
            chatid,
            t("journey_setup.bag_full_error", lang, 
              current_total=current_total, 
              max_capacity=max_capacity,
              default=f"❌ Сумка переполнена! Выбрано {current_total}/{max_capacity} предметов. Пожалуйста, соберите сумку повторно."),
            reply_markup=await m(userid, 'last_menu', lang)
        )
        return

    # Save to state and proceed to location selection
    state = await get_state(userid, chatid)
    bag_selections = {item['item_id']: item['count'] for item in chosen_items}
    selected_multinv = trans_data.get('selected_multinv', {})
    await state.update_data(
        selected_dino_ids=selected_dinos,
        bag_selections=bag_selections,
        selected_multinv=selected_multinv
    )

    await state.set_state(JourneySetupStates.selecting_location)
    msg = await bot.send_message(chatid, "🗺️...")
    await render_location_selection(msg, userid, lang)

@main_router.callback_query(JourneySetupStates.selecting_dinos, F.data == "w_dino_done")
async def finish_dino_selection(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    selected = state_data.get("selected_dino_ids", [])

    if not selected:
        await callback.answer(t("journey_setup.select_at_least_one_dino", lang), show_alert=True)
        return

    # Proceed to bag assembly via ChooseStepHandler
    from bot.modules.states_fabric.state_handlers import ChooseStepHandler
    from bot.modules.states_fabric.steps_datatype import MultiInventoryStepData, StepMessage
    from bot.modules.items.item import get_item_capacity

    inventory, _ = await User.get_inventory(userid, [])

    # Calculate capacity: 10 per dino + capacity of equipped backpacks
    from bot.models.dinosaur import Dino
    from bot.models.items import Item

    dino_db_ids = []
    for d_val in selected:
        dino_obj = Dino()
        if await dino_obj.create(d_val):
            dino_db_ids.append(dino_obj.id)

    backpack_cap = 0
    for dino_id in dino_db_ids:
        accs = await Item.find_accessory(dino_id, 'backpack')
        backpack_cap += sum(get_item_capacity(acc.items_data) for acc in accs)

    base_cap = 10 * len(selected)
    bag_limit = base_cap + backpack_cap

    from bot.modules.logs import log
    log(prefix="journey_capacity", lvl=0,
        message=f"Starting journey bag limit setup: base_cap={base_cap}, backpack_cap={backpack_cap} (dinos={len(selected)}), bag_limit={bag_limit}")

    steps = [
        MultiInventoryStepData('bag_items', StepMessage(
            text=t('journey_setup.bag_title_fabric', lang, default="🎒 *Сбор сумки*\n\nВыберите любые предметы из инвентаря, которые хотите взять с собой в путешествие:"),
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

    transmitted_data = {
        'selected_dino_ids': selected,
    }

    try:
        await callback.message.delete()
    except Exception:
        pass

    await ChooseStepHandler(bag_assembly_fabric_callback, userid,
                            callback.message.chat.id, lang, steps,
                            transmitted_data).start()
    await callback.answer()

async def render_location_selection(message: Message, userid: int, lang: str):
    from bot.modules.user.friends import get_frineds
    friends_data = await get_frineds(userid)
    friends_list = friends_data.get("friends", [])

    content_data = get_data('journey_start', lang)
    text = content_data['ask_loc']
    buttons = []
    
    # Build mob info per location from journey_config
    from bot.const import MOBS
    import json as _json
    try:
        with open('bot/json/journey_config.json', encoding='utf-8') as _f:
            jcfg = _json.load(_f)
    except Exception:
        jcfg = {}
    loc_mobs_cfg = jcfg.get('locations', {})
    mobs_loc = get_data('mobs', lang) or {}

    user = await User().create(userid)
    a = 1
    row = []
    for key, dct in content_data['locations'].items():
        active_journeys = await JourneyActivity.find(JourneyActivity.location == key).to_list()
        friends_count = sum(len(j.dino_ids) for j in active_journeys if j.userid in friends_list)
        friends_text = t('journey_start.friends_here', lang, count=friends_count) if friends_count > 0 else ""

        # Mob info for location
        mobs_val = loc_mobs_cfg.get(key, {}).get('mobs', [])
        if isinstance(mobs_val, dict):
            if 'mobs' in mobs_val and isinstance(mobs_val['mobs'], list):
                loc_mob_ids = mobs_val['mobs']
            else:
                loc_mob_ids = list(mobs_val.keys())
        elif isinstance(mobs_val, list):
            loc_mob_ids = mobs_val
        else:
            loc_mob_ids = []

        if loc_mob_ids:
            import html as _html
            sample_mobs = loc_mob_ids[:4]
            mob_line = ', '.join(
                f"{mobs_loc.get(m, {}).get('emoji', '')} {mobs_loc.get(m, {}).get('name', m)}".strip()
                for m in sample_mobs
            )
            if len(loc_mob_ids) > 4:
                mob_line += t('journey_start.and_more', lang, count=len(loc_mob_ids)-4)
            mob_text = t('journey_start.mobs_label', lang, mobs=_html.escape(mob_line))
        else:
            mob_text = ""

        diff_text = t('journey_start.difficulty_label', lang, difficulty=dct['difficulty']) if 'difficulty' in dct else ""
        prem_text = t('journey_start.premium_label', lang, premium=dct['premium']) if 'premium' in dct else ""

        text += f"<b>{a}</b>. {dct['text']}{diff_text}{prem_text}{friends_text}{mob_text}\n\n"
        emoji = dct.get('emoji', '')
        btn_text = f"{emoji} {dct['name']}".strip() if emoji else dct['name']
        if await user.premium or key not in ['magic-forest']:
            row.append(InlineKeyboardButton(text=btn_text, callback_data=f"w_loc:{key}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        a += 1
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=t("journey_menu.buttons.back", lang), callback_data="w_location_back")])

    # Delete previous complexity message if it exists
    state = await get_state(userid, userid)
    state_data = await state.get_data()
    comp_msg_id = state_data.get("complexity_msg_id")
    if comp_msg_id:
        try:
            await bot.delete_message(userid, comp_msg_id)
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass

    from aiogram.types import FSInputFile
    photo_input = FSInputFile("images/actions/journey/preview.png")
    if len(text) <= 1000:
        main_msg = await bot.send_photo(
            chat_id=userid,
            photo=photo_input,
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    else:
        try:
            await bot.send_photo(chat_id=userid, photo=photo_input)
        except Exception:
            pass
        main_msg = await bot.send_message(
            chat_id=userid,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )

    comp_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=content_data['complexity']['button'], callback_data="w_complexity")]
    ])
    comp_msg = await bot.send_message(
        chat_id=userid,
        text=content_data['complexity']['text'],
        reply_markup=comp_markup,
        parse_mode="HTML"
    )
    await state.update_data(complexity_msg_id=comp_msg.message_id)

@main_router.callback_query(
    JourneySetupStates.selecting_location, F.data == "w_complexity")
async def show_complexity_info(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    text = t("journey_complexity", lang)
    buttons = [
        [InlineKeyboardButton(text=t("journey_menu.buttons.back", lang), callback_data="w_location_back_from_comp")]
    ]
    await callback.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )
    await callback.answer()

@main_router.callback_query(
    JourneySetupStates.selecting_location, F.data == "w_location_back_from_comp")
async def back_from_complexity(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    content_data = get_data('journey_start', lang)
    comp_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=content_data['complexity']['button'], callback_data="w_complexity")]
    ])
    await callback.message.edit_text(
        text=content_data['complexity']['text'],
        reply_markup=comp_markup,
        parse_mode="HTML"
    )
    await callback.answer()

@main_router.callback_query(
    JourneySetupStates.selecting_location, F.data == "w_location_back")
async def back_to_bag(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    selected_dinos = state_data.get("selected_dino_ids", [])
    selected_multinv = state_data.get("selected_multinv", {})

    comp_msg_id = state_data.get("complexity_msg_id")
    if comp_msg_id:
        try:
            await bot.delete_message(userid, comp_msg_id)
        except Exception:
            pass

    await state.clear()

    from bot.modules.states_fabric.state_handlers import ChooseStepHandler
    from bot.modules.states_fabric.steps_datatype import MultiInventoryStepData, StepMessage
    from bot.modules.items.item import get_item_capacity

    inventory, _ = await User.get_inventory(userid, [])

    # Calculate capacity: 10 per dino + capacity of equipped backpacks
    from bot.models.dinosaur import Dino
    from bot.models.items import Item

    dino_db_ids = []
    for d_val in selected_dinos:
        dino_obj = Dino()
        if await dino_obj.create(d_val):
            dino_db_ids.append(dino_obj.id)

    backpack_cap = 0
    for dino_id in dino_db_ids:
        accs = await Item.find_accessory(dino_id, 'backpack')
        backpack_cap += sum(get_item_capacity(acc.items_data) for acc in accs)

    base_cap = 10 * len(selected_dinos)
    bag_limit = base_cap + backpack_cap

    from bot.modules.logs import log
    log(prefix="journey_capacity", lvl=0,
        message=f"Back to bag limit setup: base_cap={base_cap}, backpack_cap={backpack_cap} (dinos={len(selected_dinos)}), bag_limit={bag_limit}")

    steps = [
        MultiInventoryStepData('bag_items', StepMessage(
            text=t('journey_setup.bag_title_fabric', lang, default="🎒 *Сбор сумки*\n\nВыберите любые предметы из инвентаря, которые хотите взять с собой в путешествие:"),
            translate_message=False,
        ), inventory=inventory, limit=bag_limit, limit_type='journey_bag', empty_allowed=True, selected=selected_multinv,
           filter_interact=False, filter_cant_sell=False)
    ]

    transmitted_data = {
        'selected_dino_ids': selected_dinos,
    }

    try:
        await callback.message.delete()
    except Exception:
        pass

    await ChooseStepHandler(bag_assembly_fabric_callback, userid,
                            callback.message.chat.id, lang, steps,
                            transmitted_data).start()
    await callback.answer()

@main_router.callback_query(JourneySetupStates.selecting_location, F.data.startswith("w_loc:"))
async def select_location(callback: CallbackQuery, state: FSMContext):
    location = callback.data.split(":")[1]
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state_data = await state.get_data()
    comp_msg_id = state_data.get("complexity_msg_id")
    if comp_msg_id:
        try:
            await bot.delete_message(userid, comp_msg_id)
        except Exception:
            pass

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

    buttons.append([InlineKeyboardButton(text=t("journey_setup.back", lang, default="◀ Назад"), callback_data="w_duration_back")])

    if callback.message.caption is not None:
        await callback.message.edit_caption(
            caption=content_data['time_info'],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="html"
        )
    else:
        await callback.message.edit_text(
            text=content_data['time_info'],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="html"
        )
    await callback.answer()

@main_router.callback_query(JourneySetupStates.selecting_duration, F.data == "w_duration_back")
async def back_to_location(callback: CallbackQuery, state: FSMContext):
    userid = callback.from_user.id
    lang = await get_lang(userid)

    await state.set_state(JourneySetupStates.selecting_location)
    await render_location_selection(callback.message, userid, lang)
    await callback.answer()

@main_router.callback_query(
    JourneySetupStates.selecting_duration, F.data.startswith("w_dur:"))
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
        await bot.send_message(userid, t("journey_start.start_failed", lang))

    await state.clear()
    await callback.answer()


# =====================================================================
# CHOICE CALLBACK HANDLER
# =====================================================================

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
        await callback.answer(t("journey_menu.already_ended", lang), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    ev = journey.pregenerated_events[event_idx]
    if ev.get("status") != "waiting_choice":
        await callback.answer(t("journey_menu.already_completed", lang), show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    current_time = int(time())
    if current_time >= ev.get("timeout", 0):
        await callback.answer(t("journey_menu.timeout", lang), show_alert=True)
        # Process expired choice
        resolved = False
        for opt_i in range(len(ev.get("event_data", {}).get("outcomes", []))):
            try:
                await JourneyActivity.resolve_choice_event(journey, ev, option_idx=opt_i, expired=True, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
                resolved = True
                break
            except ValueError:
                continue
        if not resolved:
            try:
                await JourneyActivity.resolve_choice_event(journey, ev, option_idx=0, expired=True, force=True, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
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
        alert_msg = t("journey_menu.missing_item", lang, name=missing_item_name)
        await callback.answer(alert_msg, show_alert=True)