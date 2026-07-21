from bot.models.dinosaur import Egg

from asyncio import sleep
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.get_state import get_state
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.models.dinosaur import Egg
from bot.modules.images import create_eggs_image
from bot.modules.inventory_tools import (InventoryStates, back_button, filter_items_data,
                                         filter_menu,
                                         forward_button, generate, search_menu,
                                         send_item_info, swipe_page, sort_menu)
from bot.modules.items.item import (CheckCountItemFromUser, CheckItemFromUser,
                              RemoveItemFromUser, counts_items, decode_item, get_item_dict, get_items_names, item_code)
from bot.dataclasess.ns_craft import NSmaterial
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import  get_name, get_emoji, get_emoji_html
from bot.modules.items.item_tools import (AddItemToUser, book_page,
                                     data_for_use_item,
                                    delete_item_action, exchange_item)
from bot.modules.items.time_craft import add_time_craft
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import count_markup, markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseIntHandler, ChooseInventoryHandler

from bot.models.user import User

from fuzzywuzzy import fuzz
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text
from bot.filters.states import NothingState
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.types import InputMediaPhoto

from bot.dbmanager import mongo_client


async def cancel(message):
    lang = await get_lang(message.from_user.id)
    await bot.send_message(message.chat.id, "❌", 
          reply_markup= await m(message.from_user.id, 'last_menu', lang))
    
    state = await get_state(message.from_user.id, message.chat.id)
    if state: await state.clear()

    from bot.modules.tutorial import advance_tutorial_if_step
    await advance_tutorial_if_step(message.from_user.id, message.chat.id, lang, bot, expected_step="profile_inventory")

@main_router.message(IsPrivateChat(), Text('commands_name.profile.inventory'), IsAuthorizedUser(), NothingState())
async def open_inventory(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await ChooseInventoryHandler(None, userid, chatid, lang).start()
    # Advance tutorial AFTER inventory is opened so tutorial message appears below
    from bot.modules.tutorial import advance_tutorial_if_step, update_pinned_message, get_tutorial_step
    await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="profile_top")
    # Also resend if already on profile_inventory step (re-opened)
    if await get_tutorial_step(userid) == "profile_inventory":
        await update_pinned_message(userid, chatid, "profile_inventory", lang, bot, resend=True)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('inventory_start'))
async def start_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    parts = call.data.split()
    type_filter = None
    if len(parts) > 1:
        type_filter = parts[1].split(',')

    await ChooseInventoryHandler(None, userid, chatid, lang, type_filter=type_filter).start()

@main_router.message(IsPrivateChat(), StateFilter(InventoryStates.Inventory), IsAuthorizedUser())
async def inventory(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    content = message.text

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        pages = data.get('pages')
        if pages is None:
            return
        items_data = data.get('items_data', {})
        page = data.get('settings', {}).get('page', 0)
        main_message = data.get('main_message', 0)
        settings = data.get('settings', {})

        function = data.get('function')
        transmitted_data = data.get('transmitted_data')
    else:
        return

    names = list(items_data.keys())

    matched_key = None
    if content in items_data:
        matched_key = content
    else:
        from bot.modules.data_format import parse_custom_emoji_markdown, remove_alt_emoji_from_text
        for key in items_data.keys():
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(key)
            if emoji_id:
                text_without_alt = remove_alt_emoji_from_text(clean_text, alt_emoji)
                if settings.get('is_premium', False):
                    if content in [clean_text, text_without_alt]:
                        matched_key = key
                        break
                else:
                    expected_text = f"{alt_emoji} {clean_text}" if alt_emoji else clean_text
                    if content in [expected_text, clean_text, text_without_alt]:
                        matched_key = key
                        break

    if content in [back_button, forward_button]:

        if content == back_button:
            if page == 0: page = len(pages) - 1
            else: page -= 1

        elif content == forward_button:
            if page >= len(pages) - 1: page = 0
            else: page += 1

        settings['page'] = page
        await state.update_data(settings=settings, main_message=0)

        await swipe_page(chatid, userid)
        await bot.delete_message(chatid, main_message)
        await bot.delete_message(chatid, message.message_id)

    elif matched_key:
        if 'inline_func' in settings:
            transmitted_data['inline_code'] = settings['inline_code'] 
            await ChooseInventoryHandler(**data).call_inline_func(items_data[matched_key], transmitted_data)
            # await settings['inline_func'](items_data[matched_key], transmitted_data)
        else:
            await ChooseInventoryHandler(**data).call_function(items_data[matched_key])
            # await function(items_data[matched_key], transmitted_data)
    else: await cancel(message)

@main_router.callback_query(IsPrivateChat(), StateFilter(InventoryStates.Inventory), 
                            F.data.startswith('inventory_menu'))
async def inv_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        changing_filter = data['settings']['changing_filters']
        sett = data['settings']
        items = data['items_data']
        meta_data = data.get('meta_data', {})

    if call_data == 'search' and changing_filter:
        # Активирует поиск
        if not ('delete_search' in data['settings'] and data['settings']['delete_search']):

            await state.set_state(InventoryStates.InventorySearch)
            await search_menu(chatid, userid)

    elif call_data == 'clear_search' and changing_filter:
        inv_sort = sett.get('inv_sort', 'name_asc')
        sort_key, direction = inv_sort.split('_')
        
        from bot.modules.inventory_tools import filter_and_sort_inventory
        raw_inventory = data.get('raw_inventory')
        if raw_inventory is None:
            from bot.models.user import User
            raw_inventory, _ = await User.get_inventory(userid, data.get('exclude_ids', []))
        filters = data['filters']
        sorted_items = filter_and_sort_inventory(raw_inventory, sett['lang'], filters, [], sort_key, direction, rare_emoji=sett.get('rare_emoji', True), only_emoji=sett.get('only_emoji', False), numbered=sett.get('only_emoji', False))
        
        view = sett['view']
        items_per_page = view[0] * view[1]
        from bot.modules.data_format import chunks
        virtual_pages = chunks(sorted_items, items_per_page)
        
        pages = [None] * len(virtual_pages)

        await state.update_data(items=[], pages=pages, virtual_pages=virtual_pages, items_data={}, meta_data={})
        await swipe_page(chatid, userid)

    elif call_data == 'filters' and changing_filter:
        # Активирует настройку филтров
        await state.set_state(InventoryStates.InventorySetFilters)
        await filter_menu(chatid)

    elif call_data == 'sort':
        # Открыть меню сортировки
        await sort_menu(chatid, userid)

    elif call_data in ['end_page', 'first_page']:
        # Быстрый переходи к 1-ой / полседней странице
        page = 0
        page_now = sett['page']
        if data := await state.get_data():
            pages = data['pages']

        if call_data == 'first_page': page = 0
        elif call_data == 'end_page': page = len(pages) - 1

        if page != page_now:
            data['settings']['page'] = page
            await state.update_data(settings=data['settings'])

            await swipe_page(chatid, userid)

    elif call_data == 'clear_filters' and changing_filter:
        inv_sort = sett.get('inv_sort', 'name_asc')
        sort_key, direction = inv_sort.split('_')
        
        from bot.modules.inventory_tools import filter_and_sort_inventory
        raw_inventory = data.get('raw_inventory')
        if raw_inventory is None:
            from bot.models.user import User
            raw_inventory, _ = await User.get_inventory(userid, data.get('exclude_ids', []))
        sorted_items = filter_and_sort_inventory(raw_inventory, sett['lang'], [], [], sort_key, direction, rare_emoji=sett.get('rare_emoji', True), only_emoji=sett.get('only_emoji', False), numbered=sett.get('only_emoji', False))
        
        view = sett['view']
        items_per_page = view[0] * view[1]
        from bot.modules.data_format import chunks
        virtual_pages = chunks(sorted_items, items_per_page)
        
        pages = [None] * len(virtual_pages)
        
        await state.update_data(items=[], pages=pages, filters=[], virtual_pages=virtual_pages, items_data={}, meta_data={})
        await swipe_page(chatid, userid)
    
    elif call_data == 'remessage':
        # Переотправка сообщения
        if data := await state.get_data():
            main_message = data['main_message']

        await state.update_data(main_message=0)

        await swipe_page(chatid, userid)
        await bot.delete_message(chatid, main_message)

async def render_priority_menu(call: CallbackQuery, item_base: dict, item_id: str, lang: str):
    from bot.modules.items.combat_properties import get_item_properties
    from bot.modules.inline import list_to_inline
    from bot.modules.items.item import get_name
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    if 'items_data' not in item_base:
        item = item_base
    else:
        item = item_base['items_data']
    
    props = get_item_properties(item)
    if not props:
        text = t("combat_properties.priority_menu.no_props", lang, default="❌ У этого предмета нет настраиваемых свойств.")
        back_btn = t("buttons_name.back", lang, default="↪️ Назад")
        markup = list_to_inline([{back_btn: f"item info {item_id}"}])
    else:
        lines = []
        abilities = item.get('abilities', {})
        skills_priority = abilities.get('skills_priority', {})
        
        for idx, (prop_id, prop_data) in enumerate(props):
            p_val = skills_priority.get(prop_id, t("combat_properties.priority_menu.random", lang, default="Random"))
            name_key = prop_data.get('name', prop_id)
            name = t(name_key, lang, default=prop_id)
            row_tpl = t("combat_properties.priority_menu.row", lang, formating=False, default="{index}. *{name}* (Приоритет: {priority})")
            lines.append(row_tpl.format(index=idx + 1, name=name, priority=p_val))
            
        list_str = "\n".join(lines)
        item_name = get_name(item['item_id'], lang, item.get('abilities', {}))
        
        title_tpl = t("combat_properties.priority_menu.title", lang, formating=False)
        text = title_tpl.format(name=item_name, list=list_str)
        
        markup_builder = InlineKeyboardBuilder()
        for idx, (prop_id, prop_data) in enumerate(props):
            name_key = prop_data.get('name', prop_id)
            name = t(name_key, lang, default=prop_id)
            btn_text = f"🔼 {name}"
            markup_builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"item pri_up {item_id} {prop_id}"))
            
        reset_text = t("combat_properties.buttons.clear_priority", lang, default="🗑 Сбросить приоритеты")
        back_text = t("buttons_name.back", lang, default="↪️ Назад")
        
        markup_builder.row(
            InlineKeyboardButton(text=reset_text, callback_data=f"item pri_reset {item_id}"),
            InlineKeyboardButton(text=back_text, callback_data=f"item properties {item_id}"),
            width=2
        )
        markup = markup_builder.as_markup()
        
    chatid = call.message.chat.id
    if getattr(call.message, 'photo', None):
        await bot.edit_message_caption(
            chat_id=chatid,
            message_id=call.message.message_id,
            caption=text,
            reply_markup=markup
        )
    else:
        await bot.edit_message_text(
            text=text,
            chat_id=chatid,
            message_id=call.message.message_id,
            reply_markup=markup
        )

@main_router.callback_query(IsPrivateChat(), F.data.startswith('item'))
async def item_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    item_id = call_data[2]
    preabil = {}

    item_base = await decode_item(item_id)
    if 'items_data' not in item_base:
        item = item_base
    else: item = item_base['items_data']

    if item:
        if call_data[1] == 'info':
            from bot.modules.items.item import item_info
            from bot.modules.inline import item_info_markup
            from bot.config import conf
            
            dev = userid in conf.bot_devs
            text, image = await item_info(item_base, lang, dev, html=True)
            
            recipe_code = None
            if len(call_data) > 3 and call_data[3].startswith("preview_"):
                recipe_code = call_data[3].replace("preview_", "")

            if recipe_code:
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                from aiogram.types import InlineKeyboardButton
                markup_builder = InlineKeyboardBuilder()
                back_text = t("buttons_name.back", lang, default="↪️ Назад")
                markup_builder.row(InlineKeyboardButton(text=back_text, callback_data=f"item info {recipe_code}"))
                markup = markup_builder.as_markup()
            else:
                markup = await item_info_markup(item_base, lang, userid)
            
            try:
                has_photo = bool(call.message.photo)
            except AttributeError:
                has_photo = False

            if has_photo:
                from bot.modules.images_save import edit_SmartPhoto
                photo_path = image if image else "images/remain/mulinv.png"
                await edit_SmartPhoto(chatid, call.message.message_id, photo_path, text, 'HTML', markup)
            else:
                await bot.edit_message_text(
                    text=text,
                    chat_id=chatid,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )
            
        elif call_data[1] == 'use':
            await data_for_use_item(item, userid, chatid, lang, item_base_id=item_base.get('_id'))
            
        elif call_data[1] == 'delete':
            await delete_item_action(userid, chatid, item, lang)
            
        elif call_data[1] == 'exchange':
            await exchange_item(userid, chatid, item, lang, 
                                 await User.get_user_name(userid))

        elif call_data[1] == 'lvl_effects':
            from bot.modules.items.combat_properties import format_level_preview_page
            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            page = int(call_data[3]) if len(call_data) > 3 and call_data[3].isdigit() else 0
            text, pages = format_level_preview_page(item_base, lang, page)
            back_btn_text = t("buttons_name.back", lang, default="↪️ Назад")

            markup_builder = InlineKeyboardBuilder()
            if pages > 1:
                prev_page = page - 1 if page > 0 else pages - 1
                next_page = page + 1 if page < pages - 1 else 0
                markup_builder.row(
                    InlineKeyboardButton(text="⬅️", callback_data=f"item lvl_effects {item_id} {prev_page}"),
                    InlineKeyboardButton(text="➡️", callback_data=f"item lvl_effects {item_id} {next_page}"),
                    width=2
                )
            markup_builder.row(InlineKeyboardButton(text=back_btn_text, callback_data=f"item info {item_id}"))
            markup = markup_builder.as_markup()
            
            if getattr(call.message, 'photo', None):
                await bot.edit_message_caption(
                    chat_id=chatid,
                    message_id=call.message.message_id,
                    caption=text,
                    reply_markup=markup
                )
            else:
                await bot.edit_message_text(
                    text=text,
                    chat_id=chatid,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )

        elif call_data[1] == 'properties':
            from bot.modules.items.combat_properties import format_all_properties_page
            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            page = int(call_data[3]) if len(call_data) > 3 and call_data[3].isdigit() else 0
            text, pages = format_all_properties_page(item, lang, page)
            if not text:
                text = t("combat_properties.priority_menu.no_props", lang, default="❌ У этого предмета нет настраиваемых свойств.")

            skills_priority_text = t("combat_properties.buttons.skills_priority", lang, default="⚙ Приоритет навыков")
            back_text = t("buttons_name.back", lang, default="↪️ Назад")

            markup_builder = InlineKeyboardBuilder()
            if pages > 1:
                prev_page = page - 1 if page > 0 else pages - 1
                next_page = page + 1 if page < pages - 1 else 0
                markup_builder.row(
                    InlineKeyboardButton(text="⬅️", callback_data=f"item properties {item_id} {prev_page}"),
                    InlineKeyboardButton(text="➡️", callback_data=f"item properties {item_id} {next_page}"),
                    width=2
                )
            if get_item_data(item['item_id']).get('properties'):
                markup_builder.row(
                    InlineKeyboardButton(text=skills_priority_text, callback_data=f"item skills_priority {item_id}")
                )
            markup_builder.row(
                InlineKeyboardButton(text=back_text, callback_data=f"item info {item_id}")
            )
            markup = markup_builder.as_markup()

            if getattr(call.message, 'photo', None):
                await bot.edit_message_caption(
                    chat_id=chatid,
                    message_id=call.message.message_id,
                    caption=text,
                    reply_markup=markup
                )
            else:
                await bot.edit_message_text(
                    text=text,
                    chat_id=chatid,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )

        elif call_data[1] == 'skills_priority':
            await render_priority_menu(call, item_base, item_id, lang)

        elif call_data[1] == 'dev_data':
            from bot.modules.items.item import get_data as get_item_data_raw
            raw_data = get_item_data_raw(item['item_id'])
            raw_text = f"<b>Item Document:</b>\n<code>{item_base}</code>\n\n<b>Item Static Config:</b>\n<code>{raw_data}</code>"
            if len(raw_text) > 4000:
                raw_text = raw_text[:4000] + "..."
            await bot.send_message(chatid, raw_text)
            await call.answer()
            
        elif call_data[1] == 'pri_up':
            from bot.modules.items.combat_properties import get_item_properties
            from bot.models.items import Item
            prop_id = call_data[3]
            props = get_item_properties(item)
            
            abilities = item.get('abilities', {})
            skills_priority = abilities.get('skills_priority', {})
            if not isinstance(skills_priority, dict):
                skills_priority = {}
            else:
                skills_priority = dict(skills_priority)
                
            sorted_props = sorted(props, key=lambda x: skills_priority.get(x[0], 9999))
            for i, (p_id, _) in enumerate(sorted_props):
                skills_priority[p_id] = i + 1
                
            prop_idx = -1
            for idx, (p_id, _) in enumerate(sorted_props):
                if p_id == prop_id:
                    prop_idx = idx
                    break
                    
            if prop_idx > 0:
                above_prop_id = sorted_props[prop_idx - 1][0]
                temp = skills_priority[prop_id]
                skills_priority[prop_id] = skills_priority[above_prop_id]
                skills_priority[above_prop_id] = temp
                
                if '_id' in item_base:
                    db_item = await Item.find_one(Item.id == item_base['_id'])
                    if db_item:
                        await db_item.update_skills_priority(skills_priority)
                elif item_id.startswith("it:"):
                    from bot.redismanager import redis_set
                    if 'items_data' not in item_base:
                        item_base['items_data'] = {}
                    if 'abilities' not in item_base['items_data']:
                        item_base['items_data']['abilities'] = {}
                    item_base['items_data']['abilities']['skills_priority'] = skills_priority
                    await redis_set(item_id, item_base, ex=86400)
                
                if 'items_data' not in item_base:
                    item_base['items_data'] = {}
                if 'abilities' not in item_base['items_data']:
                    item_base['items_data']['abilities'] = {}
                item_base['items_data']['abilities']['skills_priority'] = skills_priority
                
                prop_name = sorted_props[prop_idx][1].get('name', prop_id)
                translated_name = t(prop_name, lang, default=prop_name)
                alert_text = t("combat_properties.priority_menu.changed", lang, name=translated_name)
                await call.answer(alert_text)
            else:
                await call.answer()
                
            await render_priority_menu(call, item_base, item_id, lang)

        elif call_data[1] == 'pri_reset':
            from bot.models.items import Item
            db_item = await Item.find_one(Item.id == item_base['_id'])
            if db_item:
                await db_item.clear_skills_priority()
            
            if 'abilities' in item_base['items_data']:
                item_base['items_data']['abilities'].pop('skills_priority', None)
            
            alert_text = t("combat_properties.priority_menu.cleared", lang)
            await call.answer(alert_text)
            await render_priority_menu(call, item_base, item_id, lang)
            
        elif call_data[1] == 'egg':
            ret_data = await CheckItemFromUser(userid, item)
            if 'abilities' in item:
                preabil = item['abilities']

            if ret_data['status']:
                user = await User().create(userid)

                limit = await user.max_dino_col()
                limit_now = limit['standart']['limit'] - limit['standart']['now']
                
                if limit_now > 0:
                    egg_id = call_data[3]
                    item_data = get_item_data(item['item_id'])
                    end_time = seconds_to_str(item_data['incub_time'], lang)
                    i_name = get_name(item['item_id'], lang, item.get('abilities', {}))

                    if await RemoveItemFromUser(userid, item['item_id'], 1, preabil):
                        res = await Egg.incubation(int(egg_id), userid, item_data['incub_time'], item_data['inc_type'])

                        if res is None:
                            await call.message.delete()
                            await AddItemToUser(userid, item['item_id'], 1, preabil)
                            return

                        from bot.models.dinosaur import Dino
                        from bot.modules.managment.tracking import update_all_user_track
                        from bot.modules.notifications import user_notification
                        from time import time
                        
                        egg_doc = await Egg.find_one(Egg.owner_id == userid, Egg.stage == 'incubation', Egg.egg_id == int(egg_id))
                        if egg_doc and egg_doc.incubation_time <= int(time()):
                            # Hatch immediately atomically to prevent double hatching!
                            delete_result = await egg_doc.delete()
                            if delete_result and delete_result.deleted_count:
                                res_dino, alt_id = await Dino.insert_dino(userid, egg_doc.dino_id, egg_doc.quality)
                                await update_all_user_track(userid, 'gaming')
                                
                                await user_notification(userid, 
                                            'incubation_ready', lang, 
                                            user_name=user.name, dino_alt_id_markup=alt_id)
                                            
                                try:
                                    await call.message.delete()
                                except:
                                    pass
                        else:
                            await bot.send_message(chatid, 
                                t('item_use.egg.incubation', lang, 
                                item_name = i_name, end_time=end_time),  
                                reply_markup= await m(userid, 'last_menu', lang))

                            new_text = t('item_use.egg.edit_content', lang)
                            await bot.edit_message_caption(None, chat_id=chatid, message_id=call.message.message_id, 
                                        caption=new_text, reply_markup=None)
            else:
                await bot.send_message(chatid, 
                        t('item_use.cannot_be_used', lang),  
                          reply_markup= await m(userid, 'last_menu', lang))

        elif call_data[1] == 'egg_edit':
            from bot.modules.items.item import get_item_dict
            has_stone = await CheckItemFromUser(userid, get_item_dict('magic_stone'), 1)
            if not has_stone['status']:
                await call.answer(t('item_use.egg.no_magic_stone', lang), show_alert=True)
                return

            await call.message.delete_reply_markup()

            mag_stone = get_item_data('magic_stone')
            item_data = get_item_data(item['item_id'])

            preabil = mag_stone.get('abilities', {})
            if await RemoveItemFromUser(userid, 'magic_stone', 1, preabil):

                egg = await Egg.find_one(
                    Egg.owner_id == userid, 
                    Egg.stage == 'choosing',
                    Egg.quality == item_data['inc_type']
                )

                if egg:
                    old_eggs = list(egg.eggs)

                    egg.choose_eggs()
                    await egg.update({'$set': {
                                'eggs': egg.eggs,
                                'dinos': egg.dinos,
                                }}
                    )
                    
                    await call.message.edit_caption(
                        caption=t('item_use.egg.edit_eggs', lang)
                    )

                    for i in range(3):
                        old_eggs[i] = egg.eggs[i]
                        image = await create_eggs_image(old_eggs)

                        await call.message.edit_media(
                            media=InputMediaPhoto(
                                media=image,
                                caption=t('item_use.egg.edit_eggs', lang)
                            )
                        )
                        await sleep(2)

                    buttons = {}
                    code = await item_code(item_dict=item, userid=userid)

                    for i in range(3): 
                        buttons[f'🥚 {i+1}'] = (
                            f'item egg {code} {egg.eggs[i]}'
                    )

                    btn = {
                        t('item_use.egg.edit_buttons', lang):  f'item egg_edit {code}'
                    }

                    buttons = list_to_inline([btn, buttons])
                    await call.message.edit_caption(
                        caption=t('item_use.egg.egg_answer', lang),
                        reply_markup=buttons
                    )

                else:
                    await AddItemToUser(userid, mag_stone['item_id'], 1, preabil)
                    await call.message.delete()

            else: 
                await call.message.edit_caption(
                                       caption=t('item_use.egg.no_magic_stone', lang))

        elif call_data[1] == 'custom_book_read':

            if 'abilities' in item:
                if 'content' in item['abilities']:
                    content = item['abilities']['content']

                    await bot.send_message(chatid, content, reply_markup=list_to_inline([
                        {'🗑': 'delete_message'}]
                        )) 

        else: print('item_callback', call_data[1])

# Поиск внутри инвентаря
@main_router.callback_query(IsPrivateChat(), StateFilter(InventoryStates.InventorySearch), 
                            F.data.startswith('inventory_search'))
async def search_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    state = await get_state(userid, chatid)
    if call_data == 'close':
        # Данная функция не открывает новый инвентарь, а возвращает к меню
        await state.set_state(InventoryStates.Inventory)
        await swipe_page(chatid, userid)

@main_router.message(IsPrivateChat(), StateFilter(InventoryStates.InventorySearch), IsAuthorizedUser())
async def search_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    content = message.text
    searched = []

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        sett = data['settings']
        filters = data['filters']
        raw_inventory = data.get('raw_inventory')
        if raw_inventory is None:
            from bot.models.user import User
            raw_inventory, _ = await User.get_inventory(userid, data.get('exclude_ids', []))

    from bot.modules.items.item import get_name as get_item_name

    content_lower = content.lower()
    # Строим поиск напрямую из raw_inventory, а не из virtual_pages
    # чтобы повторный поиск всегда охватывал весь инвентарь
    for base_item in raw_inventory:
        item = base_item.get('items_data') or base_item.get('item', {})
        item_id = item.get('item_id')
        if not item_id:
            continue
        name = get_item_name(item_id, lang, item.get('abilities', {}))
        clean_lower = name.lower()

        tok_s = fuzz.token_sort_ratio(content_lower, clean_lower)
        ratio = fuzz.ratio(content_lower, clean_lower)
        all_find = fuzz.partial_ratio(content_lower, clean_lower)

        if (tok_s + ratio + all_find) // 3 >= 60 or content_lower in clean_lower:
            if item_id not in searched:
                searched.append(item_id)

    if searched:
        inv_sort = sett.get('inv_sort', 'name_asc')
        sort_key, direction = inv_sort.split('_')
        
        from bot.modules.inventory_tools import filter_and_sort_inventory
        sorted_items = filter_and_sort_inventory(raw_inventory, sett['lang'], filters, searched, sort_key, direction, rare_emoji=sett.get('rare_emoji', True), only_emoji=sett.get('only_emoji', False), numbered=sett.get('only_emoji', False))
        
        view = sett['view']
        items_per_page = view[0] * view[1]
        from bot.modules.data_format import chunks
        virtual_pages = chunks(sorted_items, items_per_page)
        
        pages = [None] * len(virtual_pages)

        await state.set_state(InventoryStates.Inventory)
        sett['page'] = 0
        await state.update_data(items=searched, pages=pages, virtual_pages=virtual_pages, settings=sett, items_data={}, meta_data={})

        await swipe_page(chatid, userid)
    else:
        await bot.send_message(userid, t('inventory.search_null', lang))


#Фильтры
@main_router.callback_query(IsPrivateChat(), StateFilter(InventoryStates.InventorySetFilters), 
                            F.data.startswith('inventory_filter'))
async def filter_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    lang = await get_lang(call.from_user.id)
    state = await get_state(userid, chatid)

    if call_data[1] == 'close':
        # Данная функция не открывает новый инвентарь, а возвращает к меню
        if data := await state.get_data():
            filters = data['filters']
            sett = data['settings']
            itm_fil = data['items']
            raw_inventory = data.get('raw_inventory')
            if raw_inventory is None:
                from bot.models.user import User
                raw_inventory, _ = await User.get_inventory(userid, data.get('exclude_ids', []))

        sett['page'] = 0
        await state.update_data(settings=sett)

        if 'edited_message' in sett:
            try:
                await bot.delete_message(chatid, sett['edited_message'])
            except: pass

        inv_sort = sett.get('inv_sort', 'name_asc')
        sort_key, direction = inv_sort.split('_')
        
        from bot.modules.inventory_tools import filter_and_sort_inventory
        sorted_items = filter_and_sort_inventory(raw_inventory, sett['lang'], filters, itm_fil, sort_key, direction, rare_emoji=sett.get('rare_emoji', True), only_emoji=sett.get('only_emoji', False), numbered=sett.get('only_emoji', False))
        
        view = sett['view']
        items_per_page = view[0] * view[1]
        from bot.modules.data_format import chunks
        virtual_pages = chunks(sorted_items, items_per_page)
        
        pages = [None] * len(virtual_pages)

        if not sorted_items:
            await state.update_data(filters=[])
            await bot.send_message(chatid, t('inventory.filter_null', lang))
            await state.set_state(InventoryStates.Inventory)
            sorted_items = filter_and_sort_inventory(raw_inventory, sett['lang'], [], itm_fil, sort_key, direction, rare_emoji=sett.get('rare_emoji', True), only_emoji=sett.get('only_emoji', False), numbered=sett.get('only_emoji', False))
            virtual_pages = chunks(sorted_items, items_per_page)
            pages = [None] * len(virtual_pages)
            await state.update_data(pages=pages, virtual_pages=virtual_pages, items_data={}, meta_data={})
            await swipe_page(chatid, userid)

        else:
            await state.set_state(InventoryStates.Inventory)
            await state.update_data(pages=pages, virtual_pages=virtual_pages, items_data={}, meta_data={})
            await swipe_page(chatid, userid)

    elif call_data[1] == 'toggle':
        if data := await state.get_data():
            filters = data.get('filters', []) or []
        itype = call_data[2]
        if itype in filters:
            filters.remove(itype)
        else:
            filters.append(itype)
        await state.update_data(filters=filters)
        await filter_menu(chatid, False)

    elif call_data[1] == 'clear':
        await state.update_data(filters=[])
        await filter_menu(chatid, False)

@main_router.callback_query(IsPrivateChat(), StateFilter(InventoryStates.Inventory), 
                            F.data.startswith('inventory_sort'))
async def inv_sort_callback(call: CallbackQuery):
    call_data = call.data.split()
    if len(call_data) < 2:
        return
    option = call_data[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    state = await get_state(userid, chatid)
    if option != 'cancel':
        if data := await state.get_data():
            sett = data['settings']
            itm_fil = data['items']
            filters = data['filters']
            raw_inventory = data.get('raw_inventory')
            if raw_inventory is None:
                from bot.models.user import User
                raw_inventory, _ = await User.get_inventory(userid, data.get('exclude_ids', []))

            sett['inv_sort'] = option
            sett['page'] = 0
            
            from bot.modules.inventory_tools import filter_and_sort_inventory
            sort_key, direction = option.split('_')
            sorted_items = filter_and_sort_inventory(raw_inventory, sett['lang'], filters, itm_fil, sort_key, direction, rare_emoji=sett.get('rare_emoji', True), only_emoji=sett.get('only_emoji', False), numbered=sett.get('only_emoji', False))
            
            view = sett['view']
            items_per_page = view[0] * view[1]
            from bot.modules.data_format import chunks
            virtual_pages = chunks(sorted_items, items_per_page)
            
            pages = [None] * len(virtual_pages)

            await state.update_data(settings=sett, pages=pages, virtual_pages=virtual_pages, items_data={}, meta_data={})

    await swipe_page(chatid, userid)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('book'))
async def book(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    book_id = call_data[1]
    page = int(call_data[2])
    text, markup = book_page(book_id, page, lang)
    try:
        await bot.edit_message_text(text, None, chatid, call.message.message_id, reply_markup=markup)
    except Exception as e: 
        log(message=f'Book edit error {e}', lvl=2)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('ns_craft'))
async def ns_craft(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_base = await decode_item(call_data[1])
    if 'items_data' not in item_base:
        item_ns = item_base
    else:
        item_ns = item_base['items_data']

    item = get_item_data(item_ns['item_id'])
    ns_id = call_data[2]

    from bot.modules.items.item import check_and_return_dif
    from bot.dataclasess.ns_craft import NSmaterial

    nd_data = item['ns_craft'][ns_id]
    materials = {}
    for i in nd_data['materials']: 
        if isinstance(i, str):
            materials[i] = materials.get(i, 0) + 1
        elif isinstance(i, (dict, NSmaterial)):
            item_i = i['item_id']
            count_i = i['count']
            materials[item_i] = materials.get(item_i, 0) + count_i

    max_crafts = 1000
    for key, value in materials.items():
        user_count = await check_and_return_dif(userid, key)
        max_crafts = min(max_crafts, user_count // value)

    if max_crafts == 0:
        await bot.send_message(chatid, t('ns_craft.not_materials', lang),
                           reply_markup = await m(userid, 'last_menu', lang))
        return

    max_crafts = min(max_crafts, 25)

    transmitted_data = {
        'item': item.model_dump() if hasattr(item, 'model_dump') else item,
        'ns_id': ns_id
    }
    await ChooseIntHandler(ns_end, userid, chatid, lang, max_int=max_crafts, autoanswer=False, transmitted_data=transmitted_data).start()
    
    await bot.send_message(chatid, t('css.wait_count', lang), 
                       reply_markup=count_markup(max_crafts, lang))


async def ns_end(count, transmitted_data: dict):

    userid = transmitted_data['userid']
    item = transmitted_data['item']
    ns_id = transmitted_data['ns_id']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    nd_data = item['ns_craft'][ns_id]
    materials = {}
    for i in nd_data['materials']: 
        if isinstance(i, str):
            materials[i] = materials.get(i, 0) + 1

        elif isinstance(i, (dict, NSmaterial)):
            item_i = i['item_id']
            count_i = i['count']

            materials[item_i] = materials.get(item_i, 0) + count_i

    for key, col in materials.items(): materials[key] = col * count

    check_lst = []
    for key, value in materials.items():
        item_data = get_item_dict(key)
        res = await CheckItemFromUser(userid, item_data, value)
        check_lst.append(res['status'])

    if all(check_lst):
        craft_list = []

        if 'time_craft' in item['ns_craft'][ns_id] and item['ns_craft'][ns_id]['time_craft'] > 0:

            for key, value in materials.items():
                await RemoveItemFromUser(userid, key, value)

            items_tcraft = []
            for iid in item['ns_craft'][ns_id]['create']:
                if isinstance(iid, (dict, NSmaterial)):
                    items_tcraft.append(
                        {'item': {
                            'item_id': iid['item_id'] 
                            },
                         'count': iid['count'] * count
                        }
                    )

                elif isinstance(iid, str):
                    items_tcraft.append(
                        {'item': {
                            'item_id': iid 
                            },
                         'count': 1 * count
                        }
                    )

            tt = item['ns_craft'][ns_id]['time_craft']
            tc = await add_time_craft(userid, 
                                 tt, 
                                 items_tcraft)
            text = t('time_craft.text_start', lang, 
                    items=get_items_names(items_tcraft, lang),
                    craft_time=seconds_to_str(tt, lang)
                    )
            markup = list_to_inline(
                [
                    {t('time_craft.button', lang): f"time_craft {tc['alt_code']}  send_dino"}
                ]
            )

            await bot.send_message(chatid, text, 
                           reply_markup = markup)

            text = t('time_craft.text2', lang,
                    command='/craftlist')
            markup = await m(userid, 'last_menu', lang)
            await bot.send_message(chatid, text, 
                            reply_markup = markup)
        
        else:
            for iid in item['ns_craft'][ns_id]['create']:
                if isinstance(iid, (dict, NSmaterial)):
                    item_i = iid['item_id']
                    count_i = iid['count']
                    craft_list.append(item_i)

                    await AddItemToUser(userid, item_i, count_i * count)

                elif isinstance(iid, str):
                    craft_list.append(iid)
                    await AddItemToUser(userid, iid, count)

            for key, value in materials.items():
                await RemoveItemFromUser(userid, key, value)

            text = t('ns_craft.create', lang, 
                    items = counts_items(craft_list, lang))
            await bot.send_message(chatid, text, 
                            reply_markup = await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('ns_craft.not_materials', lang),
                           reply_markup = await m(userid, 'last_menu', lang))

@main_router.callback_query(IsPrivateChat(), F.data.startswith('buyer'))
async def buyer(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_base = await decode_item(call_data[1])
    if 'items_data' not in item_base:
        item_decode = item_base
    else:
        item_decode = item_base['items_data']

    item = get_item_data(item_decode['item_id'])
    item_rank = item['rank']

    buyer_data = GAME_SETTINGS['buyer'][item_rank]
    one_col = buyer_data['one_col']
    
    if item.get('buyer_price') is not None:
        price = item['buyer_price']
    else:
        price = buyer_data['price']

    emoji = get_emoji_html(item_decode['item_id'])

    transmitted_data = {
        'item': item_decode,
        'one_col': one_col,
        'price': price
    }
    # await ChooseIntState(buyer_end, userid, chatid, lang, max_int=25, transmitted_data=transmitted_data)
    await ChooseIntHandler(buyer_end, userid, chatid, lang, max_int=25, transmitted_data=transmitted_data).start()

    await bot.send_message(chatid, t('buyer.choose', lang,
                                 emoji=emoji, one_col=one_col,
                                 price=price), 
                       reply_markup=count_markup(25, lang))


async def buyer_end(count, transmitted_data: dict):

    userid = transmitted_data['userid']
    item = transmitted_data['item']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    one_col = transmitted_data['one_col']
    price = transmitted_data['price'] * count

    if 'abilities' in item:
        preabil = item['abilities']
    else: preabil = {}

    need_col = one_col * count
    status = await CheckCountItemFromUser(userid, need_col, 
                                          item['item_id'], preabil.copy())

    if status:
        from bot.modules.overwriting.DataCalsses import Transaction
        async with Transaction():
            user = await User.find_one(User.userid == userid)
            if user:
                await user.remove_item(item['item_id'], need_col, preabil)
                await user.add_coins(price)
                if 'buyer_sell_count' not in user.settings:
                    user.settings['buyer_sell_count'] = 0
                if 'buyer_sell_total' not in user.settings:
                    user.settings['buyer_sell_total'] = 0
                user.settings['buyer_sell_count'] += need_col
                user.settings['buyer_sell_total'] += price
                await user.save()
                from bot.modules.user.achievements import check_achievements
                item_rarity = item.get('quality', item.get('rare', ''))
                await check_achievements(userid, "sell_buyer", {'count': need_col, 'rarity': item_rarity, 'coins': price})


        await bot.send_message(chatid, t('buyer.ok', lang), 
                           reply_markup=await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('buyer.no', lang), 
                           reply_markup=await m(userid, 'last_menu', lang))

@main_router.callback_query(IsPrivateChat(), StateFilter(InventoryStates.Inventory), IsAuthorizedUser(), 
                            F.data.startswith('inventoryinline'))
async def InventoryInline(callback: CallbackQuery):
    code = callback.data.split()
    chatid = callback.message.chat.id
    userid = callback.from_user.id

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        settings = data.get('settings')
        transmitted_data = data.get('transmitted_data')
        function = data.get('function')

    if not settings or not transmitted_data or not function:
        log(f'InventoryInline data corrupted', lvl=2, prefix='InventoryInline')
        return

    custom_code = settings.get('inline_code')

    code.pop(0)
    if code and code[0] == str(custom_code):
        code.pop(0)
        if len(code) == 1: 
            code: str = code[0]

        transmitted_data['temp'] = {}
        transmitted_data['temp']['message_data'] = callback.message

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            try:
                transmitted_data['steps'][transmitted_data['process']]['bmessageid'] = callback.message.message_id
            except Exception as e:
                import traceback
                log(f'Inline edit error: {e}\n{traceback.format_exc()}', lvl=2, prefix='InventoryInline')
        else: transmitted_data['bmessageid'] = callback.message.message_id

        item_base = await decode_item(code)
        if not item_base or 'items_data' not in item_base:
            lang = await get_lang(userid)
            try:
                await callback.answer(t('not_found_key', lang, default='Предмет не найден или устарел!'), show_alert=True)
            except Exception:
                pass
            return

        handler = ChooseInventoryHandler(**data)
        try:
            await handler.call_function(item_base['items_data'])
            # await function(item_base['items_data'], transmitted_data=transmitted_data)
        except Exception as e:
            import traceback
            log(f'InventoryInline error: {e}\n{traceback.format_exc()}', lvl=2, prefix='InventoryInline')
