"""
Обработчики UI для управления автодействиями динозавра.
Callback-префикс: daa_*
"""
import time
from bson import ObjectId
from aiogram import F
from aiogram.types import CallbackQuery, Message
from bot.exec import main_router, bot
from bot.modules.localization import t, get_lang
from bot.modules.markup import markups_menu as m
from bot.modules.data_format import list_to_inline
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.models.dinosaur import Dino, DinoAutoAction, DinoOwners
from bot.models.enums import DinoOwnerType, DinoStatus
from bot.const import GAME_SETTINGS


async def _edit_or_send_message(message_to_edit: Message, chatid: int, text: str, markup=None):
    """Редактирует текущее сообщение (текст или caption у медиа/фото), а если невозможно — отправляет новое."""
    if message_to_edit:
        try:
            if message_to_edit.photo or message_to_edit.caption is not None:
                await message_to_edit.edit_caption(caption=text, reply_markup=markup)
                return
            else:
                await message_to_edit.edit_text(text, reply_markup=markup)
                return
        except Exception:
            try:
                await message_to_edit.edit_text(text, reply_markup=markup)
                return
            except Exception:
                try:
                    await message_to_edit.edit_caption(caption=text, reply_markup=markup)
                    return
                except Exception:
                    pass
    await bot.send_message(chatid, text, reply_markup=markup)


async def _get_dino_and_owner(alt_id: str, userid: int):
    """Возвращает (dino, is_owner) или (None, False)."""
    dino = await Dino.find_one(Dino.alt_id == alt_id)
    if not dino:
        return None, False

    # Нельзя настраивать для замороженного / находящегося в яйце дино
    st = await dino.check_status()
    if st == DinoStatus.INACTIVE:
        return dino, False

    owners = await DinoOwners.find(DinoOwners.dino.id == dino.id).to_list()
    # Если пользователь является соовнером (ADD_OWNER), настройка автодействий запрещена
    is_add_owner = any(o.owner_id == userid and o.type == DinoOwnerType.ADD_OWNER for o in owners)
    if is_add_owner:
        return dino, False

    is_owner = any(o.owner_id == userid and o.type == DinoOwnerType.OWNER for o in owners)
    return dino, is_owner


def _age_ok(age_days: int, key: str) -> bool:
    aa = GAME_SETTINGS.get('auto_actions', {})
    return age_days >= aa.get(key, 30)


async def _slots_available(userid: int, dino_id: ObjectId, action_type: str, is_premium: bool) -> bool:
    """Проверяет, не превышен ли лимит слотов."""
    aa = GAME_SETTINGS.get('auto_actions', {})
    if action_type == 'deferred':
        existing = await DinoAutoAction.get_deferred(dino_id)
        return existing is None
    key_free = f'{action_type}_slots_free'
    key_prem = f'{action_type}_slots_premium'
    limit = aa.get(key_prem if is_premium else key_free, 1)
    existing = await DinoAutoAction.get_for_dino(dino_id, action_type)
    return len(existing) < limit


# ─── ГЛАВНОЕ МЕНЮ ────────────────────────────────────────────────────────────

def _get_work_opt_name(opt: str, lang: str) -> str:
    from bot.modules.items.item import get_data as get_item_data
    idata = get_item_data(opt)
    if idata:
        return t(f'items.{opt}.name', lang, default=idata.get('name', opt.capitalize()))
    fallback_map = {
        'coal': '🌑 Уголь',
        'stone': '🪨 Камень',
        'iron': '⛓️ Железо',
        'gold': '🪙 Золотая руда',
        'crypto': '💎 Криптовалюта',
        'pine': '🌲 Сосна',
        'oak': '🌳 Дуб',
        'birch': '🪵 Берёза'
    }
    return t(f'items.{opt}.name', lang, default=fallback_map.get(opt, opt.capitalize()))


def _format_action_details(action_cfg: dict, lang: str) -> str:
    if not action_cfg:
        return ""
    act_type = action_cfg.get('type')
    details = []

    if act_type == 'sleep':
        stype = action_cfg.get('sleep_type', 'long')
        if stype == 'short':
            details.append(t('dino_auto_actions.sleep.short', lang, default='Короткий сон'))
        else:
            details.append(t('dino_auto_actions.sleep.long', lang, default='Длинный сон'))

    elif act_type == 'game':
        min_t = action_cfg.get('min_time')
        max_t = action_cfg.get('max_time')
        if min_t and max_t:
            details.append(f"{min_t} - {max_t} мин.")
        elif 'duration' in action_cfg:
            dur_m = action_cfg['duration'] // 60
            details.append(f"{dur_m} мин.")

    elif act_type in ('mine', 'bank', 'sawmill'):
        ptype = action_cfg.get('pay_type', 'coins')
        if ptype == 'coins':
            details.append(t('dino_auto_actions.pay_coins', lang, default='🪙 За монеты'))
        else:
            t_opt = action_cfg.get('target_option', '')
            opt_name = _get_work_opt_name(t_opt, lang) if t_opt else ''
            details.append(f"📦 {opt_name}" if opt_name else t('dino_auto_actions.pay_items', lang, default='📦 За предметы'))

    elif act_type == 'collecting':
        cnt = action_cfg.get('max_count', 10)
        details.append(f"{cnt} шт.")

    elif act_type in ('gym', 'library', 'park', 'swimming_pool', 'fighting'):
        use_energy = action_cfg.get('use_energy_items', False)
        if use_energy:
            details.append('⚡ С энергопредметами')

    elif act_type == 'feed':
        items = action_cfg.get('items', [])
        if items:
            from bot.modules.items.item import get_name, get_data as get_item_data
            item_strs = []
            for itm in items:
                iid = itm.get('item_id')
                cnt = itm.get('count', 1)
                if iid:
                    iname = get_name(iid, lang)
                    if not iname or iname == iid:
                        idata = get_item_data(iid) or {}
                        iname = t(f'items.{iid}.name', lang, default=idata.get('name', iid))
                    item_strs.append(f"{iname} x{cnt}")
            if item_strs:
                details.append(', '.join(item_strs))

    if details:
        return ', '.join(details)
    return ""


async def show_daa_main(chatid: int, userid: int, lang: str, alt_id: str,
                        message_to_edit: Message = None):
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    age_obj = await dino.age()
    age_days = age_obj.days
    aa = GAME_SETTINGS.get('auto_actions', {})

    from bot.modules.user.premium import premium
    is_prem = await premium(userid)

    # Загружаем текущие настройки
    deferred = await DinoAutoAction.get_deferred(dino.id)
    scheduled = await DinoAutoAction.get_for_dino(dino.id, 'scheduled')
    conditional = await DinoAutoAction.get_for_dino(dino.id, 'conditional')

    lines = [
        f"<b>⚙️ {t('dino_auto_actions.title', lang, default='Автоматические действия')} — {dino.name}</b>\n"
    ]


    # 1. Отложенное
    def_min = aa.get('deferred_min_age_days', 30)
    lines.append(f"<b>🔜 {t('dino_auto_actions.deferred', lang, default='Отложенное действие')}</b> <i>(с {def_min} дн.)</i>")
    if age_days >= def_min:
        if deferred:
            act_base = t(f'dino_auto_actions.action.{deferred.action.get("type","?")}', lang, default=deferred.action.get('type','?'))
            skip_info = ' ⏭' if deferred.skip_once else ''
            act_details = _format_action_details(deferred.action, lang)
            if act_details:
                lines.append(f"├ <b>Действие:</b> {act_base}{skip_info}")
                lines.append(f"└ <b>Настройка:</b> {act_details}")
            else:
                lines.append(f"└ <b>Действие:</b> {act_base}{skip_info}")
        else:
            lines.append(f"├ <b>Статус:</b> <i>{t('dino_auto_actions.not_set', lang, default='не настроено')}</i>")
    else:
        days_left = def_min - age_days
        lines.append(f"├ <b>Статус:</b> 🔒 <i>доступно через {days_left} дн.</i>")

    lines.append("")

    # 2. По расписанию
    sch_min = aa.get('scheduled_min_age_days', 60)
    sch_limit = aa.get('scheduled_slots_premium' if is_prem else 'scheduled_slots_free', 1)
    lines.append(f"<b>⏰ {t('dino_auto_actions.scheduled', lang, default='По расписанию')}</b> <i>[{len(scheduled)}/{sch_limit}]</i> <i>(с {sch_min} дн.)</i>")
    if age_days >= sch_min:
        if scheduled:
            import datetime
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            for s in scheduled:
                st = s.schedule_time or {}
                skip_info = ' ⏭' if s.skip_once else ''
                act_base = t(f'dino_auto_actions.action.{s.action.get("type","?")}', lang, default=s.action.get('type','?'))
                act_details = _format_action_details(s.action, lang)
                tz_off = st.get('tz_offset', 0)
                tz_sign = '+' if tz_off >= 0 else ''
                now_tz = now_utc + datetime.timedelta(hours=tz_off)
                now_str = now_tz.strftime('%H:%M')
                time_str = f"<b>{st.get('hour',0):02d}:{st.get('minute',0):02d} UTC{tz_sign}{tz_off}</b> <i>(сейчас {now_str})</i>"
                if act_details:
                    lines.append(f"├ {time_str} → {act_base}{skip_info}")
                    lines.append(f"└ <b>Настройка:</b> {act_details}")
                else:
                    lines.append(f"└ {time_str} → {act_base}{skip_info}")
        else:
            lines.append(f"├ <b>Статус:</b> <i>{t('dino_auto_actions.not_set', lang, default='не настроено')}</i>")

    else:
        days_left = sch_min - age_days
        lines.append(f"├ <b>Статус:</b> 🔒 <i>доступно через {days_left} дн.</i>")

    lines.append("")

    # 3. При X
    cond_min = aa.get('conditional_min_age_days', 90)
    cond_limit = aa.get('conditional_slots_premium' if is_prem else 'conditional_slots_free', 1)
    lines.append(f"<b>🎯 {t('dino_auto_actions.conditional', lang, default='При условии (При X)')}</b> <i>[{len(conditional)}/{cond_limit}]</i> <i>(с {cond_min} дн.)</i>")
    if age_days >= cond_min:
        if conditional:
            for c in conditional:
                cond = c.condition or {}
                skip_info = ' ⏭' if c.skip_once else ''
                act_base = t(f'dino_auto_actions.action.{c.action.get("type","?")}', lang, default=c.action.get('type','?'))
                act_details = _format_action_details(c.action, lang)
                if cond.get('stat') == 'activity_end':
                    cond_text = f"⏳ {t('dino_auto_actions.cond.activity_end', lang, default='Конец активности')}"
                else:
                    c_stat = cond.get('stat', '?')
                    c_emoji = COND_EMOJIS.get(c_stat, '')
                    cond_stat_name = t(f'dino_auto_actions.cond.{c_stat}', lang, default=c_stat)
                    cond_text = f"{c_emoji} {cond_stat_name} ≤ {cond.get('threshold', 0)}".strip()
                if act_details:
                    lines.append(f"├ <b>{cond_text}:</b> {act_base}{skip_info}")
                    lines.append(f"└ <b>Настройка:</b> {act_details}")
                else:
                    lines.append(f"└ <b>{cond_text}:</b> {act_base}{skip_info}")
        else:
            lines.append(f"├ <b>Статус:</b> <i>{t('dino_auto_actions.not_set', lang, default='не настроено')}</i>")
    else:
        days_left = cond_min - age_days
        lines.append(f"├ <b>Статус:</b> 🔒 <i>доступно через {days_left} дн.</i>")

    lines.append("")

    if not is_prem:

        lines.append(f"<i>{t('dino_auto_actions.premium_hint', lang, default='💡 Доступно 2 слота по расписанию и при условии с подпиской DinoUltima')}</i>")


    text = '\n'.join(lines)

    # Кнопки
    rows = []
    if age_days >= def_min:
        if deferred:
            def_act_name = t(f'dino_auto_actions.action.{deferred.action.get("type","?")}', lang, default=deferred.action.get('type','?'))
            rows.append([
                {def_act_name: 'daa_noop'},
                {t('dino_auto_actions.btn_edit', lang, default='✏️'): f'daa_edit deferred 0 {alt_id}'},
                {t('dino_auto_actions.btn_del', lang, default='🗑'): f'daa_delete {str(deferred.id)} {alt_id}'}
            ])
        else:
            rows.append({t('dino_auto_actions.btn_deferred_add', lang, default='➕ Задать отложенное'): f'daa_add deferred {alt_id}'})

    if age_days >= sch_min and len(scheduled) < sch_limit:
        rows.append({t('dino_auto_actions.btn_sched_add', lang, default='➕ Добавить расписание'): f'daa_add scheduled {alt_id}'})
    for i, s in enumerate(scheduled):
        sch_act_name = t(f'dino_auto_actions.action.{s.action.get("type","?")}', lang, default=s.action.get('type','?'))
        rows.append([
            {sch_act_name: 'daa_noop'},
            {t('dino_auto_actions.btn_edit', lang, default='✏️'): f'daa_edit scheduled {i} {alt_id}'},
            {t('dino_auto_actions.btn_del', lang, default='🗑'): f'daa_delete {str(s.id)} {alt_id}'}
        ])
        rows.append({
            (t('dino_auto_actions.btn_skip_cancel', lang, default='❌ Отменить пропуск') if s.skip_once else t('dino_auto_actions.btn_skip', lang, default='⏭ Пропустить 1 раз')): f'daa_skip {str(s.id)} {alt_id}'
        })

    if age_days >= cond_min and len(conditional) < cond_limit:
        rows.append({t('dino_auto_actions.btn_cond_add', lang, default='➕ Добавить условие'): f'daa_add conditional {alt_id}'})
    for i, c in enumerate(conditional):
        cond_act_name = t(f'dino_auto_actions.action.{c.action.get("type","?")}', lang, default=c.action.get('type','?'))
        rows.append([
            {cond_act_name: 'daa_noop'},
            {t('dino_auto_actions.btn_edit', lang, default='✏️'): f'daa_edit conditional {i} {alt_id}'},
            {t('dino_auto_actions.btn_del', lang, default='🗑'): f'daa_delete {str(c.id)} {alt_id}'}
        ])
        rows.append({
            (t('dino_auto_actions.btn_skip_cancel', lang, default='❌ Отменить пропуск') if c.skip_once else t('dino_auto_actions.btn_skip', lang, default='⏭ Пропустить 1 раз')): f'daa_skip {str(c.id)} {alt_id}'
        })



    # Доп кнопки: Инфо, Донат (если нет премиума), Профиль
    nav_row = {
        t('dino_auto_actions.btn_info', lang, default='ℹ️ Информация'): f'daa_info {alt_id}',
        t('dino_auto_actions.btn_profile', lang, default='👤 Профиль'): {'callback_data': f'dino_profile {alt_id}', 'style': 'primary'}
    }
    if not is_prem:
        nav_row[t('dino_auto_actions.btn_subscribe', lang, default='{custom_emoji:star} DinoUltima')] = 'support info dino_ultima'

    rows.append(nav_row)

    markup = list_to_inline(rows, 2)
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


async def _show_daa_main_edit_by_id(chatid: int, userid: int, lang: str, alt_id: str, message_id: int):
    """Показывает меню автодействий, редактируя существующее сообщение по message_id напрямую (для фото-сообщений профиля)."""
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        await show_daa_main(chatid, userid, lang, alt_id)
        return

    age_obj = await dino.age()
    age_days = age_obj.days
    aa = GAME_SETTINGS.get('auto_actions', {})

    from bot.modules.user.premium import premium
    is_prem = await premium(userid)

    deferred = await DinoAutoAction.get_deferred(dino.id)
    scheduled = await DinoAutoAction.get_for_dino(dino.id, 'scheduled')
    conditional = await DinoAutoAction.get_for_dino(dino.id, 'conditional')

    # Reuse show_daa_main to build text+markup by passing a dummy message_to_edit=None
    # then call it with edit via message_id
    # Instead, build inline and call bot API directly
    class _FakeEditMsg:
        """Surrogate Message that routes edit_caption / edit_text to bot API calls by ID."""
        def __init__(self, mid, cid):
            self.message_id = mid
            self.photo = True  # treat as photo so _edit_or_send_message tries edit_caption first
            self.caption = ""
            self.chat = type('_C', (), {'id': cid})()

        async def edit_caption(self, caption, reply_markup=None, **kwargs):
            await bot.edit_message_caption(
                chat_id=chatid, message_id=self.message_id,
                caption=caption, reply_markup=reply_markup, parse_mode='HTML'
            )

        async def edit_text(self, text, reply_markup=None, **kwargs):
            await bot.edit_message_text(
                chat_id=chatid, message_id=self.message_id,
                text=text, reply_markup=reply_markup, parse_mode='HTML'
            )

    fake = _FakeEditMsg(message_id, chatid)
    await show_daa_main(chatid, userid, lang, alt_id, message_to_edit=fake)




@main_router.callback_query(IsPrivateChat(), F.data == 'daa_noop')
async def daa_noop_callback(callback: CallbackQuery):
    await callback.answer()


# ─── ИНФОРМАЦИОННАЯ СТРАНИЦА ──────────────────────────────────────────────────


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_info'))
async def daa_info_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    alt_id = callback.data.split()[1]

    info_text = (
        f"<b>ℹ️ {t('dino_auto_actions.info_title', lang, default='Информация об автодействиях')}</b>\n\n"
        f"<b>🔜 {t('dino_auto_actions.deferred', lang, default='Отложенное действие')}</b> <i>(от 30 дн.)</i>:\n"
        f"Автоматически выполняется сразу после того, как динозавр завершит текущую активность (сон, игра, сбор, работа).\n\n"
        f"<b>⏰ {t('dino_auto_actions.scheduled', lang, default='По расписанию')}</b> <i>(от 60 дн.)</i>:\n"
        f"Запускается каждый день в выбранное время с учётом вашего часового пояса. "
        f"Если динозавр занят в это время, действие ставится в отложенное.\n\n"
        f"<b>🎯 {t('dino_auto_actions.conditional', lang, default='При условии (При X)')}</b> <i>(от 90 дн.)</i>:\n"
        f"Срабатывает, когда указанный показатель (энергия, сытость, здоровье и т.д.) опускается до выбранного порога, "
        f"либо по завершении любой активности. Кулдаун после срабатывания: 12 часов.\n\n"
        f"<i>{t('dino_auto_actions.premium_hint', lang, default='💡 Доступно 2 слота по расписанию и при условии с подпиской DinoUltima')}</i>"
    )

    markup = list_to_inline([
        {
            t('buttons_name.back', lang, default='↪️ Назад'): {'callback_data': f'daa_main {alt_id}', 'style': 'danger'},
            t('dino_auto_actions.btn_subscribe', lang, default='{custom_emoji:star} DinoUltima'): 'support info dino_ultima',
            t('dino_auto_actions.btn_profile', lang, default='👤 Профиль'): {'callback_data': f'dino_profile {alt_id}', 'style': 'primary'}
        }
    ])


    await _edit_or_send_message(callback.message, callback.message.chat.id, info_text, markup)


# ─── CALLBACKS ───────────────────────────────────────────────────────────────

@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_main'))
async def daa_main_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    alt_id = callback.data.split()[1]

    # Delete prompt_msg if present
    from bot.modules.get_state import get_state
    state = await get_state(userid, callback.message.chat.id)
    was_in_setup = False
    if state:
        data = await state.get_data()
        prompt_id = data.get('daa_prompt_id') or data.get('transmitted_data', {}).get('prompt_msg_id')
        if prompt_id:
            was_in_setup = True
            try:
                await bot.delete_message(callback.message.chat.id, prompt_id)
            except Exception:
                pass
        await state.clear()

    # Only send return message with last_menu reply keyboard if canceling an active setup
    if was_in_setup:
        from bot.modules.markup import markups_menu as m
        try:
            await bot.send_message(callback.message.chat.id, t('p_profile.return', lang, default='🔮 | Возвращение в главное меню!'), reply_markup=await m(userid, 'last_menu', lang))
        except Exception:
            pass

    # Update/restore the daa_main profile photo message
    await show_daa_main(callback.message.chat.id, userid, lang, alt_id, callback.message)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_skip'))
async def daa_skip_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    action_id_str, alt_id = parts[1], parts[2]
    try:
        action = await DinoAutoAction.get(ObjectId(action_id_str))
        if action:
            action.skip_once = not action.skip_once
            await action.save()
    except Exception:
        pass
    await show_daa_main(callback.message.chat.id, userid, lang, alt_id, callback.message)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_delete'))
async def daa_delete_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    action_id_str, alt_id = parts[1], parts[2]
    try:
        action = await DinoAutoAction.get(ObjectId(action_id_str))
        if action:
            await action.delete()
    except Exception:
        pass
    await show_daa_main(callback.message.chat.id, userid, lang, alt_id, callback.message)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_add'))
async def daa_add_callback(callback: CallbackQuery):
    """Начало добавления нового автодействия."""
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    action_type = parts[1]
    alt_id = parts[2]

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    if action_type == 'deferred':
        st = await dino.check_status()
        if st == DinoStatus.PASS:
            text = t(
                'dino_auto_actions.deferred_only_busy', lang,
                default='❌ <b>Отложенное действие нельзя установить, пока динозавр свободен!</b>\n\nОтложенное действие предназначено для того, чтобы задать активность, которая выполнится сразу после завершения текущего занятия динозавра.'
            )
            markup = list_to_inline([
                {
                    t('buttons_name.back', lang, default='↪️ Назад'): {'callback_data': f'daa_main {alt_id}', 'style': 'danger'},
                    t('dino_auto_actions.btn_profile', lang, default='👤 Профиль'): {'callback_data': f'dino_profile {alt_id}', 'style': 'primary'}
                }
            ])
            await _edit_or_send_message(callback.message, callback.message.chat.id, text, markup)
            return

    from bot.modules.markup import cancel_markup
    prompt_msg = await bot.send_message(
        callback.message.chat.id,
        t('dino_auto_actions.setup_started', lang, default='⚙️ Начата настройка автоматического действия...'),
        reply_markup=cancel_markup(lang)
    )

    from bot.modules.get_state import get_state
    from bot.modules.states_fabric.state_handlers import GeneralStates
    state = await get_state(userid, callback.message.chat.id)
    if state:
        await state.set_state(GeneralStates.ChooseOption)
        await state.update_data(
            daa_prompt_id=prompt_msg.message_id,
            daa_main_msg_id=callback.message.message_id,
            daa_alt_id=alt_id,
            transmitted_data={
                'prompt_msg_id': prompt_msg.message_id,
                'main_msg_id': callback.message.message_id,
                'alt_id': alt_id,
                'chatid': callback.message.chat.id,
                'userid': userid,
                'lang': lang,
                'action_type': action_type
            }
        )

    await show_action_type_picker(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message)


CATEGORIES = [
    {
        'key': 'life',
        'title': '❤️ Жизнь',
        'acts': ['feed', 'sleep', 'game', 'collecting']
    },
    {
        'key': 'quick',
        'title': '⚡ Быстрая активность',
        'acts': ['pet', 'talk', 'fighting']
    },
    {
        'key': 'training',
        'title': '🥏 Тренировки',
        'acts': ['gym', 'library', 'park', 'swimming_pool']
    },
    {
        'key': 'work',
        'title': '⛏️ Работы',
        'acts': ['mine', 'bank', 'sawmill']
    }
]



async def show_action_type_picker(chatid: int, userid: int, lang: str, alt_id: str, action_type: str, dino_id: ObjectId, message_to_edit: Message = None, page_idx: int = 0):
    """Показывает список доступных типов действий с пагинацией по категориям."""
    aa = GAME_SETTINGS.get('auto_actions', {})
    available = set(aa.get('available_actions', []))

    cat_count = len(CATEGORIES)
    page_idx = page_idx % cat_count
    cat = CATEGORIES[page_idx]

    cat_acts = [act for act in cat['acts'] if act in available]

    rows = []
    row = {}
    for act in cat_acts:
        act_name = t(f'dino_auto_actions.action.{act}', lang, default=act)
        cd = f'daa_pick_action {action_type} {act} {alt_id}'
        row[act_name] = cd
        if len(row) == 2:
            rows.append(row)
            row = {}
    if row:
        rows.append(row)

    prev_page = (page_idx - 1) % cat_count
    next_page = (page_idx + 1) % cat_count
    cat_title_btn = f"{cat['title']} [{page_idx + 1}/{cat_count}]"

    rows.append([
        {'◀': f'daa_pick_page {prev_page} {action_type} {alt_id}'},
        {cat_title_btn: 'daa_noop'},
        {'▶': f'daa_pick_page {next_page} {action_type} {alt_id}'}
    ])

    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    profile_text = t('dino_auto_actions.btn_profile', lang, default='👤 Профиль')
    rows.append([
        {cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}},
        {profile_text: {'callback_data': f'dino_profile {alt_id}', 'style': 'primary'}}
    ])


    markup = list_to_inline(rows, 2)
    pick_prompt = t('dino_auto_actions.pick_action', lang, default='Выберите действие:')
    text = f"<b>{cat['title']}</b> <i>[{page_idx + 1}/{cat_count}]</i>\n\n{pick_prompt}"
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_pick_page'))
async def daa_pick_page_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    page_idx = int(parts[1])
    action_type = parts[2]
    alt_id = parts[3]

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    await show_action_type_picker(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message, page_idx)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_pick_action'))
async def daa_pick_action_callback(callback: CallbackQuery):
    """Выбор типа действия и начало настройки параметров."""
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    action_type = parts[1]
    act = parts[2]
    alt_id = parts[3]

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    action_cfg = {'type': act}

    if act == 'feed':
        await _start_feed_setup(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message)
        return

    if act in ('gym', 'library', 'park', 'swimming_pool'):
        await _start_skill_setup(callback.message.chat.id, userid, lang, alt_id, action_type, act, dino.id, callback.message)
        return

    if act == 'game':
        await _start_game_setup(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message)
        return

    if act in ('mine', 'bank', 'sawmill'):
        await _start_work_setup(callback.message.chat.id, userid, lang, alt_id, action_type, act, dino.id, callback.message)
        return

    if act == 'sleep':
        await _start_sleep_setup(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message)
        return

    if act == 'collecting':
        await _start_collecting_setup(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message)
        return

    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)


async def _start_skill_setup(chatid, userid, lang, alt_id, action_type, skill, dino_id, message_to_edit: Message = None):
    text = t('dino_auto_actions.pick_energy', lang, default='⚡ Использовать энергопредметы при тренировке?')
    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows = [
        {
            t('buttons_name.yes', lang, default='✅ Да'): f'daa_skill_energy 1 {skill} {action_type} {alt_id}',
            t('buttons_name.no', lang, default='❌ Нет'): f'daa_skill_energy 0 {skill} {action_type} {alt_id}'
        },
        {cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}}
    ]
    markup = list_to_inline(rows, 2)
    await _edit_or_send_message(message_to_edit, chatid, text, markup)



@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_skill_energy'))
async def daa_skill_energy(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    use_energy_val, skill, action_type, alt_id = parts[1], parts[2], parts[3], parts[4]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    action_cfg = {'type': skill, 'use_energy_items': bool(int(use_energy_val))}
    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)


async def _start_game_setup(chatid, userid, lang, alt_id, action_type, dino_id, message_to_edit: Message = None):
    text = t('dino_auto_actions.pick_game_duration', lang, default='⏱ Выберите разрешённый промежуток времени игры:')
    durations = [
        ('15 - 30 мин.', 15, 30),
        ('30 - 60 мин.', 30, 60),
        ('60 - 90 мин.', 60, 90),
        ('90 - 120 мин.', 90, 120)
    ]
    rows = [{label: f'daa_game_dur {min_t} {max_t} {action_type} {alt_id}'} for label, min_t, max_t in durations]
    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append({cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}})
    markup = list_to_inline(rows, 2)
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_game_dur'))
async def daa_game_dur(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    min_t, max_t, action_type, alt_id = parts[1], parts[2], parts[3], parts[4]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    action_cfg = {'type': 'game', 'min_time': int(min_t), 'max_time': int(max_t)}
    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)


async def _start_sleep_setup(chatid, userid, lang, alt_id, action_type, dino_id, message_to_edit: Message = None):
    from bot.models.items import Item
    from bot.models.dinosaur import Dino
    dino = await Dino.find_one(Dino.id == ObjectId(dino_id))
    has_bear = await Item.check_accessory(dino, 'bear') if dino else False

    rows = [
        {t('dino_auto_actions.sleep.long', lang, default='Длинный сон'): f'daa_sleep_type long {action_type} {alt_id}'}
    ]
    if has_bear:
        rows.append({t('dino_auto_actions.sleep.short', lang, default='Короткий сон'): f'daa_sleep_type short {action_type} {alt_id}'})

    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append({cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}})
    markup = list_to_inline(rows)
    text = t('dino_auto_actions.pick_sleep', lang, default='Тип сна:')
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_sleep_type'))
async def daa_sleep_type(callback: CallbackQuery):
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    sleep_type, action_type, alt_id = parts[1], parts[2], parts[3]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        await callback.answer()
        return
    if sleep_type == 'short':
        from bot.models.items import Item
        if not await Item.check_accessory(dino, 'bear'):
            await callback.answer(t('dino_auto_actions.need_bear', lang, default='❌ Для выбора короткого сна необходим аксессуар Мишка!'), show_alert=True)
            return
    await callback.answer()
    action_cfg = {'type': 'sleep', 'sleep_type': sleep_type}
    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)


async def _start_collecting_setup(chatid, userid, lang, alt_id, action_type, dino_id, message_to_edit: Message = None):
    options = ['collecting', 'hunt', 'fishing', 'all']
    rows = [{t(f'collecting.buttons.{o}', lang, default=o): f'daa_coll_type {o} {action_type} {alt_id}'} for o in options]
    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append({cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}})
    markup = list_to_inline(rows)
    text = t('dino_auto_actions.pick_collecting', lang, default='Тип сбора:')
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_coll_type'))
async def daa_coll_type(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    coll_type, action_type, alt_id = parts[1], parts[2], parts[3]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    await _start_coll_count_setup(callback.message.chat.id, userid, lang, alt_id, action_type, coll_type, dino, callback.message)


async def _start_coll_count_setup(chatid, userid, lang, alt_id, action_type, coll_type, dino, message_to_edit: Message = None):
    from bot.models.items import Item
    from bot.modules.user.user import User
    from bot.const import GAME_SETTINGS

    user = await User().create(userid)
    is_prem = await user.premium
    base_max = GAME_SETTINGS.get('premium_max_collecting', 200) if is_prem else GAME_SETTINGS.get('max_collecting', 100)
    has_basket = await Item.check_accessory(dino, 'basket') if dino else False
    max_count = base_max + (20 if has_basket else 0)

    if base_max <= 100:
        counts = [10, 25, 50, 75, base_max]
    else:
        counts = [25, 50, 100, 150, base_max]

    if has_basket and max_count not in counts:
        counts.append(max_count)

    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows = [{f'{c} шт.': f'daa_coll_count {c} {coll_type} {action_type} {alt_id}'} for c in counts]
    rows.append({cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}})
    markup = list_to_inline(rows, 3)
    text = t('dino_auto_actions.pick_coll_count', lang, default='🧺 Выберите количество предметов для сбора:')
    await _edit_or_send_message(message_to_edit, chatid, text, markup)



@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_coll_count'))
async def daa_coll_count(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    cnt_str, coll_type, action_type, alt_id = parts[1], parts[2], parts[3], parts[4]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    action_cfg = {'type': 'collecting', 'coll_type': coll_type, 'max_count': int(cnt_str)}
    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)


async def _start_work_setup(chatid, userid, lang, alt_id, action_type, work_type, dino_id, message_to_edit: Message = None):
    options_map = {
        'mine': ['coal', 'stone', 'iron'],
        'bank': ['gold', 'crypto'],
        'sawmill': ['pine', 'oak', 'birch'],
    }
    opts = options_map.get(work_type, [])
    rows = [{_get_work_opt_name(o, lang): f'daa_work_opt {work_type} {o} {action_type} {alt_id}'} for o in opts]
    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append({cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}})
    markup = list_to_inline(rows)
    work_name = t(f'dino_auto_actions.action.{work_type}', lang, default=work_type)
    pick_prompt = t('dino_auto_actions.pick_work_option', lang, default='Выберите тип ресурса:')
    text = f"<b>{work_name}</b>\n\n{pick_prompt}"
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_work_opt'))
async def daa_work_opt(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    work_type, target_opt, action_type, alt_id = parts[1], parts[2], parts[3], parts[4]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    await _start_work_pay_setup(callback.message.chat.id, userid, lang, alt_id, action_type, work_type, target_opt, dino.id, callback.message)


async def _start_work_pay_setup(chatid, userid, lang, alt_id, action_type, work_type, target_opt, dino_id, message_to_edit: Message = None):
    text = t('dino_auto_actions.pick_work_pay', lang, default='💼 Выберите тип награды за работу:')
    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows = [
        {
            t('dino_auto_actions.pay_coins', lang, default='🪙 За монеты'): f'daa_work_pay coins {work_type} {target_opt} {action_type} {alt_id}',
            t('dino_auto_actions.pay_items', lang, default='📦 За предметы'): f'daa_work_pay items {work_type} {target_opt} {action_type} {alt_id}'
        },
        {cancel_text: {'callback_data': f'daa_main {alt_id}', 'style': 'danger'}}
    ]
    markup = list_to_inline(rows, 2)
    await _edit_or_send_message(message_to_edit, chatid, text, markup)



@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_work_pay'))
async def daa_work_pay(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    pay_type, work_type, target_opt, action_type, alt_id = parts[1], parts[2], parts[3], parts[4], parts[5]
    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    final_target = 'coins' if pay_type == 'coins' else target_opt
    action_cfg = {'type': work_type, 'target_option': final_target, 'pay_type': pay_type}
    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)


async def _start_feed_setup(chatid, userid, lang, alt_id, action_type, dino_id, message_to_edit: Message = None, page: int = 0):
    """Легкий встраиваемый инлайн-выбор продуктов питания из инвентаря пользователя."""
    from bot.modules.user.user import User
    from bot.modules.inventory_tools import filter_and_sort_inventory
    from bot.modules.data_format import chunks

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    inventory, _ = await User.get_inventory(userid)
    sorted_items = filter_and_sort_inventory(inventory, lang, type_filter=['eat'])

    if not sorted_items:
        text = f"🍖 <b>{t('dino_auto_actions.action.feed', lang, default='Покормить')}</b>\n\n" + t('feed.no_items', lang, default='❌ У вас нет продуктов питания в инвентаре!')
        cancel_text = t('buttons_name.back', lang, default='↪️ Назад')
        markup = list_to_inline([[{'text': cancel_text, 'callback_data': f'daa_main {alt_id}', 'style': 'danger'}]])
        await _edit_or_send_message(message_to_edit, chatid, text, markup)
        return

    food_item_ids = []
    for _, item_dict, _ in sorted_items:
        iid = item_dict.get('item_id') if isinstance(item_dict, dict) else str(item_dict)
        food_item_ids.append(iid)

    from bot.modules.get_state import get_state
    state = await get_state(userid, chatid)
    if state:
        await state.update_data(
            daa_food_items=food_item_ids,
            daa_action_type=action_type
        )

    items_per_page = 6
    item_chunks = chunks(sorted_items, items_per_page)
    total_pages = len(item_chunks)
    page = max(0, min(page, total_pages - 1))
    current_chunk = item_chunks[page]

    rows = []
    item_btns = []
    start_idx = page * items_per_page
    for i, (display_name, item_dict, meta) in enumerate(current_chunk):
        global_idx = start_idx + i
        item_btns.append({
            'text': display_name,
            'callback_data': f'dfi {global_idx} {alt_id}'
        })

    for pair in chunks(item_btns, 2):
        rows.append(pair)

    if total_pages > 1:
        prev_page = (page - 1) % total_pages
        next_page = (page + 1) % total_pages
        nav_row = [
            {'text': '◀️', 'callback_data': f'dfp {prev_page} {alt_id}'},
            {'text': f'{page + 1}/{total_pages}', 'callback_data': 'daa_noop'},
            {'text': '▶️', 'callback_data': f'dfp {next_page} {alt_id}'}
        ]
        rows.append(nav_row)

    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append([{'text': cancel_text, 'callback_data': f'daa_main {alt_id}', 'style': 'danger'}])

    markup = list_to_inline(rows, 2)
    text = t('dino_auto_actions.pick_feed_item', lang, default='🍖 <b>Сбор продуктов для автокормления</b>\n\nВыберите продукт из вашего инвентаря:')
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('dfp'))
async def dfp_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    page, alt_id = int(parts[1]), parts[2]

    from bot.modules.get_state import get_state
    state = await get_state(userid, callback.message.chat.id)
    action_type = 'deferred'
    if state:
        data = await state.get_data()
        action_type = data.get('daa_action_type') or data.get('transmitted_data', {}).get('action_type', 'deferred')

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return
    await _start_feed_setup(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message, page=page)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('dfi'))
async def dfi_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    idx = int(parts[1])
    alt_id = parts[2]

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    from bot.modules.get_state import get_state
    state = await get_state(userid, callback.message.chat.id)
    item_id = None
    if state:
        data = await state.get_data()
        food_items = data.get('daa_food_items', [])
        if 0 <= idx < len(food_items):
            item_id = food_items[idx]

    if not item_id:
        from bot.modules.user.user import User
        from bot.modules.inventory_tools import filter_and_sort_inventory
        inventory, _ = await User.get_inventory(userid)
        sorted_items = filter_and_sort_inventory(inventory, lang, type_filter=['eat'])
        if 0 <= idx < len(sorted_items):
            item_dict = sorted_items[idx][1]
            item_id = item_dict.get('item_id') if isinstance(item_dict, dict) else str(item_dict)

    if not item_id:
        return

    from bot.modules.items.item import get_name
    item_name = get_name(item_id, lang)
    counts = [1, 5, 10, 20, 50]
    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    cnt_btns = [{'text': f'{c} шт.', 'callback_data': f'dfc {c} {idx} {alt_id}'} for c in counts]
    rows = []
    from bot.modules.data_format import chunks
    for pair in chunks(cnt_btns, 3):
        rows.append(pair)
    rows.append([{'text': cancel_text, 'callback_data': f'daa_main {alt_id}', 'style': 'danger'}])

    markup = list_to_inline(rows, 3)
    text = t('dino_auto_actions.pick_feed_count', lang, default=f'🍖 <b>{item_name}</b>\n\nВыберите количество предмета:')
    await _edit_or_send_message(callback.message, callback.message.chat.id, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('dfc'))
async def dfc_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    if len(parts) < 4:
        return
    count = int(parts[1])
    idx = int(parts[2])
    alt_id = parts[3]

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    from bot.modules.get_state import get_state
    state = await get_state(userid, callback.message.chat.id)
    item_id = None
    action_type = 'deferred'
    if state:
        data = await state.get_data()
        food_items = data.get('daa_food_items', [])
        action_type = data.get('daa_action_type') or data.get('transmitted_data', {}).get('action_type', 'deferred')
        if 0 <= idx < len(food_items):
            item_id = food_items[idx]

    if not item_id:
        from bot.modules.user.user import User
        from bot.modules.inventory_tools import filter_and_sort_inventory
        inventory, _ = await User.get_inventory(userid)
        sorted_items = filter_and_sort_inventory(inventory, lang, type_filter=['eat'])
        if 0 <= idx < len(sorted_items):
            item_dict = sorted_items[idx][1]
            item_id = item_dict.get('item_id') if isinstance(item_dict, dict) else str(item_dict)

    if not item_id:
        return

    action_cfg = {'type': 'feed', 'items': [{'item_id': item_id, 'count': count}]}
    await _finalize_action_setup(callback.message.chat.id, userid, lang, alt_id, action_type, action_cfg, dino, callback.message)



async def _clean_temp_messages_and_restore_menu(chatid: int, owner_id: int, lang: str, transmitted_data: dict):
    for key in ('prompt_msg_id', 'picker_msg_id', 'int_prompt_msg_id'):
        mid = transmitted_data.get(key)
        if mid:
            try:
                await bot.delete_message(chatid, mid)
            except Exception:
                pass
    from bot.modules.markup import markups_menu as m
    try:
        await bot.send_message(chatid, t('p_profile.return', lang, default='🏠 Главное меню'), reply_markup=await m(owner_id, 'last_menu', lang))
    except Exception:
        pass


async def auto_action_on_time_chosen(value: dict, transmitted_data: dict):
    act_cfg = transmitted_data.get('action_cfg', {})
    dino_id_str = transmitted_data.get('dino_id_str', '')
    alt_id_td = transmitted_data.get('alt_id', '')
    owner_id_td = transmitted_data.get('owner_id', 0)
    chatid = transmitted_data.get('chatid', owner_id_td)
    lang = transmitted_data.get('lang', 'ru')
    main_msg_id = transmitted_data.get('main_msg_id', 0)
    doc = DinoAutoAction(
        dino_id=ObjectId(dino_id_str),
        owner_id=owner_id_td,
        action_type='scheduled',
        action=act_cfg,
        schedule_time={'hour': value['hour'], 'minute': value['minute'], 'tz_offset': value['tz_offset']},
    )
    await doc.insert()

    # Send return/success notification with last_menu keyboard first
    await _clean_temp_messages_and_restore_menu(chatid, owner_id_td, lang, transmitted_data)

    # Update the daa_main profile photo message second
    if main_msg_id:
        await _show_daa_main_edit_by_id(chatid, owner_id_td, lang, alt_id_td, main_msg_id)
    else:
        await show_daa_main(chatid, owner_id_td, lang, alt_id_td)


async def auto_action_on_threshold(threshold: int, transmitted_data: dict):
    act_cfg = transmitted_data.get('action_cfg', {})
    alt_id_td = transmitted_data.get('alt_id', '')
    dino_id_str = transmitted_data.get('dino_id_str', '')
    owner_id_td = transmitted_data.get('owner_id', 0)
    cond_stat = transmitted_data.get('cond_stat', '')
    chatid = transmitted_data.get('chatid', owner_id_td)
    lang = transmitted_data.get('lang', 'ru')
    condition = {'stat': cond_stat, 'threshold': threshold, 'op': '<='}
    doc = DinoAutoAction(
        dino_id=ObjectId(dino_id_str), owner_id=owner_id_td,
        action_type='conditional', action=act_cfg, condition=condition
    )
    await doc.insert()
    await _clean_temp_messages_and_restore_menu(chatid, owner_id_td, lang, transmitted_data)
    await show_daa_main(chatid, owner_id_td, lang, alt_id_td)



async def _finalize_action_setup(chatid: int, userid: int, lang: str,
                                  alt_id: str, action_type: str,
                                  action_cfg: dict, dino: Dino, message_to_edit: Message = None):
    """После выбора действия — переходим к выбору условия или завершаем."""
    if action_type == 'deferred':
        await DinoAutoAction.upsert_deferred(dino.id, userid, action_cfg)
        from bot.modules.get_state import get_state
        state = await get_state(userid, chatid)
        if state:
            data = await state.get_data()
            if prompt_id := data.get('daa_prompt_id'):
                try:
                    await bot.delete_message(chatid, prompt_id)
                except Exception:
                    pass
            await state.clear()

        from bot.modules.markup import markups_menu as m
        try:
            await bot.send_message(chatid, t('p_profile.return', lang, default='🔮 | Возвращение в главное меню!'), reply_markup=await m(userid, 'last_menu', lang))
        except Exception:
            pass

        await show_daa_main(chatid, userid, lang, alt_id, message_to_edit)
        return

    if action_type == 'scheduled':
        from bot.modules.states_fabric.state_handlers import ChooseTimeHandler
        main_msg_id = message_to_edit.message_id if message_to_edit else 0
        # Remove inline buttons from the current daa_main message while time picker is open
        if message_to_edit:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=chatid,
                    message_id=main_msg_id,
                    reply_markup=None
                )
            except Exception:
                pass
        handler = ChooseTimeHandler(
            auto_action_on_time_chosen, userid, chatid, lang,
            transmitted_data={
                'action_cfg': action_cfg, 'dino_id_str': str(dino.id),
                'alt_id': alt_id, 'owner_id': userid, 'chatid': chatid, 'lang': lang,
                'main_msg_id': main_msg_id
            }
        )
        await handler.start()
        return

    if action_type == 'conditional':
        await show_condition_picker(chatid, userid, lang, alt_id, action_cfg, dino, message_to_edit)


COND_EMOJIS = {
    'energy': '⚡',
    'eat': '🍕',
    'game': '🎮',
    'mood': '🥳',
    'heal': '❤️',
    'activity_end': '⏳'
}


async def show_condition_picker(chatid, userid, lang, alt_id, action_cfg, dino, message_to_edit: Message = None):
    aa = GAME_SETTINGS.get('auto_actions', {})
    available = aa.get('available_conditions', [])

    cond_btns = []
    for cond in available:
        emoji = COND_EMOJIS.get(cond, '')
        cond_name = t(f'dino_auto_actions.cond.{cond}', lang, default=cond)
        btn_text = f"{emoji} {cond_name}".strip()
        cond_btns.append({'text': btn_text, 'callback_data': f'daa_cond_pick {cond} {alt_id}'})

    rows = []
    from bot.modules.data_format import chunks
    for pair in chunks(cond_btns, 2):
        rows.append(pair)

    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append([{'text': cancel_text, 'callback_data': f'daa_main {alt_id}', 'style': 'danger'}])

    from bot.redismanager import redis_set
    import json
    await redis_set(f'daa_pending:{userid}', json.dumps({'action_cfg': action_cfg, 'alt_id': alt_id}), ex=300)
    markup = list_to_inline(rows, 2)
    text = t('dino_auto_actions.pick_condition', lang, default='Выберите условие:')
    await _edit_or_send_message(message_to_edit, chatid, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_cond_pick'))
async def daa_cond_pick(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    cond_stat, alt_id = parts[1], parts[2]

    from bot.redismanager import redis_get
    import json
    raw = await redis_get(f'daa_pending:{userid}')
    if not raw:
        await bot.send_message(callback.message.chat.id, t('css.error', lang, default='Ошибка. Попробуйте снова.'))
        return

    pending = json.loads(raw)
    action_cfg = pending.get('action_cfg', {})

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    if cond_stat == 'activity_end':
        condition = {'stat': 'activity_end'}
        doc = DinoAutoAction(
            dino_id=dino.id, owner_id=userid, action_type='conditional',
            action=action_cfg, condition=condition
        )
        await doc.insert()
        from bot.modules.get_state import get_state
        state = await get_state(userid, callback.message.chat.id)
        if state:
            data = await state.get_data()
            if prompt_id := data.get('daa_prompt_id'):
                try:
                    await bot.delete_message(callback.message.chat.id, prompt_id)
                except Exception:
                    pass
            await state.clear()
        from bot.modules.markup import markups_menu as m
        try:
            await bot.send_message(callback.message.chat.id, t('p_profile.return', lang, default='🔮 | Возвращение в главное меню!'), reply_markup=await m(userid, 'last_menu', lang))
        except Exception:
            pass
        await show_daa_main(callback.message.chat.id, userid, lang, alt_id, callback.message)
        return

    # 6 preset threshold buttons: 0, 15, 25, 50, 75, 100
    thresholds = [0, 15, 25, 50, 75, 100]
    thresh_btns = [
        {'text': f'{val}%', 'callback_data': f'daa_cond_thresh {val} {cond_stat} {alt_id}'}
        for val in thresholds
    ]
    rows = []
    from bot.modules.data_format import chunks
    for pair in chunks(thresh_btns, 3):
        rows.append(pair)

    cancel_text = t('buttons_name.cancel', lang, default='Отмена')
    rows.append([{'text': cancel_text, 'callback_data': f'daa_main {alt_id}', 'style': 'danger'}])

    markup = list_to_inline(rows, 3)
    stat_name = t(f'dino_auto_actions.cond.{cond_stat}', lang, default=cond_stat)
    stat_emoji = COND_EMOJIS.get(cond_stat, '')
    full_stat_name = f"{stat_emoji} {stat_name}".strip()

    text = t('dino_auto_actions.pick_threshold', lang,
              stat=full_stat_name,
              default=f'Выберите пороговое значение для <b>{full_stat_name}</b>:')
    await _edit_or_send_message(callback.message, callback.message.chat.id, text, markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_cond_thresh'))
async def daa_cond_thresh_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    if len(parts) < 4:
        return
    threshold = int(parts[1])
    cond_stat = parts[2]
    alt_id = parts[3]

    from bot.redismanager import redis_get
    import json
    raw = await redis_get(f'daa_pending:{userid}')
    if not raw:
        await bot.send_message(callback.message.chat.id, t('css.error', lang, default='Ошибка. Попробуйте снова.'))
        return

    pending = json.loads(raw)
    action_cfg = pending.get('action_cfg', {})

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    condition = {'stat': cond_stat, 'threshold': threshold, 'op': '<='}
    doc = DinoAutoAction(
        dino_id=dino.id, owner_id=userid,
        action_type='conditional', action=action_cfg, condition=condition
    )
    await doc.insert()

    from bot.modules.get_state import get_state
    state = await get_state(userid, callback.message.chat.id)
    if state:
        data = await state.get_data()
        if prompt_id := data.get('daa_prompt_id'):
            try:
                await bot.delete_message(callback.message.chat.id, prompt_id)
            except Exception:
                pass
        await state.clear()

    from bot.modules.markup import markups_menu as m
    try:
        await bot.send_message(callback.message.chat.id, t('p_profile.return', lang, default='🔮 | Возвращение в главное меню!'), reply_markup=await m(userid, 'last_menu', lang))
    except Exception:
        pass

    await show_daa_main(callback.message.chat.id, userid, lang, alt_id, callback.message)



@main_router.callback_query(IsPrivateChat(), F.data.startswith('daa_edit'))
async def daa_edit_callback(callback: CallbackQuery):
    await callback.answer()
    userid = callback.from_user.id
    lang = await get_lang(userid)
    parts = callback.data.split()
    action_type, idx_str, alt_id = parts[1], parts[2], parts[3]
    idx = int(idx_str)

    dino, is_owner = await _get_dino_and_owner(alt_id, userid)
    if not dino or not is_owner:
        return

    actions = await DinoAutoAction.get_for_dino(dino.id, action_type)
    if idx < len(actions):
        await actions[idx].delete()

    await show_action_type_picker(callback.message.chat.id, userid, lang, alt_id, action_type, dino.id, callback.message)
