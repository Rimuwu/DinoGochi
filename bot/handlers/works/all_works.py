from bot.models.dinosaur import Dino, DinoMood
from time import time

from bson import ObjectId

from bot.exec import main_router, bot
from bot.models.dinosaur import Dino
from bot.models.activity import WorkActivity, Activity
from bot.modules.items.item import get_items_names
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import dino_notification
from bot.modules.states_fabric.state_handlers import ChooseOptionHandler
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, list_to_keyboard, progress_bar

from bot.filters.translated_text import StartWith, Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from aiogram import F

async def start_work_for_dino(dino: Dino, userid: int, work_type: str, target_option: str, lang: str):
    percent, _ = await dino.memory_percent('action', work_type, True)
    await DinoMood.repeat_activity(dino._id, percent)

    if work_type == 'mine':
        await WorkActivity.start_mine(dino._id, userid, target_option)
    elif work_type == 'bank':
        await WorkActivity.start_bank(dino._id, userid, target_option)
    elif work_type == 'sawmill':
        await WorkActivity.start_sawmill(dino._id, userid, target_option)

    return t(f'works.start.{work_type}', lang)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('work_start_inline'))
async def work_start_inline_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    chatid = call.message.chat.id
    data = call.data.split()

    dino_alt_id = data[1]
    work_type = data[2]
    target_option = data[3]

    dino = await Dino.find_one(Dino.alt_id == dino_alt_id)
    if not dino:
        await call.answer(t('css.no_dino', lang), show_alert=True)
        return

    st = await dino.status
    st_val = st.value if hasattr(st, 'value') else str(st)
    if st_val != 'pass':
        await call.answer(f"🦕 {dino.name}: {t('alredy_busy', lang)}", show_alert=True)
        return

    res_text = await start_work_for_dino(dino, userid, work_type, target_option, lang)
    await call.answer(f"🦕 {dino.name}: {res_text}")
    mes = await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>: {res_text}", reply_markup=await m(userid, 'extraction_actions_menu', lang, True))
    await auto_ads(mes)


async def get_works_progress_page(userid: int, lang: str, page: int = 0):
    user = await User().create(userid)
    dinos = await user.get_dinos()
    from beanie.operators import In

    working_dinos = []
    for dino in dinos:
        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val in ['bank', 'mine', 'sawmill']:
            activ = await Activity.find_one(
                Activity.activity_type == st_val,
                Activity.dino.id == dino.id
            )
            if activ:
                working_dinos.append((dino, activ))

    if not working_dinos:
        return None, None

    total_pages = len(working_dinos)
    page = max(0, min(page, total_pages - 1))
    dino, activ = working_dinos[page]
    activ_dict = activ.dict()
    status = activ_dict['activity_type']

    time_ost = int(time()) - activ_dict['start_time']
    time_end = activ_dict['end_time'] - activ_dict['start_time']
    time_bar = progress_bar(time_ost, time_end, 5, '⌛', '⚪', '[', ']')

    storage_max = 1
    storage_now = 0
    if activ_dict.get('coins') is not None:
        storage_max = activ_dict.get('max_coins') or 1
        storage_now = activ_dict.get('coins') or 0
    elif activ_dict.get('items') is not None:
        storage_max = activ_dict.get('max_items') or 1
        storage_now = 0
        for key, item in activ_dict['items'].items():
            storage_now += item['count']

    emoji_data = get_data(f'works.progress.{status}-emoji', lang)
    if not isinstance(emoji_data, list) or len(emoji_data) < 2:
        emoji_data = ['🍕', '⚪']
    storage_bar = progress_bar(storage_now, storage_max, 5, emoji_data[0], emoji_data[1], start_text='[', end_text=']')

    check_max = 3
    check_now = activ_dict.get('checks', 0)
    check_bar = progress_bar(check_now, check_max, 3, '👁', '⚪', '[', ']')

    info_body = t(f'works.progress.{status}', lang, time_bar=time_bar, storage_bar=storage_bar, check_bar=check_bar)
    header = f"<b>{t('works.progress_title', lang)}</b> ({page + 1}/{total_pages})"
    
    full_text = f"{header}\n\n🦕 <b>{dino.name}</b>:\n<blockquote>{info_body}</blockquote>"

    buttons = []
    action_row = []
    if check_now > 0:
        action_row.append({"text": t('works.buttons.check', lang), "callback_data": f"progress_work check {dino.id} {page}"})
    action_row.append({"text": t('commands_name.extraction_actions.stop_work', lang), "callback_data": f"stop_extraction_inline {dino.id} {page}"})
    buttons.append(action_row)

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"text": "⬅️", "callback_data": f"works_prog_page {prev_p}"},
            {"text": f"{page + 1} / {total_pages}", "callback_data": "None"},
            {"text": "➡️", "callback_data": f"works_prog_page {next_p}"}
        ]
        buttons.append(nav_row)

    return full_text, list_to_inline(buttons)


@main_router.message(
    IsPrivateChat(), Text('commands_name.extraction_actions.progress'))
async def progress(message: Message):
    if not message or not message.from_user:
        return

    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    chatid = message.chat.id

    full_text, inline = await get_works_progress_page(userid, lang, 0)
    if not inline:
        await bot.send_message(chatid, t('works.no_works', lang), reply_markup=await m(userid, 'extraction_actions_menu', lang))
    else:
        await bot.send_message(chatid, full_text, reply_markup=inline)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('works_prog_page'))
async def works_prog_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    data = call.data.split()
    target_page = int(data[1]) if len(data) > 1 and data[1].isdigit() else 0

    full_text, inline = await get_works_progress_page(userid, lang, target_page)
    if inline:
        try:
            await call.message.edit_text(full_text, reply_markup=inline)
        except Exception: pass
    else:
        try:
            await call.message.edit_text(t('works.no_works', lang))
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('progress_work'))
async def progress_work(call: CallbackQuery):
    if not call or not call.message or not call.from_user or not call.data:
        return

    chatid = call.message.chat.id
    userid = call.from_user.id
    data = call.data.split()

    try:
        action = data[1]
        dino_id_str = data[2]
        page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0
    except (IndexError, ValueError):
        return

    lang = await get_lang(userid)
    dino = await Dino().create(dino_id_str)
    if not dino:
        await call.answer(t('css.no_dino', lang), show_alert=True)
        return

    from beanie.operators import In
    res = await Activity.find_one(
        In(Activity.activity_type, ['bank', 'mine', 'sawmill']),
        Activity.dino.id == dino.id
    )

    if res:
        res_dict = res.dict()
        if action == 'check':
            if res_dict.get('checks', 0) != 0:
                await res.update({'$inc': {'checks': -1}})

                if res_dict.get('coins') is not None:
                    text = t('works.storage.coins', lang, 
                          coins=res_dict['coins'],
                          max_coins=res_dict['max_coins'])
                elif res_dict.get('items') is not None:
                    count = 0
                    for key, item in res_dict['items'].items(): count += item['count']

                    text = t('works.storage.items', lang, 
                          items=get_items_names(list(res_dict['items'].values()), lang),
                          count=count,
                          max_count=res_dict['max_items'])
                else:
                    text = "📦"

                await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>\n{text}", reply_markup=await m(userid, 'last_menu', lang))

        full_text, inline = await get_works_progress_page(userid, lang, page)
        if inline:
            try:
                await call.message.edit_text(full_text, reply_markup=inline)
            except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('stop_extraction_inline'))
async def stop_extraction_inline_calb(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)
    data = call.data.split()
    dino_id_str = data[1]
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    dino = await Dino().create(dino_id_str)
    if not dino:
        await call.answer(t('css.no_dino', lang), show_alert=True)
        return

    from beanie.operators import In
    res = await Activity.find_one(
        In(Activity.activity_type, ['bank', 'mine', 'sawmill']),
        Activity.dino.id == dino.id,
        with_children=True
    )

    if res:
        res_dict = res.dict()
        if res_dict.get('coins') is not None:
            text = t('works.stop.coins', lang, coins=res_dict['coins'])
        elif res_dict.get('items') is not None:
            text = t('works.stop.items', lang, items=get_items_names(list(res_dict['items'].values()), lang))
        else:
            text = ""

        await WorkActivity.end_work(dino.id)
        await dino_notification(dino.id, f'{res.activity_type}_end', results=text)
        await call.answer()

        if text:
            await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n{text}")

        full_text, inline = await get_works_progress_page(userid, lang, page)
        if inline:
            try:
                await call.message.edit_text(full_text, reply_markup=inline)
            except Exception: pass
        else:
            try:
                await call.message.edit_text(t('works.no_works', lang))
            except Exception: pass
    else:
        await call.answer("❌", show_alert=False)


@main_router.message(IsPrivateChat(), Text('commands_name.extraction_actions.stop_work'))
async def stop_work(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    from beanie.operators import In
    stopped_reports = []
    for dino in last_dinos:
        res = await Activity.find_one(
            In(Activity.activity_type, ['bank', 'mine', 'sawmill']),
            Activity.dino.id == dino.id,
            with_children=True
        )

        if res:
            res_dict = res.dict()
            if res_dict.get('coins') is not None:
                text = t('works.stop.coins', lang, coins=res_dict['coins'])
            elif res_dict.get('items') is not None:
                text = t('works.stop.items', lang, items=get_items_names(list(res_dict['items'].values()), lang))
            else: text = ""

            await WorkActivity.end_work(dino.id)
            await dino_notification(dino.id, f'{res.activity_type}_end', results=text)

            if len(last_dinos) == 1:
                stopped_reports.append(f"🦕 <b>{dino.name}</b>:\n{text}" if text else f"🦕 <b>{dino.name}</b>")
            else:
                stopped_reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{text}</blockquote>" if text else f"🦕 <b>{dino.name}</b>")

    if stopped_reports:
        msg_text = "\n\n".join(stopped_reports)
        await bot.send_message(chatid, msg_text, reply_markup=await m(userid, 'extraction_actions_menu', lang))
    else:
        await bot.send_message(chatid, "❌", reply_markup=await m(userid, 'last_menu', lang))


async def build_global_works_send_keyboard(user: User, lang: str):
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('works_global_draft', {})

    label_mine = t('commands_name.extraction_actions.mine', lang)
    label_bank = t('commands_name.extraction_actions.bank', lang)
    label_sawmill = t('commands_name.extraction_actions.sawmill', lang)
    label_coins = t('works.buttons.coins_simple', lang)
    label_items = t('works.buttons.items_simple', lang)

    buttons = []
    active_count = 0

    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_work   = dino_draft.get('work')    # mine / bank / sawmill / None
        sel_reward = dino_draft.get('reward')  # coins / items / None

        if sel_work and sel_reward:
            active_count += 1

        # Row 1 — dino name (reset); primary = not sending
        dino_btn = {"text": f"🦕 {dino.name}", "callback_data": f"wgs_reset {dino.alt_id}"}
        if not (sel_work and sel_reward):
            dino_btn["style"] = "primary"
        buttons.append([dino_btn])

        # Row 2 — work type
        def wbtn(label, wtype):
            b = {"text": label, "callback_data": f"wgs_work {dino.alt_id} {wtype}"}
            if sel_work == wtype:
                b["style"] = "primary"
            return b

        buttons.append([wbtn(label_mine, 'mine'), wbtn(label_bank, 'bank'), wbtn(label_sawmill, 'sawmill')])

        # Row 3 — reward type (coins = success/green, items = primary/blue when selected)
        def rbtn(label, rtype):
            b = {"text": label, "callback_data": f"wgs_reward {dino.alt_id} {rtype}"}
            if sel_reward == rtype:
                b["style"] = "success"
            return b

        buttons.append([rbtn(label_coins, 'coins'), rbtn(label_items, 'items')])

    buttons.append([{
        "text": t('works.send_button', lang, count=active_count),
        "callback_data": "work_global_batch_send"
    }])

    return list_to_inline(buttons)


def _resolve_work_option(work: str, reward: str):
    """Map (work_type, reward) -> (work_type, target_opt) for WorkActivity calls."""
    reward_map = {
        'mine':    {'coins': 'coins', 'items': 'ore'},
        'bank':    {'coins': 'coins', 'items': 'recipes'},
        'sawmill': {'coins': 'coins', 'items': 'wood'},
    }
    target = reward_map.get(work, {}).get(reward)
    return (work, target) if target else None


@main_router.message(
    IsPrivateChat(), StartWith('commands_name.extraction_actions.send'))
async def works_send(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    user.settings['works_global_draft'] = {}
    await user.save()

    inline = await build_global_works_send_keyboard(user, lang)
    await bot.send_message(chatid, t('works.send_title', lang), reply_markup=inline)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('wgs_reset'))
async def wgs_reset_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    dino_alt_id = call.data.split()[1]

    if 'works_global_draft' not in user.settings:
        user.settings['works_global_draft'] = {}
    user.settings['works_global_draft'].pop(dino_alt_id, None)
    await user.save()

    inline = await build_global_works_send_keyboard(user, lang)
    try:
        await call.message.edit_reply_markup(reply_markup=inline)
    except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('wgs_work'))
async def wgs_work_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, work_type = data[1], data[2]

    if 'works_global_draft' not in user.settings:
        user.settings['works_global_draft'] = {}
    dino_draft = user.settings['works_global_draft'].get(dino_alt_id, {})
    dino_draft['work'] = work_type
    # Auto-select coins reward when work type is first picked
    if not dino_draft.get('reward'):
        dino_draft['reward'] = 'coins'
    user.settings['works_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_global_works_send_keyboard(user, lang)
    try:
        await call.message.edit_reply_markup(reply_markup=inline)
    except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('wgs_reward'))
async def wgs_reward_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, reward_type = data[1], data[2]

    if 'works_global_draft' not in user.settings:
        user.settings['works_global_draft'] = {}
    dino_draft = user.settings['works_global_draft'].get(dino_alt_id, {})
    dino_draft['reward'] = reward_type
    user.settings['works_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_global_works_send_keyboard(user, lang)
    try:
        await call.message.edit_reply_markup(reply_markup=inline)
    except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'work_global_batch_send')
async def work_global_batch_send_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    chatid = call.message.chat.id

    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('works_global_draft', {})

    to_send = []
    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        work = dino_draft.get('work')
        reward = dino_draft.get('reward')
        if work and reward:
            resolved = _resolve_work_option(work, reward)
            if resolved:
                to_send.append((dino, resolved[0], resolved[1]))

    if not to_send:
        await call.answer(t('works.none_selected', lang), show_alert=True)
        return

    await call.answer()

    if len(to_send) == 1:
        dino, work_type, target_opt = to_send[0]
        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            full_text = f"🦕 <b>{dino.name}</b>:\n{t('alredy_busy', lang)}"
        else:
            res_text = await start_work_for_dino(dino, userid, work_type, target_opt, lang)
            full_text = f"🦕 <b>{dino.name}</b>:\n{res_text}"
    else:
        reports = []
        for dino, work_type, target_opt in to_send:
            st = await dino.status
            st_val = st.value if hasattr(st, 'value') else str(st)
            if st_val != 'pass':
                reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{t('alredy_busy', lang)}</blockquote>")
                continue

            res_text = await start_work_for_dino(dino, userid, work_type, target_opt, lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{res_text}</blockquote>")

        full_text = "\n\n".join(reports)
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'extraction_actions_menu', lang, True))
    await auto_ads(mes)


async def build_works_send_keyboard(user: User, work_type: str, lang: str):
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('works_draft', {}).get(work_type, {})

    if work_type == 'mine':
        options_map = {
            'coins': t('works.buttons.coins', lang),
            'ore': t('works.buttons.ore', lang)
        }
    elif work_type == 'bank':
        options_map = {
            'coins': t('works.buttons.coins', lang),
            'recipes': t('works.buttons.recipes', lang)
        }
    elif work_type == 'sawmill':
        options_map = {
            'coins': t('works.buttons.coins', lang),
            'wood': t('works.buttons.wood', lang)
        }
    else:
        options_map = {}

    buttons = []
    active_count = 0

    for dino in last_dinos:
        selected_opt = draft.get(dino.alt_id, 'dino')
        if selected_opt in options_map:
            active_count += 1

        dino_btn = {
            "text": f"🦕 {dino.name}",
            "callback_data": f"work_select {dino.alt_id} {work_type} dino"
        }
        if selected_opt == 'dino':
            dino_btn["style"] = "primary"

        buttons.append([dino_btn])

        opt_row = []
        for opt_key, opt_label in options_map.items():
            btn = {
                "text": opt_label,
                "callback_data": f"work_select {dino.alt_id} {work_type} {opt_key}"
            }
            if selected_opt == opt_key:
                btn["style"] = "primary"
            opt_row.append(btn)

        buttons.append(opt_row)

    buttons.append([{
        "text": t('works.send_button', lang, count=active_count),
        "callback_data": f"work_batch_send {work_type}"
    }])

    return list_to_inline(buttons)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('work_select'))
async def work_select_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()

    dino_alt_id = data[1]
    work_type = data[2]
    choice_opt = data[3]

    if 'works_draft' not in user.settings:
        user.settings['works_draft'] = {}
    if work_type not in user.settings['works_draft']:
        user.settings['works_draft'][work_type] = {}

    user.settings['works_draft'][work_type][dino_alt_id] = choice_opt
    await user.save()

    inline = await build_works_send_keyboard(user, work_type, lang)
    try:
        await call.message.edit_reply_markup(reply_markup=inline)
    except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('work_batch_send'))
async def work_batch_send_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    chatid = call.message.chat.id
    data = call.data.split()
    work_type = data[1]

    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('works_draft', {}).get(work_type, {})

    valid_opts = ['coins', 'ore', 'recipes', 'wood']
    to_send = []
    for dino in last_dinos:
        opt = draft.get(dino.alt_id) or draft.get(str(dino.id))
        if opt in valid_opts:
            to_send.append((dino, opt))

    if not to_send:
        await call.answer(t('works.none_selected', lang), show_alert=True)
        return

    await call.answer()

    if len(to_send) == 1:
        dino, opt = to_send[0]
        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            full_text = f"🦕 <b>{dino.name}</b>:\n{t('alredy_busy', lang)}"
        else:
            res_text = await start_work_for_dino(dino, userid, work_type, opt, lang)
            full_text = f"🦕 <b>{dino.name}</b>:\n{res_text}"
    else:
        reports = []
        for dino, opt in to_send:
            st = await dino.status
            st_val = st.value if hasattr(st, 'value') else str(st)
            if st_val != 'pass':
                reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{t('alredy_busy', lang)}</blockquote>")
                continue

            res_text = await start_work_for_dino(dino, userid, work_type, opt, lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{res_text}</blockquote>")

        full_text = "\n\n".join(reports)

    if 'works_draft' in user.settings and work_type in user.settings['works_draft']:
        user.settings['works_draft'][work_type] = {}
        await user.save()

    try:
        await bot.delete_message(userid, call.message.message_id)
    except Exception: pass

    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'extraction_actions_menu', lang, True))
    await auto_ads(mes)


@main_router.message(IsPrivateChat(), Text('commands_name.extraction_actions.mine'))
async def mine(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if 'works_draft' not in user.settings:
        user.settings['works_draft'] = {}
    user.settings['works_draft']['mine'] = {}
    await user.save()

    inline = await build_works_send_keyboard(user, 'mine', lang)
    await bot.send_message(chatid, t('works.choosy_type', lang), reply_markup=inline)

async def end_mine(data, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)

    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'mine', True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    await WorkActivity.start_mine(last_dino._id, userid, data)
    text = t('works.start.mine', lang)
    mes = await bot.send_message(chatid, text,
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)

@main_router.message(IsPrivateChat(), StartWith('commands_name.extraction_actions.bank'))
async def bank(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if 'works_draft' not in user.settings:
        user.settings['works_draft'] = {}
    user.settings['works_draft']['bank'] = {}
    await user.save()

    inline = await build_works_send_keyboard(user, 'bank', lang)
    await bot.send_message(chatid, t('works.choosy_type', lang), reply_markup=inline)

async def end_bank(data, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)

    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'bank', True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    await WorkActivity.start_bank(last_dino._id, userid, data)
    text = t('works.start.bank', lang)
    mes = await bot.send_message(chatid, text,
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)

@main_router.message(IsPrivateChat(), StartWith('commands_name.extraction_actions.sawmill'))
async def sawmill(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if 'works_draft' not in user.settings:
        user.settings['works_draft'] = {}
    user.settings['works_draft']['sawmill'] = {}
    await user.save()

    inline = await build_works_send_keyboard(user, 'sawmill', lang)
    await bot.send_message(chatid, t('works.choosy_type', lang), reply_markup=inline)

async def end_sawmill(data, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)

    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'sawmill', True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    await WorkActivity.start_sawmill(last_dino._id, userid, data)
    text = t('works.start.sawmill', lang)
    mes = await bot.send_message(chatid, text,
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)