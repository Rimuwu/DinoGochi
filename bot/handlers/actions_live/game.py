from bot.models.dinosaur import DinoMood, Dino
from random import randint
from time import time

from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.filters.status import DinoPassStatus
from bot.models.items import Item
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.models.dinosaur import Dino
from bot.models.activity import GameActivity
from bot.modules.user.friends import send_action_invite
from bot.modules.images import dino_game
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.quests import quest_process
from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import BaseUpdateType, InlineStepData, PagesStepData, StepMessage
from bot.modules.user.user import User, premium
from aiogram.types import Message, CallbackQuery

from bot.filters.translated_text import Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from aiogram import F

async def start_game_ent(userid: int, chatid: int, 
                         lang: str, dino: Dino,
                         friend: int = 0, join: bool = True, 
                         join_dino: str = ''):
    """ Запуск активности игра
        friend - id друга при наличии
        join - присоединяется ли человек к игре
    """
    transmitted_data = {
        'dino': dino._id, 
        'friend': friend, 'join': join,
        'join_dino': join_dino
    }

    # Создание первого выбора
    game_data = get_data('entertainments', lang)
    game_buttons, options = [], {}
    last_game = '-'
    need = ['console', 'snake', 'pin-pong', 'ball']

    if await Item.check_accessory(dino, 'board_games'):
        need += ["puzzles", "chess", "jenga", "dnd"]

    if await premium(userid):
        need += ["monopolia", "bowling", "darts", "golf"]

    for key, value in game_data['game'].items():
        if key in need:
            options[value] = key
            game_buttons.append(value)

    if dino.memory['games']:
        last = dino.memory['games'][0]
        last_game = t(f'entertainments.game.{last}', lang)

    # Второе сообщение
    buttons = {}
    cc = randint(1, 100)

    for key, value in get_data('entertainments.time', lang).items():
        buttons[value['text']] = f'chooseinline {cc} {key}'
    markup = list_to_inline([buttons])

    steps = [
        PagesStepData('game',
            StepMessage('entertainments.answer_game', translate_message=True, text_data={'last_game': last_game}),
            options=options
        ),
        BaseUpdateType(delete_markup),
        InlineStepData('time',
            StepMessage('entertainments.answer_text', translate_message=True,
                        markup=markup),
            delete_message=True,
            custom_code=str(cc)
        )
    ]

    await ChooseStepHandler(game_start, userid, chatid, lang, steps, 
                            transmitted_data
                        ).start()

async def delete_markup(transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text = t(f'entertainments.zero', lang)
    await bot.send_message(chatid, text, reply_markup=cancel_markup(lang))
    return transmitted_data, 0

async def game_start(return_data: dict, 
                     transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    dino_id = transmitted_data['dino']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    friend = transmitted_data['friend']
    join_status = transmitted_data['join']
    join_dino: str = transmitted_data['join_dino']
    friend_dino_id = 0

    game = return_data['game']
    code = return_data['time']

    res_dino_status = await dino.status
    if res_dino_status:
        if res_dino_status != 'pass':
            await bot.send_message(chatid, t('alredy_busy', lang), 
            reply_markup = await m(userid, 'last_menu', lang))
            return

    percent, repeat = await dino.memory_percent('games', game)
    percent_act, _1 = await dino.memory_percent('action', f'game.{game}', True)
    await DinoMood.repeat_activity(dino._id, percent_act)

    if friend and join_status and join_dino:
        dino_f = await Dino.find_one(Dino.alt_id == join_dino)
        if dino_f:
            friend_dino_id = dino_f.data_id
            res = await GameActivity.find_one(GameActivity.dino.id == dino_f.id)
            if not res: 
                join_dino = ''
                text_m = t('entertainments.join_end', lang)
                await bot.send_message(chatid, text_m)
            else: 
                percent += 0.5

                if res.game_percent < 2.0:
                    res.game_percent += 0.5
                    await res.save()

                await DinoMood.add(dino._id, 'playing_together', 1, 1800)
                await DinoMood.add(dino_f.id, 'playing_together', 1, 1800)

                from bot.models.user import DinoCollection
                await DinoCollection.add_to_collection(userid, dino_f.data_id)
                await DinoCollection.add_to_collection(friend, dino.data_id)

                text_m = t('entertainments.dino_join', lang, 
                            dinoname=dino.name)
                image = await dino_game(friend_dino_id, dino.data_id)
                await bot.send_photo(friend, image, caption = text_m)

    r_t = get_data('entertainments', lang)['time'][code]['data']
    game_time = randint(*r_t) * 60

    res = await DinoMood.check_inspiration(dino._id, 'game')
    if res: percent += 1.0

    await dino.game(game_time, percent)
    image = await dino_game(dino.data_id, friend_dino_id)

    text = t(f'entertainments.game_text.m{str(repeat)}', lang, 
            game=t(f'entertainments.game.{game}', lang)) + '\n'
    if percent < 1.0:
        text += t(f'entertainments.game_text.penalty', lang, percent=int(percent*100))

    message = await bot.send_photo(chatid, image, caption=text, 
                         reply_markup = await m(userid, 'last_menu', lang, True))

    # Пригласить друга
    if friend and not join_status:
        await send_action_invite(userid, friend, 'game', dino.alt_id, lang)
    elif not friend:
        text = t('entertainments.invite_friend.text', lang)
        button = t('entertainments.invite_friend.button', lang)
        markup = list_to_inline([
            {button: f'invite_to_action game {dino.alt_id}'}
        ])
        await bot.send_message(chatid, text, reply_markup=markup)

    await auto_ads(message)

async def build_game_send_keyboard(user: User, lang: str, page: int = 0):
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('game_global_draft', {})

    game_data = get_data('entertainments.game', lang)
    time_data = get_data('entertainments.time', lang)

    is_prem = await premium(user.userid)

    active_count = 0
    for dino in last_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_game = dino_draft.get('game')
        sel_time = dino_draft.get('time')
        if sel_game and sel_time:
            active_count += 1

    per_page = 1
    total_pages = max(1, (len(last_dinos) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    paged_dinos = last_dinos[page * per_page : (page + 1) * per_page]

    buttons = []

    for dino in paged_dinos:
        dino_draft = draft.get(dino.alt_id, {})
        sel_game = dino_draft.get('game')
        sel_time = dino_draft.get('time')

        dino_btn = {"text": f"🦕 {dino.name}", "callback_data": f"ggs_reset {dino.alt_id} {page}"}
        if not (sel_game and sel_time):
            dino_btn["style"] = "primary"
        buttons.append([dino_btn])

        need = ['console', 'snake', 'pin-pong', 'ball']
        if await Item.check_accessory(dino, 'board_games'):
            need += ["puzzles", "chess", "jenga", "dnd"]
        if is_prem:
            need += ["monopolia", "bowling", "darts", "golf"]

        game_row = []
        for g_key in need:
            g_label = game_data.get(g_key, g_key)
            g_btn = {"text": g_label, "callback_data": f"ggs_game {dino.alt_id} {g_key} {page}"}
            if sel_game == g_key:
                g_btn["style"] = "primary"
            game_row.append(g_btn)
            if len(game_row) == 2:
                buttons.append(game_row)
                game_row = []
        if game_row:
            buttons.append(game_row)

        if sel_game:
            time_row = []
            for t_key, t_val in time_data.items():
                t_label = t_val['text']
                t_btn = {"text": t_label, "callback_data": f"ggs_time {dino.alt_id} {t_key} {page}"}
                if sel_time == t_key:
                    t_btn["style"] = "primary"
                time_row.append(t_btn)
            buttons.append(time_row)

    buttons.append([{
        "text": t('entertainments.send_button', lang, count=active_count),
        "callback_data": "game_global_batch_send"
    }])

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"text": "⬅️", "callback_data": f"ggs_page {prev_p}"},
            {"text": f"{page + 1} / {total_pages}", "callback_data": "None"},
            {"text": "➡️", "callback_data": f"ggs_page {next_p}"}
        ]
        buttons.append(nav_row)

    return list_to_inline(buttons)

async def get_game_send_text(user: User, lang: str, page: int = 0) -> str:
    last_dinos = await user.get_last_dinos()
    if not last_dinos:
        return t('css.no_dino', lang)
    
    per_page = 1
    total_pages = max(1, (len(last_dinos) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    paged_dinos = last_dinos[page * per_page : (page + 1) * per_page]

    text = ""
    for dino in paged_dinos:
        last_game = '-'
        if dino.memory and 'games' in dino.memory and dino.memory['games']:
            last = dino.memory['games'][0]
            last_game = t(f'entertainments.game.{last}', lang)
        
        text += f"🦕 <b>{dino.name}</b> ({page + 1}/{total_pages})\n"
        text += t('entertainments.answer_game', lang, last_game=last_game) + "\n\n"
    
    return text.strip()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('ggs_reset'))
async def ggs_reset_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id = data[1]
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    if 'game_global_draft' in user.settings and dino_alt_id in user.settings['game_global_draft']:
        del user.settings['game_global_draft'][dino_alt_id]
        await user.save()

    inline = await build_game_send_keyboard(user, lang, page)
    text = await get_game_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('ggs_game'))
async def ggs_game_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, game_key = data[1], data[2]
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    if 'game_global_draft' not in user.settings:
        user.settings['game_global_draft'] = {}
    dino_draft = user.settings['game_global_draft'].get(dino_alt_id, {})
    dino_draft['game'] = game_key
    if not dino_draft.get('time'):
        dino_draft['time'] = 'sdj4'
    user.settings['game_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_game_send_keyboard(user, lang, page)
    text = await get_game_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('ggs_time'))
async def ggs_time_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    dino_alt_id, time_key = data[1], data[2]
    page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0

    if 'game_global_draft' not in user.settings:
        user.settings['game_global_draft'] = {}
    dino_draft = user.settings['game_global_draft'].get(dino_alt_id, {})
    dino_draft['time'] = time_key
    if not dino_draft.get('game'):
        dino_draft['game'] = 'console'
    user.settings['game_global_draft'][dino_alt_id] = dino_draft
    await user.save()

    inline = await build_game_send_keyboard(user, lang, page)
    text = await get_game_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('ggs_page'))
async def ggs_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()
    page = int(data[1])

    inline = await build_game_send_keyboard(user, lang, page)
    text = await get_game_send_text(user, lang, page)
    try:
        await call.message.edit_text(text, reply_markup=inline)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=inline)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'game_global_batch_send')
async def game_global_batch_send_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    chatid = call.message.chat.id

    draft = user.settings.get('game_global_draft', {})
    last_dinos = await user.get_last_dinos()

    to_send = []
    for dino in last_dinos:
        if dino.alt_id in draft:
            d_d = draft[dino.alt_id]
            if d_d.get('game') and d_d.get('time'):
                to_send.append((dino, d_d['game'], d_d['time']))

    if not to_send:
        await call.answer(t('works.no_dinos_selected', lang, default='⚠️ Не выбраны динозавры!'), show_alert=True)
        return

    await call.answer()

    reports = []
    for dino, game, code in to_send:
        d_status = await dino.status
        if d_status != 'pass':
            reports.append(t('css.busy_dino', lang, dino_name=dino.name))
            continue

        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            msg_txt = t('alredy_busy', lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n{msg_txt}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{msg_txt}</blockquote>")
            continue

        percent, repeat = await dino.memory_percent('games', game)
        percent_act, _1 = await dino.memory_percent('action', f'game.{game}', True)
        await DinoMood.repeat_activity(dino._id, percent_act)

        r_t = get_data('entertainments', lang)['time'][code]['data']
        game_time = randint(*r_t) * 60

        res = await DinoMood.check_inspiration(dino._id, 'game')
        if res: percent += 1.0

        await dino.game(game_time, percent)

        res_text = t(f'entertainments.game_text.m{str(repeat)}', lang, game=t(f'entertainments.game.{game}', lang))
        if percent < 1.0:
            res_text += '\n' + t('entertainments.game_text.penalty', lang, percent=int(percent*100))

        reports.append(f"🦕 <b>{dino.name}</b>:\n{res_text}" if len(to_send) == 1 else f"🦕 <b>{dino.name}</b>:\n<blockquote>{res_text}</blockquote>")

    user.settings['game_global_draft'] = {}
    await user.save()

    try:
        await bot.delete_message(userid, call.message.message_id)
    except Exception: pass

    full_text = "\n\n".join(reports)
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'live_actions_menu', lang, True))
    await auto_ads(mes)


@main_router.message(
    IsPrivateChat(), 
    Text('commands_name.actions.entertainments'), 
    DinoPassStatus()
)
async def entertainments(message: Message):
    userid = message.from_user.id # type: ignore
    lang = await get_lang(message.from_user.id) # type: ignore
    chatid = message.chat.id

    user = await User().create(userid)
    last_dinos = await user.get_last_dinos()

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if len(last_dinos) == 1:
        await start_game_ent(userid, chatid, lang, last_dinos[0])
    else:
        user.settings['game_global_draft'] = {}
        await user.save()

        from bot.modules.markup import cancel_markup
        inline = await build_game_send_keyboard(user, lang, 0)
        text = await get_game_send_text(user, lang, 0)
        await bot.send_message(chatid, t('commands_name.actions.entertainments', lang), reply_markup=cancel_markup(lang))
        await bot.send_message(chatid, text, reply_markup=inline)

async def get_game_progress_page(userid: int, lang: str, page: int | None = None):
    user = await User().create(userid)
    dinos = await user.get_dinos()

    game_dinos = []
    for dino in dinos:
        data = await GameActivity.find_one(
            GameActivity.dino.id == dino.id,
            GameActivity.activity_type == 'game'
        )
        if data:
            game_dinos.append((dino, data))

    if not game_dinos:
        return None, None

    total_pages = len(game_dinos)

    if page is None:
        last_dino = await user.get_last_dino()
        page = 0
        if last_dino:
            for idx, (dino, _) in enumerate(game_dinos):
                if dino.id == last_dino.id:
                    page = idx
                    break
    else:
        page = max(0, min(page, total_pages - 1))

    dino, data = game_dinos[page]

    game_key = dino.memory['games'][0] if (dino.memory and 'games' in dino.memory and dino.memory['games']) else None
    game_name = t(f'entertainments.game.{game_key}', lang) if game_key else '-'
    elapsed_seconds = max(0, int(time()) - data.start_time)
    time_str = seconds_to_str(elapsed_seconds, lang)

    text = f"🦕 <b>{dino.name}</b> ({page + 1}/{total_pages})\n\n"
    text += f"🎮 | {t('stop_game.playing', lang, default='Динозавр играет в')} <b>{game_name}</b> ({time_str})"

    buttons = []
    stop_button = t('buttons_name.stop_game', lang, default='❌ Остановить игру')
    buttons.append([{stop_button: f'stop_game_dino {dino.alt_id} {page}'}])

    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        nav_row = [
            {"⬅️": f"game_prog_page {prev_p}"},
            {f"{page + 1} / {total_pages}": "None"},
            {"➡️": f"game_prog_page {next_p}"}
        ]
        buttons.append(nav_row)

    markup = list_to_inline(buttons)
    return text, markup


@main_router.message(IsPrivateChat(), Text('commands_name.actions.stop_game'))
async def stop_game(message: Message):
    userid = message.from_user.id # type: ignore
    lang = await get_lang(message.from_user.id) # type: ignore
    chatid = message.chat.id

    text, markup = await get_game_progress_page(userid, lang)
    if not text:
        user = await User().create(userid)
        last_dino = await user.get_last_dino()
        if last_dino and await last_dino.status == 'game':
            from bot.models.enums import DinoStatus
            if randint(1, 2) == 1:
                await last_dino.set_status(DinoStatus.PASS)
                res_msg = t('stop_game.whatever', lang)
            else:
                res_msg = t('stop_game.dont_tear', lang)
            await bot.send_message(chatid, f"🦕 <b>{last_dino.name}</b>:\n{res_msg}", reply_markup=await m(userid, 'last_menu', lang, True))
        else:
            await bot.send_message(chatid, t('stop_game.no_games', lang, default='❌ Ни один из ваших динозавров не играет!'), reply_markup=await m(userid, 'last_menu', lang, True))
        return

    await bot.send_message(chatid, text, reply_markup=markup)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('game_prog_page'))
async def game_prog_page_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    data = call.data.split()
    page = int(data[1])

    text, markup = await get_game_progress_page(userid, lang, page)
    if text:
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('stop_game_dino'))
async def stop_game_dino_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    chatid = call.message.chat.id
    data = call.data.split()
    dino_alt_id = data[1]
    page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 0

    dino = await Dino.find_one(Dino.alt_id == dino_alt_id)
    if dino:
        penalties = GAME_SETTINGS['penalties']["games"]
        game_data = await GameActivity.find_one(
            GameActivity.dino.id == dino.id,
            GameActivity.activity_type == 'game'
        )
        random_tear, text = 1, ''
        res = await DinoMood.check_breakdown(dino._id, 'unrestrained_play')

        if not res:
            if game_data:
                game_data_dict = game_data.dict()
                if game_data_dict['game_percent'] == penalties['0']:
                    random_tear = randint(1, 2)
                elif game_data_dict['game_percent'] == penalties['1']:
                    random_tear = randint(1, 3)
                elif game_data_dict['game_percent'] == penalties['2']:
                    random_tear = randint(0, 2)
                elif game_data_dict['game_percent'] == penalties['3']:
                    random_tear = 0

                if randint(1, 2) == 1 or not random_tear:
                    if random_tear == 1:
                        text = t('stop_game.like', lang)
                        await DinoMood.add(dino._id, 'stop_game', randint(-2, -1), 3600)
                    elif random_tear == 0:
                        text = t('stop_game.dislike', lang)
                    else:
                        text = t('stop_game.whatever', lang)

                    await GameActivity.end(dino._id, False)
                    game_time = (int(time()) - game_data.start_time) // 60
                    await quest_process(userid, 'game', game_time)
                else:
                    text = t('stop_game.dont_tear', lang)

                await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n{text}")
            else:
                from bot.models.enums import DinoStatus
                if randint(1, 2) == 1:
                    if await dino.status == DinoStatus.GAME or await dino.status == 'game':
                        await dino.set_status(DinoStatus.PASS)
                    text = t('stop_game.whatever', lang)
                else:
                    text = t('stop_game.dont_tear', lang)
                await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n{text}")
        else:
            await bot.send_message(chatid, f"🦕 <b>{dino.name}</b>:\n" + t('stop_game.unrestrained_play', lang))

    next_text, next_markup = await get_game_progress_page(userid, lang, page)
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