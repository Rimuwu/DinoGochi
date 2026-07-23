from bot.models.dinosaur import DinoMood, Dino
from time import time

from aiogram.types import Message
from bson import ObjectId

from bot.exec import main_router, bot
from bot.models.items import Item
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_keyboard, seconds_to_str
from bot.models.dinosaur import Dino
from bot.models.activity import SleepActivity
from bot.modules.inline import inline_menu
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseIntHandler, ChooseOptionHandler
from bot.modules.user.user import User

from bot.filters.translated_text import Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from aiogram import F

async def short_sleep(number: int, transmitted_data: dict):
    """ Отправляем в которкий сон
    """
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    dino_id: ObjectId = transmitted_data['last_dino']
    dino = await Dino().create(dino_id)
    
    if not dino:
        await bot.send_message(chatid, t('alredy_busy', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    from bot.models.enums import DinoStatus
    res_dino_status = await dino.status
    if res_dino_status:
        if res_dino_status != DinoStatus.PASS:
            await bot.send_message(chatid, t('alredy_busy', lang),
            reply_markup = await m(userid, 'last_menu', lang))
            return

    await Item.check_accessory(dino, 'bear', True)
    await SleepActivity.start(dino._id, 'short', number * 60)
    message = await bot.send_message(chatid, 
                t('put_to_bed.sleep', lang),
                reply_markup= await m(userid, 'last_menu', lang, True)
                )
    await auto_ads(message)

async def long_sleep(dino_id: ObjectId, userid: int, lang: str):
    """ Отправляем дино в длинный сон
    """
    dino = await Dino().create(dino_id)

    if not dino:
        await bot.send_message(userid, t('alredy_busy', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    from bot.models.enums import DinoStatus
    res_dino_status = await dino.status
    if res_dino_status:
        if res_dino_status != DinoStatus.PASS:
            await bot.send_message(userid, t('alredy_busy', lang), 
            reply_markup = await m(userid, 'last_menu', lang))
            return

    await SleepActivity.start(dino._id, 'long')
    message = await bot.send_message(userid, 
                t('put_to_bed.sleep', lang),
                reply_markup = await m(userid, 'last_menu', lang, True)
                )
    await auto_ads(message)

async def end_choice(option: str, transmitted_data: dict):
    """Функция обработки выбора варианта (длинный или короткий сон)
    """
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup= await m(userid, 'last_menu', lang))
        return

    if not last_dino:
        await bot.send_message(chatid, t('alredy_busy', lang), reply_markup= await m(userid, 'last_menu', lang))
        return

    if await last_dino.status == 'pass':
        if option == 'short':
            # Если короткий, то спрашиваем сколько дино должен спать
            cancel_button = t('buttons_name.cancel', lang)
            buttons = list_to_keyboard([cancel_button])
            transmitted_data = { 
                    'last_dino': last_dino._id
                }

            await ChooseIntHandler(short_sleep, userid, chatid, lang, min_int=5, max_int=480, transmitted_data=transmitted_data).start()

            await bot.send_message(userid, 
                                t('put_to_bed.choice_time', lang), 
                                reply_markup=buttons)

        elif option == 'long':
            await long_sleep(last_dino._id, userid, lang)

    else:
        await bot.send_message(userid, t('alredy_busy', lang),
            reply_markup=inline_menu('dino_profile', lang, 
            dino_alt_id_markup=last_dino.alt_id))

from aiogram.types import CallbackQuery, Message
from bot.modules.data_format import list_to_inline, list_to_keyboard, seconds_to_str

async def build_sleep_send_keyboard(user: User, lang: str, page: int = 0):
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('sleep_global_draft', {})

    sl_buttons = get_data('put_to_bed.buttons', lang)
    long_label = sl_buttons[0][0] if sl_buttons and len(sl_buttons[0]) > 0 else "🛌 Длинный"
    short_label = sl_buttons[0][1] if sl_buttons and len(sl_buttons[0]) > 1 else "🧸 Короткий"

    active_count = 0
    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_type = dino_draft.get('type')
        sel_minutes = dino_draft.get('minutes')
        if sel_type == 'long' or (sel_type == 'short' and sel_minutes):
            active_count += 1

    per_page = 1
    total_pages = max(1, (len(last_dinos) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    paged_dinos = last_dinos[page * per_page : (page + 1) * per_page]

    buttons = []

    for dino in paged_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_type = dino_draft.get('type')        # 'long' / 'short' / None
        sel_minutes = dino_draft.get('minutes')  # int / None

        has_bear = await Item.check_accessory(dino, 'bear')

        dino_btn = {"text": f"🦕 {dino.name}", "callback_data": f"sgs_reset {dino.alt_id} {page}"}
        if not (sel_type == 'long' or (sel_type == 'short' and sel_minutes)):
            dino_btn["style"] = "primary"
        buttons.append([dino_btn])

        type_row = []
        btn_long = {"text": long_label, "callback_data": f"sgs_type {dino.alt_id} long {page}"}
        if sel_type == 'long':
            btn_long["style"] = "primary"
        type_row.append(btn_long)

        if has_bear:
            btn_short = {"text": short_label, "callback_data": f"sgs_type {dino.alt_id} short {page}"}
            if sel_type == 'short':
                btn_short["style"] = "primary"
            type_row.append(btn_short)

        buttons.append(type_row)

        if has_bear and sel_type == 'short':
            min_row = []
            for mins in [15, 30, 60, 120, 240]:
                m_btn = {"text": f"{mins}м", "callback_data": f"sgs_min {dino.alt_id} {mins} {page}"}
                if sel_minutes == mins:
                    m_btn["style"] = "primary"
                min_row.append(m_btn)
            buttons.append(min_row)

    buttons.append([{
        "text": t('put_to_bed.send_button', lang, count=active_count),
        "callback_data": "sleep_global_batch_send"
    }])

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"text": "⬅️", "callback_data": f"sgs_page {prev_p}"},
            {"text": f"{page + 1} / {total_pages}", "callback_data": "None"},
            {"text": "➡️", "callback_data": f"sgs_page {next_p}"}
        ]
        buttons.append(nav_row)

    return list_to_inline(buttons)


async def get_sleep_send_text(user: User, lang: str, page: int = 0) -> str:
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
        text += t('put_to_bed.choice', lang) + "\n\n"
    
    return text.strip()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('sgs_reset'))
async def sgs_reset_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id = data[1]
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    if 'sleep_global_draft' in user.settings and dino_alt_id in user.settings['sleep_global_draft']:
        del user.settings['sleep_global_draft'][dino_alt_id]
        await user.save()

    inline = await build_sleep_send_keyboard(user, lang, page)
    text = await get_sleep_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('sgs_type'))
async def sgs_type_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, stype = data[1], data[2]
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    if 'sleep_global_draft' not in user.settings:
        user.settings['sleep_global_draft'] = {}
    dino_draft = user.settings['sleep_global_draft'].get(dino_alt_id, {})
    dino_draft['type'] = stype
    if stype == 'short' and not dino_draft.get('minutes'):
        dino_draft['minutes'] = 30
    user.settings['sleep_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_sleep_send_keyboard(user, lang, page)
    text = await get_sleep_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('sgs_min'))
async def sgs_min_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, mins_str = data[1], data[2]
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    if 'sleep_global_draft' not in user.settings:
        user.settings['sleep_global_draft'] = {}
    dino_draft = user.settings['sleep_global_draft'].get(dino_alt_id, {})
    dino_draft['type'] = 'short'
    dino_draft['minutes'] = int(mins_str)
    user.settings['sleep_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_sleep_send_keyboard(user, lang, page)
    text = await get_sleep_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('sgs_page'))
async def sgs_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    page = int(data[1])

    inline = await build_sleep_send_keyboard(user, lang, page)
    text = await get_sleep_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'sleep_global_batch_send')
async def sleep_global_batch_send_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    chatid = call.message.chat.id

    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('sleep_global_draft', {})

    to_send = []
    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        stype = dino_draft.get('type')
        smins = dino_draft.get('minutes', 30)
        if stype == 'long' or (stype == 'short' and smins):
            to_send.append((dino, stype, smins))

    if not to_send:
        await call.answer(t('works.none_selected', lang), show_alert=True)
        return

    await call.answer()

    reports = []
    for dino, stype, smins in to_send:
        if dino.stats['energy'] >= 90:
            msg_txt = t('put_to_bed.dont_want', lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n{msg_txt}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{msg_txt}</blockquote>")
            continue

        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            msg_txt = t('alredy_busy', lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n{msg_txt}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{msg_txt}</blockquote>")
            continue

        if stype == 'long':
            await SleepActivity.start(dino._id, 'long')
            res_text = t('put_to_bed.sleep', lang)
        else:
            await Item.check_accessory(dino, 'bear', True)
            await SleepActivity.start(dino._id, 'short', smins * 60)
            res_text = t('put_to_bed.sleep', lang)

        reports.append(f"🦕 <b>{dino.name}</b>:\n{res_text}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{res_text}</blockquote>")

    user.settings['sleep_global_draft'] = {}
    await user.save()

    try:
        await bot.delete_message(userid, call.message.message_id)
    except Exception: pass

    full_text = "\n\n".join(reports)
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'live_actions_menu', lang, True))
    await auto_ads(mes)


@main_router.message(IsPrivateChat(), Text('commands_name.actions.put_to_bed'), DinoPassStatus())
async def put_to_bed(message: Message):
    """Уложить спать динозавров
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User().create(userid)
    last_dinos = await user.get_last_dinos()

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if len(last_dinos) == 1:
        last_dino = last_dinos[0]
        if await Item.check_accessory(last_dino, 'bear'):
            sl_buttons = get_data('put_to_bed.buttons', lang)
            options = {
                sl_buttons[0][0]: 'long',
                sl_buttons[0][1]: 'short'
            }
            buttons = list_to_keyboard(sl_buttons)
            await ChooseOptionHandler(
                end_choice, userid, chatid, lang, options,
                transmitted_data={'last_dino': last_dino._id}
            ).start()
            await bot.send_message(chatid, t('put_to_bed.choice', lang), reply_markup=buttons)
        else:
            await long_sleep(last_dino._id, userid, lang)
    else:
        user.settings['sleep_global_draft'] = {}
        await user.save()

        from bot.modules.markup import cancel_markup
        inline = await build_sleep_send_keyboard(user, lang, 0)
        text = await get_sleep_send_text(user, lang, 0)
        await bot.send_message(chatid, t('commands_name.actions.put_to_bed', lang), reply_markup=cancel_markup(lang))
        await bot.send_message(chatid, text, reply_markup=inline)

async def get_sleep_progress_page(userid: int, lang: str, page: int | None = None):
    user = await User().create(userid)
    dinos = await user.get_dinos()

    sleep_dinos = []
    for dino in dinos:
        data = await SleepActivity.find_one(SleepActivity.dino.id == dino.id)
        if data:
            sleep_dinos.append((dino, data))

    if not sleep_dinos:
        return None, None

    total_pages = len(sleep_dinos)

    if page is None:
        last_dino = await user.get_last_dino()
        page = 0
        if last_dino:
            for idx, (dino, _) in enumerate(sleep_dinos):
                if dino.id == last_dino.id:
                    page = idx
                    break
    else:
        page = max(0, min(page, total_pages - 1))

    dino, data = sleep_dinos[page]

    elapsed_seconds = max(0, int(time()) - data.start_time)
    time_str = seconds_to_str(elapsed_seconds, lang)

    text = f"🦕 <b>{dino.name}</b> ({page + 1}/{total_pages})\n\n"
    text += f"🛌 | {t('awaken.sleeping', lang, default='Динозавр спит')} ({time_str})"

    buttons = []
    awaken_button = t('buttons_name.awaken', lang, default='⏰ Пробудить')
    buttons.append([{awaken_button: f'awaken_dino {dino.alt_id} {page}'}])

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"⬅️": f"sleep_prog_page {prev_p}"},
            {f"{page + 1} / {total_pages}": "None"},
            {"➡️": f"sleep_prog_page {next_p}"}
        ]
        buttons.append(nav_row)

    markup = list_to_inline(buttons)
    return text, markup


@main_router.message(
    IsPrivateChat(), 
    Text('commands_name.actions.awaken')
)
async def awaken(message: Message):
    """Пробуждение динозавра
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    text, markup = await get_sleep_progress_page(userid, lang)
    if not text:
        user = await User().create(userid)
        last_dino = await user.get_last_dino()
        if last_dino and await last_dino.status == 'sleep':
            from bot.models.enums import DinoStatus
            await last_dino.set_status(DinoStatus.PASS)
            await bot.send_message(chatid, t('awaken.not_sleep', lang), reply_markup=await m(userid, 'last_menu', lang, True))
        else:
            await bot.send_message(chatid, t('awaken.no_sleepers', lang, default='😴 Ни один из ваших динозавров не спит!'), reply_markup=await m(userid, 'last_menu', lang, True))
        return

    mes = await bot.send_message(chatid, text, reply_markup=markup)
    await auto_ads(mes)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('sleep_prog_page'))
async def sleep_prog_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    data = call.data.split()
    page = int(data[1])

    text, markup = await get_sleep_progress_page(userid, lang, page)
    if text:
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('awaken_dino'))
async def awaken_dino_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    chatid = call.message.chat.id
    data = call.data.split()
    dino_alt_id = data[1]
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    dino = await Dino.find_one(Dino.alt_id == dino_alt_id)
    if dino:
        if await dino.status == 'sleep':
            sleeper = await SleepActivity.find_one(SleepActivity.dino.id == dino.id)
            if sleeper:
                sleep_time = int(time()) - sleeper.start_time
                if sleeper.sleep_type == 'long':
                    healthy_sleep = 8 * 3600
                    if sleep_time >= healthy_sleep or dino.stats.get('energy', 0) == 100:
                        await SleepActivity.end(dino.id, sleep_time)
                        await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.good_sleep', lang, default='☀️ Динозавр выспался и полон сил!'))
                    else:
                        await DinoMood.add(dino.id, 'bad_sleep', -1, 10800)
                        await SleepActivity.end(dino.id, sleep_time, False)
                        await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.down_mood', lang, time_end=seconds_to_str(sleep_time, lang)))
                elif sleeper.sleep_type == 'short':
                    healthy_sleep = 1 * 3600
                    if sleep_time >= healthy_sleep or dino.stats.get('energy', 0) == 100:
                        await SleepActivity.end(dino.id, sleep_time)
                        await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.good_sleep', lang, default='☀️ Динозавр проснулся бодрым!'))
                    else:
                        await DinoMood.add(dino.id, 'bad_sleep', -1, 7200)
                        await SleepActivity.end(dino.id, sleep_time, False)
                        await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.down_mood', lang, time_end=seconds_to_str(sleep_time, lang)))
                else:
                    await SleepActivity.end(dino.id, sleep_time)
                    await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.good_sleep', lang, default='☀️ Динозавр проснулся!'))
            else:
                from bot.models.enums import DinoStatus
                await dino.set_status(DinoStatus.PASS)
                await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.not_sleep', lang))
        else:
            await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('awaken.not_sleep', lang))

    next_text, next_markup = await get_sleep_progress_page(userid, lang, page)
    if next_text:
        try:
            await call.message.edit_text(next_text, reply_markup=next_markup)
        except Exception: pass
    else:
        try:
            await bot.delete_message(chatid, call.message.message_id)
        except Exception: pass
        await bot.send_message(chatid, t('back_text.actions_menu', lang), reply_markup=await m(userid, 'last_menu', lang))

    await call.answer()