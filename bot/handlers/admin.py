
from bot.models.user import Lang
from bot.models.other import Promo
from bot.models.user import User, Subscription
from bot.models.group import Group
from asyncio import sleep
from email import message
from time import time
from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, str_to_seconds, user_name_from_telegram
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log, latest_errors
from bot.models.other import Event
from bot.modules.markup import confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.managment.promo import (
    create_promo_start, get_promo_pages, promo_ui,use_promo)
from bot.modules.states_fabric.state_handlers import (ChooseConfirmHandler,
    ChoosePagesStateHandler, ChooseStringHandler)
from bot.modules.managment.tracking import creat_track, delete_track, get_track_pages, track_info

from aiogram.types import CallbackQuery, Message, BufferedInputFile

from bot.filters.private import IsPrivateChat
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command

@main_router.message(Command(commands=['create_tracking', 'create_track']), IsAdminUser())
async def create_tracking(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    # await ChooseStringState(create_track, userid, chatid, lang, 1, 0)
    await ChooseStringHandler(create_track, userid, chatid, lang, 1, 0).start()
    await bot.send_message(chatid, t("create_tracking.name", lang), parse_mode='Markdown')

async def create_track(code, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    await creat_track(code, 'admin')
    text, markup = await track_info(code, lang)
    
    await bot.send_message(chatid, text, parse_mode='html', reply_markup=markup)


@main_router.message(Command(commands=['create_all_packs']), IsAdminUser())
async def cmd_create_all_packs(message: Message):
    user_id = message.from_user.id
    chatid = message.chat.id
    
    await bot.send_message(chatid, "🚀 Запуск процесса создания паков динозавров и яиц в фоновом режиме...\n"
                                    "Это может занять очень много времени из-за лимитов Telegram.\n"
                                    "Прогресс будет отправляться в этот чат.")
    
    async def report_progress(text: str):
        try:
            await bot.send_message(chatid, f"📢 [Загрузка]: {text}")
        except Exception as e:
            print(f"Failed to send progress report to user: {e}")
            
    import asyncio
    from tools.emoji.upload_assets import upload_all
    asyncio.create_task(upload_all(bot, user_id, report_progress))


@main_router.message(Command(commands=['tracking']), IsAdminUser())
async def tracking(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = await get_track_pages()
    # res = await ChoosePagesState(track_info_adp, userid, chatid, lang, options, one_element=False, autoanswer=False)
    res = await ChoosePagesStateHandler(track_info_adp, userid, chatid, lang, options, one_element=False, autoanswer=False).start()
    await bot.send_message(chatid, t("track_open", lang), parse_mode='html')

async def track_info_adp(data, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, markup = await track_info(data, lang)
    try:
        await bot.send_message(chatid, text, parse_mode='html', reply_markup=markup)
    except:
        await bot.send_message(chatid, text, reply_markup=markup)

@main_router.callback_query(F.data.startswith('track'), IsPrivateChat())
async def track(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    code = split_d[2]

    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    from bot.dbmanager import mongo_client
    res = await mongo_client.dinogochi.management.find_one({'_id': 'tracking_links'})
    if res:
        text = '-'
        if action == 'delete':
            text = t("track_delete", lang)
            
            await delete_track(code)

        # elif action == 'view_users':
            
        # elif action == 'view_concern_links':

        # elif action == 'detailed_statistics':


        await bot.send_message(chatid, text)

@main_router.message(Command(commands=['create_promo']), IsAdminUser())
async def create_promo(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await create_promo_start(userid, chatid, lang)

@main_router.message(Command(commands=['promos']), IsAdminUser())
async def promos(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = await get_promo_pages()
    # res = await ChoosePagesState(promo_info_adp, userid, chatid, lang, options, 
    #                              one_element=False, autoanswer=False)
    res = await ChoosePagesStateHandler(promo_info_adp, userid, chatid, lang, options, 
                                   one_element=False, autoanswer=False).start()
    await bot.send_message(chatid, t("promo_commands.promo_open", lang), parse_mode='Markdown')

async def promo_info_adp(code, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, markup = await promo_ui(code, lang)
    await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

@main_router.callback_query(F.data.startswith('promo'))
async def promo_call(call: CallbackQuery):
    split_d = call.data.split()
    action = split_d[2]
    code = split_d[1]

    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    res = await Promo.find_one(Promo.code == code)
    if res:
        if action in ['activ', 'active', 'delete', 'clear_users'] and userid in conf.bot_devs:

            if action == 'delete': 
                await res.delete()
                await bot.delete_message(userid, call.message.message_id)

            elif action == 'clear_users':
                res.users = []
                await res.save()
                
                text, markup = await promo_ui(code, lang)
                await bot.edit_message_text(
                    text=text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )

            elif action in ['activ', 'active']:
                if not res.active:
                    res.active = True

                    if res.time != 'inf':
                        res.time_end = int(time()) + res.time

                    await res.save()

                else:
                    res.active = False
                    if res.time != 'inf':
                        try:
                            time_end_val = int(res.time_end)
                        except (ValueError, TypeError):
                            time_end_val = int(time())
                        res.time = time_end_val - int(time())

                    await res.save()

                text, markup = await promo_ui(code, lang)
                await bot.edit_message_text(
                    text=text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )

        elif action == 'use':
            status, text = await use_promo(code, userid, lang)
            await bot.send_message(userid, text, parse_mode='Markdown')
    else:
        await bot.send_message(userid, t('promo_commands.not_found', lang), parse_mode='Markdown')

@main_router.message(Command(commands=['link_promo']))
async def link_promo(message):
    user = message.from_user
    msg_args = message.text.split()
    lang = await get_lang(user.id)

    if user.id in conf.bot_devs:
        text_dict = get_data('promo_commands.link', lang)

        if len(msg_args) > 1:

            promo_code = msg_args[1]
            if len(msg_args) > 2:
                but_name = msg_args[2]
            else: but_name = '🎁'

            res = await Promo.find_one(Promo.code == promo_code)

            if res:

                fw = message.reply_to_message

                if fw != None:
                    fw_ms_id = fw.forward_from_message_id
                    fw_chat_id = fw.forward_from_chat.id
                    
                    but = {
                        but_name: f'promo_activ {promo_code} use'
                    }

                    markup_inline = list_to_inline([but])
                    await bot.edit_message_reply_markup(None, fw_chat_id, fw_ms_id, reply_markup=markup_inline)
                    await bot.send_message(user.id, text_dict['create'])

            else:
                await bot.send_message(user.id, text_dict['not_found'])

@main_router.message(Command(commands=['add_premium']), IsAdminUser())
async def add_premium(message):
    """
    Аргументы: /add_premium 0/userid None/str_time
    """
    msg_args = message.text.split()
    arg_list = msg_args[2:]

    tt = 'inf'
    if arg_list:
        tt = str_to_seconds(' '.join(arg_list))

    if msg_args[1] != '0':
        userid = int(msg_args[1])
    else: userid = message.from_user.id

    log(f'add_premium userid: {userid} time: {tt}', 4)

    await Subscription.award_premium(userid, tt)
    await bot.send_message(message.from_user.id, 'ok')

@main_router.message(Command(commands=['copy_m']), IsAdminUser())
async def copy_m(message: Message):

    """
    Аргументы: /copy_m lang
    """
    msg_args = message.text.split()
    arg_list = msg_args[1:]

    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)

    fw = message.reply_to_message
    try:
        fw_chat_id = fw.forward_from_chat.id
        fw_ms_id = fw.forward_from_message_id
    except:
        fw_chat_id = fw.chat.id
        fw_ms_id = fw.message_id

    fw_reply = fw.reply_markup.model_dump(exclude_none=True) if fw.reply_markup else None

    await bot.copy_message(chatid, fw_chat_id, fw_ms_id, reply_markup=fw_reply)

    trs_data = {
        'forward_chat': fw_chat_id,
        'forward_message': fw_ms_id,
        'markup': fw_reply,
        'to_lang': arg_list[0],
        'start_chat': chatid,
        'start_lang': lang
    }

    users_sends = await Lang.find(Lang.lang == arg_list[0]).to_list()

    # await ChooseConfirmState(confirm_send, userid, chatid, lang, True, trs_data)
    await ChooseConfirmHandler(confirm_send, userid, chatid, lang, True, trs_data).start()
    await bot.send_message(chatid, f"Confirm the newsletter for {len(users_sends)} users with language {arg_list[0]}", reply_markup=confirm_markup(lang))

@main_router.message(Command(commands=['copy_url']), IsAdminUser())
async def copy_url(message: Message):
    """
    Аргументы: /copy_url Button Text | URL
    """
    chatid = message.chat.id

    fw = message.reply_to_message
    if not fw:
        await bot.send_message(chatid, "Reply to a message to copy it.")
        return

    cmd, _, args = message.text.partition(" ")
    parts = [p.strip() for p in args.split('|')]
    if len(parts) < 2:
        await bot.send_message(chatid, "Syntax: /copy_url Button Text | URL")
        return

    button_text, url = parts[0], parts[1]

    try:
        fw_chat_id = fw.forward_from_chat.id
        fw_ms_id = fw.forward_from_message_id
    except:
        fw_chat_id = fw.chat.id
        fw_ms_id = fw.message_id

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, url=url)]
    ])

    await bot.copy_message(chatid, fw_chat_id, fw_ms_id, reply_markup=markup)

async def confirm_send(_, transmitted_data: dict):
    forward_chat = transmitted_data['forward_chat']
    forward_message = transmitted_data['forward_message']
    markup = transmitted_data['markup']
    to_lang = transmitted_data['to_lang']

    start_chat = transmitted_data['start_chat']
    start_lang = transmitted_data['start_lang']
    
    await bot.send_message(start_chat, f"🍡", reply_markup=await m(start_chat, 'last_menu', start_lang))

    users_sends = await Lang.find(Lang.lang == to_lang).to_list()
    start_time = time()
    col = 0

    from aiogram.exceptions import TelegramRetryAfter

    progress_msg = await bot.send_message(start_chat, f"📢 Starting newsletter to {len(users_sends)} users...")

    for user in users_sends:
        while True:
            try:
                await bot.copy_message(user['userid'], forward_chat, forward_message, reply_markup=markup)
                col += 1
                user_obj = await User.find_one(User.userid == user['userid'])
                if user_obj:
                    await user_obj.add_super_coins(20)
                await sleep(0.05)
                break
            except TelegramRetryAfter as e:
                await sleep(e.retry_after + 0.1)
            except Exception as e:
                log(f'[copy_m] error for user {user.get("userid")}: {e}', 2)
                break
        
        if col > 0 and col % 50 == 0:
            try:
                await bot.edit_message_text(
                    chat_id=start_chat,
                    message_id=progress_msg.message_id,
                    text=f"⏳ Progress: sent {col} / {len(users_sends)} messages..."
                )
            except Exception:
                pass

    try:
        await bot.delete_message(start_chat, progress_msg.message_id)
    except:
        pass

    await bot.send_message(start_chat, f"✅ Completed in {round(time() - start_time, 2)}s, sent to {col} / {len(users_sends)} users.")

@main_router.message(Command(commands=['eval']), IsAdminUser())
async def evaling(message):

    msg_args = message.text.split()
    msg_args.pop(0)
    text = ' '.join(msg_args)

    try:
        result = await eval(text)
    except TypeError:
        result = eval(text)

    log(f"userid: {message.from_user.id} command: {text} result: {result}", 4)
    try:
        await bot.send_message(message.from_user.id, str(result))
    except:
        await bot.send_message(message.from_user.id, 'moretext')

@main_router.message(Command(commands=['get_username']), IsAdminUser())
async def get_username(message):
    """
    Аргументы: /get_username userid
    """
    msg_args = message.text.split()

    try:
        chat_user = await bot.get_chat_member(msg_args[1], msg_args[1])
        user = chat_user.user
    except: user = None

    if user:
        await bot.send_message(message.from_user.id, user_name_from_telegram(user))
        await bot.send_message(message.from_user.id, str(user).replace("'", ''))
    else:
        await bot.send_message(message.from_user.id, "nouser")

@main_router.message(Command(commands=['log']), IsAdminUser())
async def get_log(message):
    errors_text = ''
    for i in range(len(latest_errors)): 
        s = f"{i+1}) ```{latest_errors[i]}```\n"
        if len(errors_text + s) > 4096: 
            break
        errors_text += s
    if not errors_text: errors_text = 'Ошибок нет, так держать!'
    
    await bot.send_message(message.chat.id, errors_text, parse_mode='Markdown')

@main_router.message(Command(commands=['save_users']), IsAdminUser())
async def save_users_handler(message: Message):
    cursor = await User.find_all().to_list()
    groups_s = await Group.find_all().to_list()

    with open("bot/data/users.txt", "w", encoding="utf-8") as f:
        for doc in cursor:
            f.write(str(doc.userid) + "\n")
        for doc in groups_s:
            f.write(str(doc.group_id) + "\n")

    await message.answer("User IDs saved.")

    with open("bot/data/users.txt", "rb") as f:
        await bot.send_document(message.chat.id, BufferedInputFile(f.read(), filename="users.txt"))

@main_router.message(Command(commands=['start_easter']), IsAdminUser())
async def start_easter(message: Message):

    time_end = int(time()) + 86400 * 1

    events_lst = []
    add_hunting = await Event.create_event_dict('add_hunting', time_end)
    add_hunting['data']['items'] = ['easter_egg']
    events_lst.append(add_hunting)

    add_fishing = await Event.create_event_dict('add_fishing', time_end)
    add_fishing['data']['items'] = ['easter_egg']
    events_lst.append(add_fishing)

    add_collecting = await Event.create_event_dict('add_collecting', time_end)
    add_collecting['data']['items'] = ['easter_egg']
    events_lst.append(add_collecting)

    add_all = await Event.create_event_dict('add_all', time_end)
    add_all['data']['items'] = ['easter_egg']
    events_lst.append(add_all)

    for i in events_lst: await Event.add_event(i, True)
    await bot.send_message(conf.bot_group_id, t("events.easter"))

@main_router.message(Command(commands=['count_items']), IsAdminUser())
async def count_items(message: Message):

    msg_args = message.text.split()
    msg_args.pop(0)
    item_id = ' '.join(msg_args)
    
    find_items = await mongo_client.items.items.find({"items_data.item_id": item_id}).to_list(length=None)
    count = 0
    max_count, max_id_user = 0, 0
    for i in find_items:
        count += i['count']
        if i['count'] > max_count:
            max_count = i['count']
            max_id_user = i['userid']
    
    await bot.send_message(message.chat.id, f"Count: {count}\nMax: {max_count} ({max_id_user})")

@main_router.message(Command(commands=['start_summer_event']), IsAdminUser())
async def start_summer_event(message: Message):

    time_end = int(time()) + 86400 * 2

    events_lst = []
    add_hunting = await Event.create_event_dict('add_hunting', time_end)
    add_hunting['data']['items'] = ['mysterious_egg']
    add_hunting['data']['special_chance']['mysterious_egg'] = 1
    events_lst.append(add_hunting)

    add_fishing = await Event.create_event_dict('add_fishing', time_end)
    add_fishing['data']['items'] = ['mysterious_egg']
    add_fishing['data']['special_chance']['mysterious_egg'] = 1
    events_lst.append(add_fishing)

    add_collecting = await Event.create_event_dict('add_collecting', time_end)
    add_collecting['data']['items'] = ['mysterious_egg']
    add_collecting['data']['special_chance']['mysterious_egg'] = 1
    events_lst.append(add_collecting)

    add_all = await Event.create_event_dict('add_all', time_end)
    add_all['data']['items'] = ['mysterious_egg']
    add_all['data']['special_chance']['mysterious_egg'] = 1
    events_lst.append(add_all)

    for i in events_lst: await Event.add_event(i, True)
    # await bot.send_message(conf.bot_group_id, t("events.easter"))


@main_router.message(Command(commands=['create_backup']),
                     IsAdminUser())
async def create_backup(message: Message):
    import os
    from bot.modules.bd_backup import create_mongo_dump, send_backup_to_topic

    connection_string = conf.mongo_url
    await bot.send_message(message.chat.id, "Creating backup...")
    s = create_mongo_dump(connection_string=connection_string)
    await bot.send_message(message.chat.id, f"Backup created. Filename: {s}")
    with open(s, 'rb') as f:
        file = BufferedInputFile(f.read(), filename=os.path.basename(s))
    await bot.send_document(message.chat.id, file)
    
    # Send to the configured backup topic
    await send_backup_to_topic(s)

@main_router.message(Command(commands=['give_quest']), IsAdminUser())
async def give_quest_command(message: Message):
    """
    Аргументы: /give_quest <quest_type> [complexity] [userid]
    """
    from bot.modules.quests import create_quest, save_quest
    
    userid = message.from_user.id
    lang = await get_lang(userid)
    msg_args = message.text.split()
    
    if len(msg_args) < 2:
        await message.answer(t("admin_commands.give_quest.usage", lang))
        return

    qtype = msg_args[1]
    valid_types = ['feed', 'collecting', 'fishing', 'journey', 'game', 'get', 'hunt', 'kill']
    if qtype not in valid_types:
        await message.answer(t("admin_commands.give_quest.invalid_type", lang, types=', '.join(valid_types)))
        return

    complexity = 1
    if len(msg_args) >= 3:
        try:
            complexity = int(msg_args[2])
            if not (1 <= complexity <= 5):
                await message.answer(t("admin_commands.give_quest.invalid_complexity", lang))
                return
        except ValueError:
            await message.answer(t("admin_commands.give_quest.invalid_complexity", lang))
            return

    target_userid = userid
    if len(msg_args) >= 4:
        try:
            target_userid = int(msg_args[3])
        except ValueError:
            await message.answer(t("admin_commands.give_quest.invalid_userid", lang))
            return

    target_lang = await get_lang(target_userid)
    quest = create_quest(complexity, qtype, lang=target_lang)
    if not quest:
        await message.answer(t("admin_commands.give_quest.creation_error", lang))
        return

    alt_id = await save_quest(quest, target_userid)
    await message.answer(t("admin_commands.give_quest.success", lang, userid=target_userid, alt_id=alt_id))


@main_router.message(Command(commands=['fill_inventory']), IsAdminUser())
async def cmd_fill_inventory(message: Message):
    """
    Usage: /fill_inventory <userid>
    Fills the target user's inventory with every item from ITEMS config (1300 count each).
    Total items: len(ITEMS) * 1300 ≈ 400 000+
    """
    from bot.modules.items.item import ITEMS
    from bot.models.items import Item

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /fill_inventory <userid>")
        return

    try:
        target_userid = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return

    count_per_item = 1300  # 315 items × 1300 ≈ 409 500 total

    await message.answer(
        f"🚀 Добавляю {len(ITEMS)} типов предметов по {count_per_item} штук "
        f"пользователю {target_userid}...\n"
        f"Итого: ~{len(ITEMS) * count_per_item:,} предметов"
    )

    db_items = [
        Item(
            owner=target_userid,
            items_data={"item_id": item_id},
            count=count_per_item
        )
        for item_id in ITEMS.keys()
    ]

    batch_size = 500
    inserted = 0
    for i in range(0, len(db_items), batch_size):
        batch = db_items[i:i + batch_size]
        await Item.insert_many(batch)
        inserted += len(batch)

    await message.answer(
        f"✅ Готово! Добавлено {inserted} видов предметов × {count_per_item} = "
        f"{inserted * count_per_item:,} штук пользователю {target_userid}"
    )


@main_router.message(Command(commands=['sync_stars', 'sync_donations']), IsAdminUser())
async def sync_stars_command(message: Message):
    chatid = message.chat.id
    await bot.send_message(chatid, "⏳ Начинаю получение транзакций Telegram Stars и синхронизацию с базой данных...")

    try:
        offset = 0
        limit = 1000
        total_fetched = 0
        total_added = 0
        errors = 0

        from bot.modules.donation import save_donation
        from bot.models.other import Donation
        from bot.const import GAME_SETTINGS
        from aiogram.types import TransactionPartnerUser

        while True:
            # Получаем список транзакций (в aiogram v3 возвращается StarTransactions)
            star_txs = await bot.get_star_transactions(offset=offset, limit=limit)
            if not star_txs or not star_txs.transactions:
                break
            
            transactions = star_txs.transactions
            total_fetched += len(transactions)

            for tx in transactions:
                # Нас интересуют только входящие транзакции (source populated) от пользователей
                if not tx.source or not isinstance(tx.source, TransactionPartnerUser):
                    continue

                donation_id = str(tx.id)
                # Проверяем, есть ли уже в базе транзакция с таким donation_id
                existing = await Donation.find_one(Donation.donation_id == donation_id)
                if existing:
                    continue

                # Данные транзакции
                userid = tx.source.user.id
                user_first_name = tx.source.user.first_name or "Unknown"
                amount = tx.amount

                # Конвертируем дату
                if isinstance(tx.date, int):
                    time_data = tx.date
                elif hasattr(tx.date, 'timestamp'):
                    time_data = int(tx.date.timestamp())
                else:
                    time_data = int(time())

                # Извлекаем payload
                payload = getattr(tx.source, "invoice_payload", None)
                product_key = None
                col = 1

                if payload:
                    message_split = payload.split('#')
                    product_key = message_split[0]
                    if len(message_split) > 1:
                        col_str = message_split[1]
                        if col_str == 'inf':
                            col = 'inf'
                        else:
                            try:
                                col = int(col_str)
                            except ValueError:
                                col = 1

                try:
                    # Добавляем в БД
                    await save_donation(
                        userid=userid,
                        user_first_name=user_first_name,
                        amount=amount,
                        product=product_key,
                        time_data=time_data,
                        col=col,
                        donation_id=donation_id
                    )
                    total_added += 1
                except Exception as e:
                    errors += 1
                    log(f"Ошибка при синхронизации транзакции {donation_id}: {e}", 3)

            if len(transactions) < limit:
                break
            offset += len(transactions)

        await message.answer(
            f"✅ Синхронизация завершена!\n\n"
            f"📊 Всего проверено транзакций: {total_fetched}\n"
            f"🆕 Добавлено новых донатов: {total_added}\n"
            f"⚠️ Ошибок обработки: {errors}"
        )

    except Exception as e:
        log(f"Критическая ошибка в sync_stars_command: {e}", 3)
        await message.answer(f"❌ Произошла ошибка во время синхронизации: {e}")


@main_router.message(Command(commands=['rollback_rewards']), IsAdminUser())
async def rollback_rewards_command(message: Message):
    chatid = message.chat.id
    await bot.send_message(chatid, "⏳ Начинаю точечный отзыв наград по жестко заданному списку...")

    try:
        import time
        import datetime
        from bot.models.other import Donation
        from bot.models.user import User, Subscription

        # 1. Жестко заданный список пользователей, получивших награду
        donation_users = [
            648711162, 1243731041, 1307230320, 1312219589, 1722940793, 1730502665, 1860735449, 1889725469, 1965895020,
            1976644441, 5006200869, 5086943830, 5157751444, 5650891670, 5781336547, 5800223486, 5941218050, 6181046931,
            6212296094, 6244045402, 6294748764, 6322007987, 6397447807, 6418023602, 6463440340, 6465579020, 6483326558,
            6488612857, 6590284377, 6641079326, 6691008410, 6696417940, 6778277921, 6836518858, 6848676575, 6921483498,
            6951227965, 6988382227, 7036081189, 7064329637, 7073089237, 7150879054, 7153903596, 7163952954, 7252011811,
            7325780955, 7579778554, 7826962255, 8055229089
        ]

        # 2. Жестко заданные награды для отзыва
        rewards_to_revoke = {
            648711162: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            1307230320: {"items": {"stone_resurrection": 1, "full_recovery_potion": 1}, "super_coins": 0},
            1312219589: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            1722940793: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            1889725469: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            1965895020: {"items": {"full_recovery_potion": 10}, "super_coins": 0},
            1976644441: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            5086943830: {"items": {"stone_resurrection": 2}, "super_coins": 0},
            5157751444: {"items": {"stone_resurrection": 2}, "super_coins": 0},
            5650891670: {"items": {"full_recovery_potion": 1, "stone_resurrection": 1}, "super_coins": 0},
            5781336547: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            5800223486: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            5941218050: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6212296094: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6294748764: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            6397447807: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6418023602: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6463440340: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            6465579020: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            6483326558: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6590284377: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            6778277921: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            6836518858: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6848676575: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            6921483498: {"items": {"stone_resurrection": 4}, "super_coins": 0},
            6951227965: {"items": {}, "super_coins": 300},
            6988382227: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            7036081189: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            7064329637: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            7073089237: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            7153903596: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            7252011811: {"items": {"stone_resurrection": 1}, "super_coins": 0},
            7579778554: {"items": {"stone_resurrection": 3}, "super_coins": 0},
            7826962255: {"items": {"full_recovery_potion": 1}, "super_coins": 0},
            8055229089: {"items": {"stone_resurrection": 1}, "super_coins": 0},
        }

        total_users = 0
        total_items_revoked = 0
        total_coins_revoked = 0
        total_subs_revoked = 0
        errors = 0

        # Исключаем транзакцию stxr04DHFQZPqctbmbONkRyA9xBrI3uVs_QHnmjXTWd-COhtaCcURRZ5UyoRnA1dJ7k9SHQS2clWUaY2Nrw8s4zeB1aE3_7QmrbmbBBrM-CtIU
        excluded_id = "stxr04DHFQZPqctbmbONkRyA9xBrI3uVs_QHnmjXTWd-COhtaCcURRZ5UyoRnA1dJ7k9SHQS2clWUaY2Nrw8s4zeB1aE3_7QmrbmbBBrM-CtIU"

        # 3. Производим откат
        for userid in donation_users:
            total_users += 1
            user_rewards = rewards_to_revoke.get(userid, {"items": {}, "super_coins": 0})
            
            # Отзываем предметы
            user = await User.find_one(User.userid == userid)
            if user:
                try:
                    for item_id, count in user_rewards["items"].items():
                        await user.remove_item(item_id, count)
                        total_items_revoked += count
                except Exception as e:
                    errors += 1
                    log(f"Ошибка при отзыве предметов у пользователя {userid}: {e}", 3)

                # Отзываем супер-монеты
                try:
                    if user_rewards["super_coins"] > 0:
                        await user.remove_super_coins(user_rewards["super_coins"])
                        total_coins_revoked += user_rewards["super_coins"]
                except Exception as e:
                    errors += 1
                    log(f"Ошибка при отзыве супер-монет у пользователя {userid}: {e}", 3)

            # Отзываем подписку (если была)
            try:
                sub = await Subscription.find_one(Subscription.userid == userid)
                if sub:
                    # Проверяем, что подписка создана сегодня (15 июля 2026) по её _id
                    created_today = sub.id.generation_time.date() == datetime.date(2026, 7, 15)
                    is_inf = isinstance(sub.sub_end, str) and sub.sub_end == "inf"

                    if not is_inf and created_today:
                        # Удаляем подписку полностью, так как она была создана сегодня
                        await sub.delete()
                        total_subs_revoked += 1

                # Сбрасываем флаг выданной награды для всех сегодняшних донатов пользователя
                user_donations = await Donation.find(
                    Donation.userid == userid,
                    Donation.issued_reward == True,
                    Donation.donation_id != excluded_id
                ).to_list()

                for donat in user_donations:
                    # Проверяем, что донат создан сегодня
                    donat_created_today = donat.id.generation_time.date() == datetime.date(2026, 7, 15)
                    if donat_created_today:
                        donat.issued_reward = False
                        await donat.save()

            except Exception as e:
                errors += 1
                log(f"Ошибка при обработке подписки/доната пользователя {userid}: {e}", 3)

        await message.answer(
            f"✅ Точечный отзыв наград завершен!\n\n"
            f"👥 Всего обработано пользователей: {total_users}\n"
            f"🎒 Отозвано предметов: {total_items_revoked}\n"
            f"🪙 Отозвано супер-монет: {total_coins_revoked}\n"
            f"📅 Отозвано подписок (не-inf, созданных сегодня): {total_subs_revoked}\n"
            f"⚠️ Ошибок: {errors}"
        )

    except Exception as e:
        log(f"Критическая ошибка в rollback_rewards_command: {e}", 3)
        await message.answer(f"❌ Произошла ошибка во время отзыва: {e}")