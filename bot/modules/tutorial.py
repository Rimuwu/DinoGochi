"""
bot/modules/tutorial.py - Система обучения (онбординг) нового игрока.
"""
import asyncio
from typing import Optional

from bot.models.other import TutorialProgress
from bot.modules.localization import t
from bot.modules.logs import log

TUTORIAL_STEPS = [
    "egg_selected",
    "egg_incubation",
    "egg_boost",
    "dino_hatched",
    "dino_menu",
    "dino_menu_stats",
    "dino_menu_skills",
    "dino_menu_combat",
    "dino_menu_mood",
    "profile_menu_open",
    "profile_info",
    "profile_info_user",
    "profile_achievements",
    "profile_top",
    "profile_inventory",
    "actions_intro",
    "feed_wait",
    "collecting",
    "collecting_hint",
    "map_market",
    "tavern",
    "blacksmith",
    "done",
]

# Шаги, которые обновляются НА МЕСТЕ (resend=False) внутри одного раздела
IN_PLACE_STEPS = [
    "dino_menu_stats", "dino_menu_skills", "dino_menu_combat", "dino_menu_mood",
    "profile_achievements", "profile_inventory"
]


async def get_tutorial(userid: int) -> Optional[TutorialProgress]:
    """Возвращает активный прогресс обучения или None."""
    return await TutorialProgress.find_one(
        TutorialProgress.userid == userid,
        TutorialProgress.active == True  # noqa: E712
    )


async def is_tutorial_active(userid: int) -> bool:
    tut = await get_tutorial(userid)
    return tut is not None


async def get_tutorial_step(userid: int) -> Optional[str]:
    tut = await get_tutorial(userid)
    return tut.step if tut else None


async def create_tutorial(userid: int) -> TutorialProgress:
    """Создаёт запись обучения для нового игрока и выдаёт стартовые предметы."""
    # Гарантируем наличие стартовых предметов из settings.json
    try:
        from bot.const import GAME_SETTINGS
        from bot.models.items import Item
        starter = GAME_SETTINGS.get('starter_items', [])
        for s_item in starter:
            item_id = s_item.get('item_id')
            count = s_item.get('count', 1)
            abilities = s_item.get('abilities', {})
            if item_id:
                check = await Item.check_item(userid, {"item_id": item_id, "abilities": abilities}, count=1)
                if not check.get("status"):
                    await Item.add(userid, item_id, count, abilities)
    except Exception as e:
        log(prefix="tutorial", message=f"Error granting starter items: {e}", lvl=2)

    existing = await TutorialProgress.find_one(TutorialProgress.userid == userid)
    if existing:
        existing.active = True
        existing.step = "egg_selected"
        existing.pinned_message_id = None
        await existing.save()
        return existing
    tut = TutorialProgress(userid=userid)
    await tut.insert()
    return tut


def build_step_text(step: str, lang: str) -> str:
    return t(f"tutorial.steps.{step}", lang)


async def build_feed_step_text(userid: int, lang: str) -> str:
    """Динамический текст шага feed_wait — добавляет подсказку с реальным типом дино пользователя."""
    base = t("tutorial.steps.feed_wait", lang)
    try:
        from bot.modules.user.user import User
        from bot.models.dinosaur import Dino
        from bot.modules.items.item import get_name

        user = await User().create(userid)
        if not user:
            return base
        dino = await user.get_last_dino()
        if not dino:
            return base

        dino_data = Dino.get_dino_data(dino.data_id)
        dino_class = dino_data.get('class', '')

        CLASS_FOOD = {
            'Herbivore': ('grasses_from_fields', '🥦'),
            'Carnivore': ('wolf_meat', '🍖'),
            'Flying':    ('fish', '🪶'),
        }
        CLASS_LABEL = {
            'Herbivore': t('tutorial.dino_class.herbivore', lang, default='Травоядный'),
            'Carnivore': t('tutorial.dino_class.carnivore', lang, default='Хищник'),
            'Flying':    t('tutorial.dino_class.flying',    lang, default='Летающий'),
        }

        if dino_class in CLASS_FOOD:
            item_id, emoji = CLASS_FOOD[dino_class]
            food_name = get_name(item_id, lang)
            class_label = CLASS_LABEL[dino_class]
            dino_name = dino.name
            hint = t(
                'tutorial.feed_dino_hint', lang,
                dino_name=dino_name, dino_class=class_label,
                emoji=emoji, food_name=food_name,
                default=(
                    f'💡 <b>{dino_name}</b> — {class_label}.\n'
                    f'Накормите его: {emoji} <b>{food_name}</b>'
                )
            )
            # Replace existing <tg-spoiler> block if present, otherwise append
            if '<tg-spoiler>' in base:
                import re
                base = re.sub(
                    r'<tg-spoiler>.*?</tg-spoiler>',
                    f'<tg-spoiler>{hint}</tg-spoiler>',
                    base, flags=re.DOTALL
                )
            else:
                base = base + f'\n\n<tg-spoiler>{hint}</tg-spoiler>'
    except Exception as e:
        log(prefix="tutorial", message=f"build_feed_step_text error: {e}", lvl=2)
    return base


def build_step_markup(step: str, lang: str, active_step: Optional[str] = None):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    current_idx = TUTORIAL_STEPS.index(step) if step in TUTORIAL_STEPS else -1
    active = active_step or step

    # Кнопка «Назад» если есть предыдущий шаг (начиная с шага > 1)
    if current_idx > 1 and step != "done":
        prev_step = TUTORIAL_STEPS[current_idx - 1]
        builder.button(text=t("tutorial.back_button", lang), callback_data=f"tutorial_view {prev_step}")

    NEXT_BUTTON_STEPS = ["egg_selected", "dino_menu", "dino_menu_mood", "profile_inventory"]
    skip_btn_text = t("tutorial.next_button", lang) if step in NEXT_BUTTON_STEPS else t("tutorial.skip_button", lang)

    # Если смотрим прошлый шаг — кнопка «К текущему шагу», иначе — «Далее» / «Пропустить»
    if step != active and step != "done":
        builder.button(text=t("tutorial.active_step_button", lang), callback_data="tutorial_return_active")
    elif step != "done":
        builder.button(text=skip_btn_text, callback_data="tutorial_skip")

    builder.button(text=t("tutorial.stop_button", lang), callback_data="tutorial_stop")
    builder.adjust(2)
    return builder.as_markup()


async def update_pinned_message(
    userid: int, chatid: int, step: str, lang: str, bot, resend: bool = True
) -> None:
    """
    Отправляет новое сообщение обучения снизу и закрепляет его (при resend=True).
    При resend=False редактирует текущее закреплённое сообщение на месте.
    """
    tut = await get_tutorial(userid)
    if not tut:
        return

    if step == "feed_wait":
        text = await build_feed_step_text(userid, lang)
    else:
        text = build_step_text(step, lang)
    markup = build_step_markup(step, lang, active_step=step)

    if resend and tut.pinned_message_id:
        try:
            await bot.delete_message(chatid, tut.pinned_message_id)
        except Exception:
            try:
                await bot.unpin_chat_message(chatid, tut.pinned_message_id)
            except Exception:
                pass
        tut.pinned_message_id = None

    pinned_ok = False
    if not resend and tut.pinned_message_id:
        try:
            await bot.edit_message_text(
                text=text, chat_id=chatid, message_id=tut.pinned_message_id,
                parse_mode="HTML", reply_markup=markup,
            )
            pinned_ok = True
        except Exception:
            # Message may have been deleted — clear so fallback sends a new one
            tut.pinned_message_id = None
            await tut.save()


    if not pinned_ok:
        try:
            msg = await bot.send_message(chatid, text, parse_mode="HTML", reply_markup=markup)
            await tut.set_pinned(msg.message_id)
            try:
                await bot.pin_chat_message(chatid, msg.message_id, disable_notification=True)
            except Exception:
                pass
        except Exception as e:
            log(prefix="tutorial", message=f"Failed to send tutorial msg: {e}", lvl=2)


async def advance_tutorial(userid: int, chatid: int, lang: str, bot) -> bool:
    """Переходит к следующему шагу обучения. Возвращает True если обучение продолжается."""
    tut = await get_tutorial(userid)
    if not tut:
        return False
    current_idx = TUTORIAL_STEPS.index(tut.step) if tut.step in TUTORIAL_STEPS else -1
    next_idx = current_idx + 1
    if next_idx >= len(TUTORIAL_STEPS):
        await stop_tutorial(userid, chatid, bot, lang, completed=True)
        return False
    next_step = TUTORIAL_STEPS[next_idx]
    await tut.set_step(next_step)
    
    # Для подшагов внутри карточки/раздела обновляем на месте (resend=False), для новых сообщений отправляем снизу (resend=True)
    should_resend = next_step not in IN_PLACE_STEPS
    await update_pinned_message(userid, chatid, next_step, lang, bot, resend=should_resend)
    if next_step == "done":
        await stop_tutorial(userid, chatid, bot, lang, completed=True)
        return False
    return True


async def advance_tutorial_if_step(
    userid: int, chatid: int, lang: str, bot, expected_step: str
) -> bool:
    """Переходит к следующему шагу только если текущий == expected_step."""
    current = await get_tutorial_step(userid)
    if current == expected_step:
        return await advance_tutorial(userid, chatid, lang, bot)
    return False


async def stop_tutorial(
    userid: int, chatid: int, bot, lang: str, completed: bool = False
) -> None:
    """Останавливает обучение: открепляет сообщение и деактивирует прогресс."""
    tut = await get_tutorial(userid)
    if not tut:
        return
    final_key = "tutorial.steps.done" if completed else "tutorial.stopped"
    final_text = t(final_key, lang)

    final_markup = None
    if completed:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        from bot.const import GAME_SETTINGS
        from bot.modules.localization import get_data
        try:
            b1, b2 = get_data('start_command.request_subscribe.buttons', lang)
            final_markup_builder = InlineKeyboardBuilder()
            final_markup_builder.add(InlineKeyboardButton(text=b1, url=GAME_SETTINGS['bot_channel']))
            final_markup_builder.add(InlineKeyboardButton(text=b2, url=GAME_SETTINGS['bot_forum']))
            final_markup = final_markup_builder.as_markup()
        except Exception as e:
            log(prefix="tutorial", message=f"Failed to generate done final_markup: {e}", lvl=2)

    if tut.pinned_message_id:
        try:
            await bot.edit_message_text(
                text=final_text, chat_id=chatid, message_id=tut.pinned_message_id,
                parse_mode="HTML", reply_markup=final_markup,
            )
        except Exception:
            pass
        try:
            await bot.unpin_chat_message(chatid, tut.pinned_message_id)
        except Exception:
            pass
    await tut.deactivate()

