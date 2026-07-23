from bot.models.dinosaur import DinoMood, Dino
from bson import ObjectId
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.models.items import Item
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_inline, list_to_keyboard, seconds_to_str
from bot.models.dinosaur import Dino
from bot.models.activity import CollectingActivity
from bot.modules.images import dino_collecting
from bot.modules.items.item import counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.quests import quest_process
from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import IntStepData, OptionStepData, StepMessage

from bot.modules.user.user import User, count_inventory_items, max_eat, premium
from aiogram.types import CallbackQuery, Message, InputMediaPhoto

from bot.filters.translated_text import StartWith, Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F

async def collecting_adapter(return_data, transmitted_data):
    dino_id: ObjectId = transmitted_data['dino']
    count: int = return_data['count']
    option = return_data['option']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    eat_count = await count_inventory_items(userid, ['eat'])
    if eat_count + count > await max_eat(userid):

        text = t(f'collecting.max_count', lang,
                eat_count=eat_count,
                add_count=count,
                max_c=await max_eat(userid)
                )
        await bot.send_message(chatid, text, reply_markup= await m(
            userid, 'last_menu', lang))
    else:
        from bot.models.enums import DinoStatus
        res_dino_status = await dino.status
        if res_dino_status:
            if res_dino_status != DinoStatus.PASS:
                await bot.send_message(chatid, t('alredy_busy', lang), reply_markup= await m(userid, 'last_menu', lang))
                return

            await dino.collecting(userid, option, count)
            await Item.check_accessory(dino, 'basket', True)
            percent, _ = await dino.memory_percent(
                'action', f'collecting.{option}', True)
            await DinoMood.repeat_activity(dino._id, percent)

            image = await dino_collecting(dino.data_id, option)
            text = t(f'collecting.result.{option}', lang,
                    dino_name=dino.name, count=count)
            stop_button = t(f'collecting.stop_button.{option}', lang)
            markup = list_to_inline([
                {stop_button: f'collecting stop {dino.alt_id}'}])

            await bot.send_photo(chatid, image, caption=text, reply_markup=markup)
            message = await bot.send_message(chatid, t('back_text.actions_menu', lang),
                                        reply_markup = await m(userid, 'last_menu', lang)
                                        )

            await auto_ads(message)

            from bot.modules.tutorial import advance_tutorial_if_step
            await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="collecting_hint")

async def build_collecting_send_keyboard(user: User, lang: str, page: int = 0):
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('collecting_global_draft', {})

    data_options = get_data('collecting.buttons', lang)
    # data_options: {'collecting': '🌿 Поля', 'hunt': '🍖 Леса', 'fishing': '🍤 Озёра', 'all': '🥗 Всё вместе'}

    is_prem = await user.premium
    base_max = GAME_SETTINGS['premium_max_collecting'] if is_prem else GAME_SETTINGS['max_collecting']

    active_count = 0
    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_opt = dino_draft.get('option')
        sel_cnt = dino_draft.get('count')
        if sel_opt and sel_cnt:
            active_count += 1

    per_page = 1
    total_pages = max(1, (len(last_dinos) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    paged_dinos = last_dinos[page * per_page : (page + 1) * per_page]

    buttons = []

    for dino in paged_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_opt = dino_draft.get('option')  # 'collecting'/'hunt'/'fishing'/'all'/None
        sel_cnt = dino_draft.get('count')   # int / None

        have_basket = await Item.check_accessory(dino, 'basket')
        dino_max = base_max + (20 if have_basket else 0)

        dino_btn = {"text": f"🦕 {dino.name}", "callback_data": f"cgs_reset {dino.alt_id} {page}"}
        if not (sel_opt and sel_cnt):
            dino_btn["style"] = "primary"
        buttons.append([dino_btn])

        loc_row = []
        for opt_key, opt_label in data_options.items():
            btn = {"text": opt_label, "callback_data": f"cgs_opt {dino.alt_id} {opt_key} {page}"}
            if sel_opt == opt_key:
                btn["style"] = "primary"
            loc_row.append(btn)
        buttons.append(loc_row)

        if sel_opt:
            cnt_row = []
            possible_counts = [10, 20, 30, 50, 70, dino_max]
            possible_counts = sorted(list(set([c for c in possible_counts if c <= dino_max])))
            for cnt in possible_counts:
                label = f"{cnt}" if cnt < dino_max else f"max ({cnt})"
                c_btn = {"text": label, "callback_data": f"cgs_cnt {dino.alt_id} {cnt} {page}"}
                if sel_cnt == cnt:
                    c_btn["style"] = "primary"
                cnt_row.append(c_btn)
            buttons.append(cnt_row)

    buttons.append([{
        "text": t('collecting.send_button', lang, count=active_count),
        "callback_data": "collecting_global_batch_send"
    }])

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"text": "⬅️", "callback_data": f"cgs_page {prev_p}"},
            {"text": f"{page + 1} / {total_pages}", "callback_data": "None"},
            {"text": "➡️", "callback_data": f"cgs_page {next_p}"}
        ]
        buttons.append(nav_row)

    return list_to_inline(buttons)


async def get_collecting_send_text(user: User, lang: str, page: int = 0) -> str:
    last_dinos = await user.get_last_dinos()
    if not last_dinos:
        return t('css.no_dino', lang)
    
    per_page = 1
    total_pages = max(1, (len(last_dinos) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    paged_dinos = last_dinos[page * per_page : (page + 1) * per_page]

    text = ""
    for dino in paged_dinos:
        text += f"🦕 <b>{dino.name}</b> ({page + 1}/{total_pages})\n"
        text += t('collecting.way', lang) + "\n\n"
    
    return text.strip()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('cgs_reset'))
async def cgs_reset_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id = data[1]
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    if 'collecting_global_draft' in user.settings and dino_alt_id in user.settings['collecting_global_draft']:
        del user.settings['collecting_global_draft'][dino_alt_id]
        await user.save()

    inline = await build_collecting_send_keyboard(user, lang, page)
    text = await get_collecting_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('cgs_opt'))
async def cgs_opt_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, opt = data[1], data[2]
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    if 'collecting_global_draft' not in user.settings:
        user.settings['collecting_global_draft'] = {}
    dino_draft = user.settings['collecting_global_draft'].get(dino_alt_id, {})
    dino_draft['option'] = opt

    dino = await Dino.find_one(Dino.alt_id == dino_alt_id)
    if dino and not dino_draft.get('count'):
        is_prem = await user.premium
        base_max = GAME_SETTINGS['premium_max_collecting'] if is_prem else GAME_SETTINGS['max_collecting']
        have_basket = await Item.check_accessory(dino, 'basket')
        dino_draft['count'] = base_max + (20 if have_basket else 0)

    user.settings['collecting_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_collecting_send_keyboard(user, lang, page)
    text = await get_collecting_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('cgs_cnt'))
async def cgs_cnt_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, cnt_str = data[1], data[2]
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    if 'collecting_global_draft' not in user.settings:
        user.settings['collecting_global_draft'] = {}
    dino_draft = user.settings['collecting_global_draft'].get(dino_alt_id, {})
    dino_draft['count'] = int(cnt_str)
    if not dino_draft.get('option'):
        dino_draft['option'] = 'collecting'
    user.settings['collecting_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_collecting_send_keyboard(user, lang, page)
    text = await get_collecting_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('cgs_page'))
async def cgs_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    page = int(data[1])

    inline = await build_collecting_send_keyboard(user, lang, page)
    text = await get_collecting_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'collecting_global_batch_send')
async def collecting_global_batch_send_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    chatid = call.message.chat.id

    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('collecting_global_draft', {})

    to_send = []
    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        opt = dino_draft.get('option')
        cnt = dino_draft.get('count')
        if opt and cnt:
            to_send.append((dino, opt, cnt))

    if not to_send:
        await call.answer(t('works.none_selected', lang), show_alert=True)
        return

    await call.answer()

    reports = []
    for dino, option, count in to_send:
        eat_count = await count_inventory_items(userid, ['eat'])
        if eat_count + count > await max_eat(userid):
            msg_txt = t('collecting.max_count', lang, eat_count=eat_count, add_count=count, max_c=await max_eat(userid))
            reports.append(f"🦕 <b>{dino.name}</b>:\n{msg_txt}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{msg_txt}</blockquote>")
            continue

        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            msg_txt = t('alredy_busy', lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n{msg_txt}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{msg_txt}</blockquote>")
            continue

        await dino.collecting(userid, option, count)
        await Item.check_accessory(dino, 'basket', True)
        percent, _ = await dino.memory_percent('action', f'collecting.{option}', True)
        await DinoMood.repeat_activity(dino._id, percent)

        res_text = t(f'collecting.result.{option}', lang, dino_name=dino.name, count=count)
        reports.append(f"🦕 <b>{dino.name}</b>:\n{res_text}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{res_text}</blockquote>")

    user.settings['collecting_global_draft'] = {}
    await user.save()

    try:
        await bot.delete_message(userid, call.message.message_id)
    except Exception: pass

    full_text = "\n\n".join(reports)
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'live_actions_menu', lang, True))
    await auto_ads(mes)


@main_router.message(
    IsPrivateChat(), 
    StartWith('commands_name.actions.collecting'),
    DinoPassStatus()
)
async def collecting_button(message: Message):
    if message.from_user:
        userid = message.from_user.id
        chatid = message.chat.id

        user = await User().create(userid)
        lang = await user.lang
        last_dinos = await user.get_last_dinos()

        if not last_dinos:
            await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
            return

        if len(last_dinos) == 1:
            last_dino = last_dinos[0]
            is_prem = await premium(userid)
            max_count = GAME_SETTINGS['premium_max_collecting'] if is_prem else GAME_SETTINGS['max_collecting']

            data_options = get_data('collecting.buttons', lang)
            options = {}
            for key, value in data_options.items():
                options[value] = key

            markup = list_to_keyboard([list(data_options.values()), 
                                    [t('buttons_name.cancel', lang)]], 2)

            steps = [
                OptionStepData('option', 
                            StepMessage('collecting.way', markup, True),
                            options=options
                            ),
                IntStepData('count', 
                            StepMessage('collecting.wait_count',
                                count_markup(max_count, lang), True),
                            max_int=max_count,
                            )
            ]
            await ChooseStepHandler(collecting_adapter, userid, chatid,
                                    lang, steps, 
                                    transmitted_data={'dino': last_dino._id}
                                ).start()
            from bot.modules.tutorial import advance_tutorial_if_step
            await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="collecting")
        else:
            user.settings['collecting_global_draft'] = {}
            await user.save()

            from bot.modules.markup import cancel_markup
            inline = await build_collecting_send_keyboard(user, lang, 0)
            text = await get_collecting_send_text(user, lang, 0)
            await bot.send_message(chatid, t('commands_name.actions.collecting', lang), reply_markup=cancel_markup(lang))
            await bot.send_message(chatid, text, reply_markup=inline)

async def get_collecting_progress_page(userid: int, lang: str, page: int | None = None):
    user = await User().create(userid)
    dinos = await user.get_dinos()

    col_dinos = []
    for dino in dinos:
        data = await CollectingActivity.find_one(CollectingActivity.dino.id == dino.id)
        if data:
            col_dinos.append((dino, data))

    if not col_dinos:
        return None, None, None

    total_pages = len(col_dinos)

    if page is None:
        last_dino = await user.get_last_dino()
        page = 0
        if last_dino:
            for idx, (dino, _) in enumerate(col_dinos):
                if dino.id == last_dino.id:
                    page = idx
                    break
    else:
        page = max(0, min(page, total_pages - 1))

    dino, data = col_dinos[page]

    import time
    current_time = int(time.time())
    now_count = 0
    collected_items = {}
    for tick in data.pregenerated_ticks:
        if tick["trigger_time"] <= current_time:
            now_count = tick["count"]
            for item_id, count in tick.get("items", {}).items():
                collected_items[item_id] = collected_items.get(item_id, 0) + count

    image = await dino_collecting(dino.data_id, data.collecting_type)
    stop_button = t(f'collecting.stop_button.{data.collecting_type}', lang)

    base_text = t(
        f'collecting.progress.{data.collecting_type}', lang,
        now=now_count, max_count=data.max_count
    )

    elapsed_seconds = max(0, current_time - data.start_time)
    time_str = seconds_to_str(elapsed_seconds, lang)

    items_list = []
    for item_id, count in collected_items.items():
        items_list.extend([item_id] * count)

    if items_list:
        items_str = counts_items(items_list, lang, separator=', ')
    else:
        items_str = t('collecting.empty_items', lang)

    time_line = t('collecting.progress_time', lang, time=time_str)
    items_line = t('collecting.progress_items', lang, items=items_str)

    if total_pages > 1:
        text = f"🦕 <b>{dino.name}</b> ({page + 1}/{total_pages})\n\n{base_text}\n\n{time_line}\n{items_line}"
    else:
        text = f"🦕 <b>{dino.name}</b>\n\n{base_text}\n\n{time_line}\n{items_line}"

    buttons = []
    buttons.append([{stop_button: f'collecting stop {dino.alt_id} {page}'}])

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"text": "⬅️", "callback_data": f"collecting_prog_page {prev_p}"},
            {"text": f"{page + 1} / {total_pages}", "callback_data": "None"},
            {"text": "➡️", "callback_data": f"collecting_prog_page {next_p}"}
        ]
        buttons.append(nav_row)

    inline = list_to_inline(buttons)
    return image, text, inline


@main_router.message(IsPrivateChat(), Text('commands_name.actions.progress'))
async def collecting_progress(message: Message):
    if message.from_user:
        userid = message.from_user.id
        chatid = message.chat.id

        user = await User().create(userid)
        lang = await user.lang

        image, text, inline = await get_collecting_progress_page(userid, lang, None)
        if image:
            await bot.send_photo(chatid, image, caption=text, reply_markup=inline)
        else:
            await bot.send_message(chatid, '❌', reply_markup=await m(userid, 'last_menu', lang))


@main_router.callback_query(IsPrivateChat(), F.data.startswith('collecting_prog_page'))
async def collecting_prog_page_calb(call: CallbackQuery):
    if call.data:
        userid = call.from_user.id
        lang = await get_lang(userid)
        page = int(call.data.split()[1])

        image, text, inline = await get_collecting_progress_page(userid, lang, page)
        if image:
            try:
                await call.message.edit_media(
                    media=InputMediaPhoto(media=image, caption=text),
                    reply_markup=inline
                )
            except Exception:
                pass
        await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('collecting stop'), IsAuthorizedUser())
async def collecting_callback(callback: CallbackQuery):
    if callback.data:
        split_data = callback.data.split()
        dino_data = split_data[2]
        action = split_data[1]
        page = int(split_data[3]) if len(split_data) > 3 else 0

        lang = await get_lang(callback.from_user.id)

        dino = await Dino().create(dino_data)
        if not dino:
            await bot.send_message(callback.from_user.id, t('css.no_dino', lang), reply_markup=await m(callback.from_user.id, 'last_menu', lang))
            return

        data = await CollectingActivity.find_one(CollectingActivity.dino.id == dino.id)
        if data and dino:
            items_list = []
            for key, count in data.items.items():
                items_list += [key] * count

            items_names = counts_items(items_list, lang)

            if action == 'stop':
                await CollectingActivity.end(dino.id, 
                                    data.items, data.userid, 
                                    items_names)
                await callback.answer()
                if callback.message:
                    image, text, inline = await get_collecting_progress_page(callback.from_user.id, lang, page)
                    if image:
                        try:
                            await callback.message.edit_media(
                                media=InputMediaPhoto(media=image, caption=text),
                                reply_markup=inline
                            )
                        except Exception:
                            pass
                    else:
                        try:
                            await bot.delete_message(callback.message.chat.id, callback.message.message_id)
                        except Exception:
                            pass