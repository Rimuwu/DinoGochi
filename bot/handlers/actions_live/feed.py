from bot.models.items import Item
from bson import ObjectId
from bot.exec import main_router, bot
from bot.filters.private import IsPrivateChat
from bot.models.dinosaur import Dino
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_name
from bot.modules.items.item_tools import use_item
from bot.modules.localization import get_lang, t
from bot.modules.markup import feed_count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.data_format import list_to_inline
from bot.modules.states_fabric.state_handlers import ChooseInventoryHandler, ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import DataType, IntStepData, MultiInventoryStepData, StepMessage
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup

from bot.filters.translated_text import Text
from aiogram import F
from aiogram.filters import Command

async def adapter_function(return_dict, transmitted_data):
    count = return_dict['count']
    item = transmitted_data['item']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    dino_id = transmitted_data['dino']
    lang = transmitted_data['lang']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    send_status, return_text = await use_item(
        userid, chatid, lang, item, count, dino)

    if send_status:
        await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n<blockquote>{return_text}</blockquote>", 
                               reply_markup= await m(userid, 'last_menu', lang))

        from bot.modules.tutorial import advance_tutorial_if_step
        await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="feed_wait")


async def execute_feed_all_at_once(userid: int, chatid: int, lang: str, user: User, dinos: list[Dino], chosen_items: list[dict]):
    reports = []
    for dino in dinos:
        dino_reports = []
        for item in chosen_items:
            qty = item.get('count', 1)
            send_status, return_text = await use_item(userid, chatid, lang, item, qty, dino)
            if send_status and return_text:
                dino_reports.append(return_text)
        if dino_reports:
            block_text = "\n".join(dino_reports)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{block_text}</blockquote>")

    user.settings['feed_draft'] = {}
    await user.save()

    full_text = "\n\n".join(reports) if reports else t('css.no_feed_effect', lang, default='Продукты успешно использованы!')
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'last_menu', lang))
    await auto_ads(mes)

    from bot.modules.tutorial import advance_tutorial_if_step
    await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="feed_wait")


async def multi_feed_start_adapter(return_data: dict, trans_data: dict):
    userid = trans_data['userid']
    chatid = trans_data['chatid']
    lang = trans_data['lang']
    chosen_items = return_data.get('food_items', [])

    if not chosen_items:
        await bot.send_message(chatid, t('feed.no_items', lang, default='❌ Продукты не выбраны!'), reply_markup=await m(userid, 'last_menu', lang))
        return

    user = await User().create(userid)
    eligible_ids = trans_data.get('eligible_dino_ids', [])
    dinos = []
    for alt_id in eligible_ids:
        d = await Dino.find_one(Dino.alt_id == alt_id)
        if d: dinos.append(d)

    if not dinos:
        dinos = await user.get_last_dinos()

    user.settings['feed_draft'] = {
        'items': chosen_items,
        'eligible_ids': [d.alt_id for d in dinos]
    }
    await user.save()

    target_msg_id = trans_data.get('edit_message_id') or trans_data.get('main_message', 0)

    if len(dinos) == 1:
        if target_msg_id:
            try:
                await bot.delete_message(chatid, target_msg_id)
            except Exception: pass
        await execute_feed_all_at_once(userid, chatid, lang, user, dinos, chosen_items)
    else:
        total_items = sum(i.get('count', 1) for i in chosen_items)
        diff_items = len(chosen_items)

        text = t('feed.mode_title', lang)
        text += f"\n\n📦 <b>{t('multinv.total_selected', lang, default='Выбрано продуктов')}:</b> {total_items} ({diff_items})"

        btn_all = t('feed.mode_all', lang, default='🍴 Всем сразу')
        btn_dist = t('feed.mode_dist', lang, default='🍱 Распределить')
        btn_cancel = t('buttons_name.cancel', lang, default='❌ Отмена')

        buttons = [
            [
                {btn_all: "feed_mode all"},
                {btn_dist: "feed_mode dist"}
            ],
            [{btn_cancel: "feed_mode cancel"}]
        ]
        markup = list_to_inline(buttons)

        if target_msg_id:
            try:
                from bot.modules.images_save import edit_SmartPhoto
                await edit_SmartPhoto(chatid, target_msg_id, "images/remain/mulinv.png", text, 'HTML', reply_markup=markup)
            except Exception:
                await bot.send_message(chatid, text, reply_markup=markup)
        else:
            await bot.send_message(chatid, text, reply_markup=markup)


async def edit_feed_message(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    try:
        await call.message.edit_caption(caption=text, reply_markup=markup, parse_mode='HTML')
    except Exception:
        try:
            from bot.modules.images_save import edit_SmartPhoto
            await edit_SmartPhoto(call.message.chat.id, call.message.message_id, "images/remain/mulinv.png", text, 'HTML', reply_markup=markup)
        except Exception:
            await bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')


async def build_feed_dist_card(user: User, lang: str, page: int = 0, detail_idx: int | None = None):
    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])
    eligible_ids = feed_draft.get('eligible_ids', [])
    dist_draft = user.settings.get('feed_dist_draft', {})

    dinos = []
    for alt_id in eligible_ids:
        d = await Dino.find_one(Dino.alt_id == alt_id)
        if d: dinos.append(d)

    if not dinos or not chosen_items:
        return None, None

    total_pages = len(dinos)
    page = max(0, min(page, total_pages - 1))
    dino = dinos[page]
    dino_dist = dist_draft.get(dino.alt_id, {})

    item_unassigned = []
    for idx, item in enumerate(chosen_items):
        total_assigned = sum(
            dist_draft.get(d_alt, {}).get(str(idx), 0)
            for d_alt in dist_draft
        )
        remaining = max(0, item.get('count', 1) - total_assigned)
        item_unassigned.append(remaining)

    total_assigned_all = sum(
        sum(dist_draft.get(d_alt, {}).values())
        for d_alt in dist_draft
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    if detail_idx is not None and 0 <= detail_idx < len(chosen_items):
        # --- DETAIL ADJUSTMENT VIEW FOR SINGLE ITEM ---
        item = chosen_items[detail_idx]
        item_id = item['item_id']
        item_name_html = get_name(item_id, lang, item.get('abilities', {}), html=True)
        item_name_btn = get_name(item_id, lang, item.get('abilities', {}), with_emoji=True, custom_emoji=False, html=False)
        assigned = dino_dist.get(str(detail_idx), 0)
        remaining = item_unassigned[detail_idx]
        total_qty = item.get('count', 1)

        text = f"🍱 <b>Распределение пищи</b> ({page + 1}/{total_pages})\n"
        text += f"🦕 <b>{dino.name}</b>\n"
        text += f"🍗 Сытость: {dino.stats.get('eat', 0)}/100 | ⚡ Энергия: {dino.stats.get('energy', 0)}/100\n\n"
        text += f"📦 <b>Настройка продукта:</b>\n"
        text += f"• {item_name_html}: <b>{assigned} шт.</b> — Свободно {remaining} / {total_qty}\n\n"
        text += "Используйте кнопки ниже для изменения количества:"

        label = f"{item_name_btn}: {assigned}"

        # Row 1: -100 -10 -1
        builder.button(text="-100", callback_data=f"feed_dist_adj {dino.alt_id} {detail_idx} -100 {page}")
        builder.button(text="-10", callback_data=f"feed_dist_adj {dino.alt_id} {detail_idx} -10 {page}")
        builder.button(text="-1", callback_data=f"feed_dist_adj {dino.alt_id} {detail_idx} -1 {page}")

        # Row 2: Label
        builder.button(text=label, callback_data="feed_dist_noop")

        # Row 3: +1 +10 +100
        builder.button(text="+1", callback_data=f"feed_dist_adj {dino.alt_id} {detail_idx} 1 {page}")
        builder.button(text="+10", callback_data=f"feed_dist_adj {dino.alt_id} {detail_idx} 10 {page}")
        builder.button(text="+100", callback_data=f"feed_dist_adj {dino.alt_id} {detail_idx} 100 {page}")

        # Row 4: Back button
        btn_back = t('buttons_name.back', lang, default='↪️ Назад')
        builder.button(text=btn_back, callback_data=f"feed_dist_back {dino.alt_id} {page}")

        builder.adjust(3, 1, 3, 1)
    else:
        # --- OVERVIEW VIEW OF ALL ITEMS ---
        text = f"🍱 <b>Распределение пищи</b> ({page + 1}/{total_pages})\n"
        text += f"🦕 <b>{dino.name}</b>\n"
        text += f"🍗 Сытость: {dino.stats.get('eat', 0)}/100 | ⚡ Энергия: {dino.stats.get('energy', 0)}/100\n\n"
        text += "📦 <b>Выбранные продукты:</b>\n"

        for idx, item in enumerate(chosen_items):
            item_id = item['item_id']
            item_name_html = get_name(item_id, lang, item.get('abilities', {}), html=True)
            assigned = dino_dist.get(str(idx), 0)
            remaining = item_unassigned[idx]
            total_qty = item.get('count', 1)

            text += f"• {item_name_html}: <b>{assigned} шт.</b> — Свободно {remaining} / {total_qty}\n"

        text += "\nВыберите продукт для изменения количества:"

        for idx, item in enumerate(chosen_items):
            item_id = item['item_id']
            item_name_btn = get_name(item_id, lang, item.get('abilities', {}), with_emoji=True, custom_emoji=False, html=False)
            assigned = dino_dist.get(str(idx), 0)

            label = f"{item_name_btn}: {assigned}"
            builder.button(text=label, callback_data=f"feed_dist_select {dino.alt_id} {idx} {page}")

        confirm_btn_text = t('feed.confirm_btn', lang, default='Покормить')
        confirm_label = f"🚀 {confirm_btn_text} ({total_assigned_all})"
        builder.button(text=confirm_label, callback_data="feed_dist_confirm", style="success")

        if total_pages > 1:
            prev_p = (page - 1) % total_pages
            next_p = (page + 1) % total_pages
            builder.button(text="⬅️", callback_data=f"feed_dist_page {prev_p}")
            builder.button(text=f"{page + 1} / {total_pages}", callback_data="feed_dist_noop")
            builder.button(text="➡️", callback_data=f"feed_dist_page {next_p}")

        num_items = len(chosen_items)
        adjust_pattern = [2] * (num_items // 2)
        if num_items % 2 != 0:
            adjust_pattern.append(1)
        adjust_pattern.append(1)
        if total_pages > 1:
            adjust_pattern.append(3)

        builder.adjust(*adjust_pattern)

    return text, builder.as_markup()


@main_router.callback_query(IsPrivateChat(), F.data == 'feed_dist_noop')
async def feed_dist_noop_calb(call: CallbackQuery):
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_dist_select'))
async def feed_dist_select_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id = data[1]
    item_idx = int(data[2])
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])
    if not chosen_items:
        try: await call.message.delete()
        except Exception: pass
        await call.answer(t('buttons_name.cancel', lang), show_alert=True)
        return

    text, markup = await build_feed_dist_card(user, lang, page, detail_idx=item_idx)
    if text:
        await edit_feed_message(call, text, markup)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_dist_back'))
async def feed_dist_back_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])
    if not chosen_items:
        try: await call.message.delete()
        except Exception: pass
        await call.answer(t('buttons_name.cancel', lang), show_alert=True)
        return

    text, markup = await build_feed_dist_card(user, lang, page, detail_idx=None)
    if text:
        await edit_feed_message(call, text, markup)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_mode'))
async def feed_mode_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    chatid = call.message.chat.id
    user = await User().create(userid)
    data = call.data.split()
    mode = data[1]

    if mode == 'cancel':
        user.settings['feed_draft'] = {}
        user.settings['feed_dist_draft'] = {}
        await user.save()
        try:
            await bot.delete_message(chatid, call.message.message_id)
        except Exception:
            try:
                await call.message.edit_reply_markup(reply_markup=None)
            except Exception: pass
        await bot.send_message(chatid, t('buttons_name.cancel', lang), reply_markup=await m(userid, 'last_menu', lang))
        await call.answer()
        return

    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])
    eligible_ids = feed_draft.get('eligible_ids', [])

    if not chosen_items:
        try:
            await call.message.delete()
        except Exception: pass
        await call.answer(t('buttons_name.cancel', lang), show_alert=True)
        return

    dinos = []
    for alt_id in eligible_ids:
        d = await Dino.find_one(Dino.alt_id == alt_id)
        if d: dinos.append(d)

    if mode == 'all':
        try:
            await bot.delete_message(chatid, call.message.message_id)
        except Exception: pass
        await execute_feed_all_at_once(userid, chatid, lang, user, dinos, chosen_items)
        await call.answer()
        return

    if mode == 'dist':
        dist_draft = {d.alt_id: {} for d in dinos}
        user.settings['feed_dist_draft'] = dist_draft
        await user.save()

        text, markup = await build_feed_dist_card(user, lang, 0)
        if text:
            await edit_feed_message(call, text, markup)
        await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_dist_adj'))
async def feed_dist_adj_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id = data[1]
    item_idx = data[2]
    delta = int(data[3])
    page = int(data[4]) if len(data) > 4 and data[4].isdigit() else 0

    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])
    dist_draft = user.settings.get('feed_dist_draft', {})

    if not chosen_items:
        try:
            await call.message.delete()
        except Exception: pass
        await call.answer(t('buttons_name.cancel', lang), show_alert=True)
        return

    if dino_alt_id not in dist_draft:
        dist_draft[dino_alt_id] = {}

    current_assigned = dist_draft[dino_alt_id].get(item_idx, 0)
    idx_int = int(item_idx)

    if 0 <= idx_int < len(chosen_items):
        item_total = chosen_items[idx_int].get('count', 1)
        total_assigned_other = sum(
            dist_draft.get(d_alt, {}).get(item_idx, 0)
            for d_alt in dist_draft if d_alt != dino_alt_id
        )
        max_assignable_for_this_dino = item_total - total_assigned_other

        new_assigned = max(0, min(current_assigned + delta, max_assignable_for_this_dino))
        dist_draft[dino_alt_id][item_idx] = new_assigned
        user.settings['feed_dist_draft'] = dist_draft
        await user.save()

    text, markup = await build_feed_dist_card(user, lang, page, detail_idx=idx_int)
    if text:
        await edit_feed_message(call, text, markup)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_dist_page'))
async def feed_dist_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    page = int(data[1])

    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])

    if not chosen_items:
        try:
            await call.message.delete()
        except Exception: pass
        await call.answer(t('buttons_name.cancel', lang), show_alert=True)
        return

    text, markup = await build_feed_dist_card(user, lang, page)
    if text:
        await edit_feed_message(call, text, markup)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'feed_dist_confirm')
async def feed_dist_confirm_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    chatid = call.message.chat.id
    user = await User().create(userid)

    feed_draft = user.settings.get('feed_draft', {})
    chosen_items = feed_draft.get('items', [])
    dist_draft = user.settings.get('feed_dist_draft', {})
    eligible_ids = feed_draft.get('eligible_ids', [])

    if not chosen_items:
        try:
            await call.message.delete()
        except Exception: pass
        await call.answer(t('buttons_name.cancel', lang), show_alert=True)
        return

    dinos = []
    for alt_id in eligible_ids:
        d = await Dino.find_one(Dino.alt_id == alt_id)
        if d: dinos.append(d)

    total_assigned_all = sum(
        sum(dist_draft.get(d_alt, {}).values())
        for d_alt in dist_draft
    )

    if total_assigned_all <= 0:
        await call.answer(t('feed.no_assigned', lang, default='⚠️ Вы не распределили продукты ни одному динозавру!'), show_alert=True)
        return

    await call.answer()

    reports = []
    for dino in dinos:
        dino_dist = dist_draft.get(dino.alt_id, {})
        dino_reports = []
        for idx_str, qty in dino_dist.items():
            idx = int(idx_str)
            if 0 <= idx < len(chosen_items) and qty > 0:
                item = chosen_items[idx]
                send_status, return_text = await use_item(userid, chatid, lang, item, qty, dino)
                if send_status and return_text:
                    dino_reports.append(return_text)
        if dino_reports:
            block_text = "\n".join(dino_reports)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{block_text}</blockquote>")

    user.settings['feed_draft'] = {}
    user.settings['feed_dist_draft'] = {}
    await user.save()

    try:
        await bot.delete_message(chatid, call.message.message_id)
    except Exception: pass

    full_text = "\n\n".join(reports) if reports else t('css.no_feed_effect', lang, default='Продукты успешно использованы!')
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'last_menu', lang))
    await auto_ads(mes)

    from bot.modules.tutorial import advance_tutorial_if_step
    await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="feed_wait")


@main_router.message(IsPrivateChat(), Text('commands_name.actions.feed'))
@main_router.message(IsPrivateChat(), Command(commands=['feed']))
async def feed(message: Message):
    if message.from_user:
        userid = message.from_user.id
        lang = await get_lang(message.from_user.id)
        chatid = message.chat.id
        user = await User().create(userid)

        last_dinos = await user.get_last_dinos()

        if not last_dinos:
            await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
            return

        eligible_dinos = []
        for dino in last_dinos:
            st = await dino.status
            st_val = st.value if hasattr(st, 'value') else str(st)
            if st_val not in ['sleep', 'journey']:
                eligible_dinos.append(dino)

        if not eligible_dinos:
            await bot.send_message(chatid, t('item_use.eat.all_busy', lang, default='⚠️ Все ваши динозавры сейчас спят или в путешествии!'), reply_markup=await m(userid, 'last_menu', lang))
            return

        transmitted_data = {
            'chatid': chatid,
            'lang': lang,
            'eligible_dino_ids': [d.alt_id for d in eligible_dinos]
        }

        steps = [
            MultiInventoryStepData(
                'food_items',
                StepMessage(
                    text=t('feed.multinv_title', lang, default='🍖 <b>Сбор продуктов для кормления</b>\n\nВыберите продукты из инвентаря:'),
                    translate_message=False
                ),
                type_filter=['eat'],
                cancel_text_key='cancel_feed',
                limit=600,
                max_different_items=10,
                empty_allowed=False,
                filter_interact=False,
                filter_cant_sell=False,
                changing_filters=False,
                change_reply_markup=False,
                delete_message=True
            )
        ]

        from bot.modules.markup import cancel_markup
        await bot.send_message(chatid, t('commands_name.actions.feed', lang), reply_markup=cancel_markup(lang))

        await ChooseStepHandler(
            multi_feed_start_adapter, userid, chatid, lang, steps,
            transmitted_data=transmitted_data
        ).start()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_inl'))
async def feed_inl(callback: CallbackQuery):
    if callback.message:
        lang = await get_lang(callback.from_user.id)
        chatid = callback.message.chat.id

        if callback.data:
            alt_id = callback.data.split()[1]
            userid = callback.from_user.id

            dino_d = await Dino().create(alt_id)
            if not dino_d:
                await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
                return

            dino_status = await dino_d.status
            st_val = dino_status.value if hasattr(dino_status, 'value') else str(dino_status)
            if st_val == 'sleep':
                await bot.send_message(chatid, t('item_use.eat.sleep', lang), reply_markup=await m(userid, 'last_menu', lang))
                return
            elif st_val == 'journey':
                await bot.send_message(chatid, t('item_use.eat.journey', lang), reply_markup=await m(userid, 'last_menu', lang))
                return

            transmitted_data = {
                'chatid': chatid,
                'lang': lang,
                'eligible_dino_ids': [dino_d.alt_id]
            }

            steps = [
                MultiInventoryStepData(
                    'food_items',
                    StepMessage(
                        text=t('feed.multinv_title', lang, default='🍖 <b>Сбор продуктов для кормления</b>\n\nВыберите продукты из инвентаря:'),
                        translate_message=False
                    ),
                    type_filter=['eat'],
                    cancel_text_key='cancel_feed',
                    limit=600,
                    max_different_items=10,
                    empty_allowed=False,
                    filter_interact=False,
                    filter_cant_sell=False,
                    changing_filters=False,
                    change_reply_markup=False,
                    delete_message=True
                )
            ]

            from bot.modules.markup import cancel_markup
            await bot.send_message(chatid, t('commands_name.actions.feed', lang), reply_markup=cancel_markup(lang))

            await ChooseStepHandler(
                multi_feed_start_adapter, userid, chatid, lang, steps,
                transmitted_data=transmitted_data
            ).start()