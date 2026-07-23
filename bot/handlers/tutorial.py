from aiogram import F, types
from aiogram.filters import Command

from bot.exec import bot, main_router
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.private import IsPrivateChat
from bot.modules.localization import get_lang, t
from bot.models.other import TutorialProgress
from bot.modules.tutorial import (
    advance_tutorial,
    build_step_markup,
    build_step_text,
    get_tutorial,
    stop_tutorial,
    update_pinned_message,
)


@main_router.message(F.pinned_message)
async def delete_pinned_service_message(message: types.Message) -> None:
    """Удаляет системное сообщение Telegram о закрепе."""
    try:
        await message.delete()
    except Exception:
        pass


@main_router.message(IsPrivateChat(), IsAuthorizedUser(), Command(commands=['tutorial']))
async def tutorial_resume_command(message: types.Message) -> None:
    """Возобновление или показ текущего шага обучения по команде /tutorial."""
    if not message.from_user:
        return
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)

    # Look for any existing record (active or not)
    existing = await TutorialProgress.find_one(TutorialProgress.userid == userid)
    if not existing:
        await message.answer(t('tutorial.no_tutorial', lang, default='❌ У вас нет активного обучения. Оно запускается автоматически при регистрации.'))
        return

    if not existing.active:
        # Reactivate
        existing.active = True
        await existing.save()

    await update_pinned_message(userid, chatid, existing.step, lang, bot, resend=True)


@main_router.callback_query(IsPrivateChat(), IsAuthorizedUser(), F.data == "tutorial_start")
async def tutorial_start_callback(call: types.CallbackQuery) -> None:
    """Запуск обучения по кнопке «Запустить обучение»."""
    if not call.from_user or not call.message:
        return
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)

    try:
        await call.message.delete()
    except Exception:
        pass

    tut = await get_tutorial(userid)
    if not tut:
        await call.answer()
        return

    next_step = "egg_incubation"
    await tut.set_step(next_step)

    from bot.modules.tutorial import update_pinned_message
    await update_pinned_message(userid, chatid, next_step, lang, bot, resend=True)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), IsAuthorizedUser(), F.data.startswith("tutorial_view"))
async def tutorial_view_callback(call: types.CallbackQuery) -> None:
    """Просмотр прошедшего шага без отправки нового сообщения (редактирование на месте)."""
    if not call.from_user or not call.message:
        return
    userid = call.from_user.id
    lang = await get_lang(userid)

    spl = call.data.split()
    target_step = spl[1] if len(spl) > 1 else "egg_incubation"

    tut = await get_tutorial(userid)
    if not tut:
        await call.answer()
        return

    text = build_step_text(target_step, lang)
    markup = build_step_markup(target_step, lang, active_step=tut.step)

    try:
        await call.message.edit_text(text, reply_markup=markup)
    except Exception:
        pass

    await call.answer()


@main_router.callback_query(IsPrivateChat(), IsAuthorizedUser(), F.data == "tutorial_return_active")
async def tutorial_return_active_callback(call: types.CallbackQuery) -> None:
    """Возврат к активному шагу обучения из истории просмотра."""
    if not call.from_user or not call.message:
        return
    userid = call.from_user.id
    lang = await get_lang(userid)

    tut = await get_tutorial(userid)
    if not tut:
        await call.answer()
        return

    text = build_step_text(tut.step, lang)
    markup = build_step_markup(tut.step, lang, active_step=tut.step)

    try:
        await call.message.edit_text(text, reply_markup=markup)
    except Exception:
        pass

    await call.answer()


@main_router.callback_query(IsPrivateChat(), IsAuthorizedUser(), F.data == "tutorial_skip")
async def tutorial_skip_callback(call: types.CallbackQuery) -> None:
    """Пропустить текущий шаг обучения."""
    if not call.from_user or not call.message:
        return
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)

    await advance_tutorial(userid, chatid, lang, bot)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), IsAuthorizedUser(), F.data == "tutorial_stop")
async def tutorial_stop_callback(call: types.CallbackQuery) -> None:
    """Остановить обучение."""
    if not call.from_user or not call.message:
        return
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)

    await stop_tutorial(userid, chatid, bot, lang, completed=False)
    await call.answer()
