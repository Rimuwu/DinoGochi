
from asyncio import sleep

from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str, user_name
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import incubation_egg
from bot.modules.inventory_tools import (InventoryStates, back_button,
                                         filter_items_data, filter_menu,
                                         forward_button, generate, search_menu,
                                         send_item_info, start_inv, swipe_page)
from bot.modules.items.item import (CheckCountItemFromUser, CheckItemFromUser,
                              RemoveItemFromUser, counts_items, decode_item, get_items_names)
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_item_dict, get_name
from bot.modules.items.item_tools import (AddItemToUser, CheckItemFromUser,
                                    book_page, data_for_use_item,
                                    delete_item_action, exchange_item)
from bot.modules.items.time_craft import add_time_craft
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import count_markup, markups_menu
from bot.modules.markup import markups_menu as m
from bot.modules.states_tools import ChooseIntState
from bot.modules.user.user import User, take_coins
from fuzzywuzzy import fuzz
from aiogram.types import CallbackQuery, Message


async def cancel(message):
    lang = await get_lang(message.from_user.id)
    await bot.send_message(message.chat.id, "❌", 
          reply_markup= await m(message.from_user.id, 'last_menu', lang))
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.reset_data(message.from_user.id,  message.chat.id)

@bot.message(text='commands_name.profile.inventory', is_authorized=True, nothing_state=True, private=True)
@HDMessage
async def open_inventory(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await start_inv(None, userid, chatid, lang)

@bot.callback_query(func=lambda call: call.data.startswith('inventory_start'), private=True)
@HDCallback
async def start_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    await start_inv(None, userid, chatid, lang)

@bot.message(state=InventoryStates.Inventory, is_authorized=True, private=True)
@HDMessage
async def inventory(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    content = message.text

    async with bot.retrieve_data(userid, chatid) as data:
        pages = data['pages']
        items_data = data['items_data']
        page = data['settings']['page']
        main_message = data['main_message']
        settings = data['settings']

        function = data['function']
        transmitted_data = data['transmitted_data']

    names = list(items_data.keys())

    if content in [back_button, forward_button]:

        if content == back_button:
            if page == 0: page = len(pages) - 1
            else: page -= 1

        elif content == forward_button:
            if page >= len(pages) - 1: page = 0
            else: page += 1

        async with bot.retrieve_data(userid, chatid) as data: 
            data['settings']['page'] = page
            data['main_message'] = 0

        await swipe_page(userid, chatid)
        await bot.delete_message(chatid, main_message)
        await bot.delete_message(chatid, message.message_id)

    elif content in names:
        if 'inline_func' in settings:
            transmitted_data['inline_code'] = settings['inline_code'] 
            await settings['inline_func'](items_data[content], transmitted_data)
        else:
            await function(items_data[content], transmitted_data)
    else: await cancel(message)

@bot.callback_query(state=InventoryStates.Inventory, func=lambda call: call.data.startswith('inventory_menu'), private=True)
@HDCallback
async def inv_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    async with bot.retrieve_data(userid, chatid) as data:
        changing_filter = data['settings']['changing_filters']
        sett = data['settings']
        items = data['items_data']

    if call_data == 'search' and changing_filter:
        # Активирует поиск
        if not ('delete_search' in data['settings'] and data['settings']['delete_search']):
            await bot.set_state(userid, InventoryStates.InventorySearch, chatid)
            await search_menu(userid, chatid)

    elif call_data == 'clear_search' and changing_filter:
        # Очищает поиск
        pages, _ = await generate(items, *sett['view'])

        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
            data['items'] = []
        await swipe_page(userid, chatid)

    elif call_data == 'filters' and changing_filter:
        # Активирует настройку филтров
        await bot.set_state(userid, InventoryStates.InventorySetFilters, chatid)
        await filter_menu(userid, chatid)

    elif call_data in ['end_page', 'first_page']:
        # Быстрый переходи к 1-ой / полседней странице
        page = 0
        page_now = sett['page']
        async with bot.retrieve_data(userid, chatid) as data:
            pages = data['pages']

        if call_data == 'first_page': page = 0
        elif call_data == 'end_page': page = len(pages) - 1

        if page != page_now:
            async with bot.retrieve_data(userid, chatid) as data: data['settings']['page'] = page
            await swipe_page(userid, chatid)

    elif call_data == 'clear_filters' and changing_filter:
        # Очищает фильтры
        pages, _ = await generate(items, *sett['view'])

        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
            data['filters'] = []
        await swipe_page(userid, chatid)
    
    elif call_data == 'remessage':
        # Переотправка сообщения
        async with bot.retrieve_data(userid, chatid) as data: 
            main_message = data['main_message']

        async with bot.retrieve_data(userid, chatid) as data: 
            data['main_message'] = 0

        await swipe_page(userid, chatid)
        await bot.delete_message(chatid, main_message)

@bot.callback_query(func=lambda call: call.data.startswith('item'), private=True)
@HDCallback
async def item_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    item = decode_item(call_data[2])
    preabil = {}

    if item:
        if call_data[1] == 'info':
            await send_item_info(item, {'chatid': chatid, 'lang': lang, 'userid': userid}, False)
        elif call_data[1] == 'use':
            await data_for_use_item(item, userid, chatid, lang)
        elif call_data[1] == 'delete':
            await delete_item_action(userid, chatid, item, lang)
        elif call_data[1] == 'exchange':
            await exchange_item(userid, chatid, item, lang, 
                                user_name(call.from_user))
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
                        await bot.send_message(chatid, 
                            t('item_use.egg.incubation', lang, 
                            item_name = i_name, end_time=end_time),  
                            reply_markup= await m(userid, 'last_menu', lang))

                        await incubation_egg(int(egg_id), userid, item_data['incub_time'], item_data['inc_type'])

                        new_text = t('item_use.egg.edit_content', lang)
                        await bot.edit_message_caption(new_text, chatid, call.message.id, reply_markup=None)
            else:
                await bot.send_message(chatid, 
                        t('item_use.cannot_be_used', lang),  
                          reply_markup= await m(userid, 'last_menu', lang))
        else: print('item_callback', call_data[1])

# Поиск внутри инвентаря
@bot.callback_query(state=InventoryStates.InventorySearch, 
                            func=lambda call: call.data.startswith('inventory_search'), private=True)
@HDCallback
async def search_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    if call_data == 'close':
        # Данная функция не открывает новый инвентарь, а возвращает к меню
        await bot.set_state(userid, InventoryStates.Inventory, chatid)
        await swipe_page(userid, chatid)

@bot.message(state=InventoryStates.InventorySearch, is_authorized=True, private=True)
@HDMessage
async def search_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    content = message.text
    searched = []

    async with bot.retrieve_data(userid, chatid) as data:
        items_data = data['items_data']
        sett = data['settings']

    names = list(items_data.keys())

    for item in names:
        name = item[2:]
        tok_s = fuzz.token_sort_ratio(content, name)
        ratio = fuzz.ratio(content, name)
        all_find = fuzz.partial_ratio(content, name)

        if (tok_s + ratio + all_find) // 3 >= 60 or item == content:
            item_id = items_data[item]['item_id']
            if item_id not in searched: searched.append(item_id)

    if searched:
        new_items = filter_items_data(items_data, item_filter=searched)
        pages, _ = await generate(new_items, *sett['view'])

        await bot.set_state(userid, InventoryStates.Inventory, chatid)
        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
            data['settings']['page'] = 0
            data['items'] = searched
        await swipe_page(userid, chatid)
    else:
        await bot.send_message(userid, t('inventory.search_null', lang))

#Фильтры
@bot.callback_query(state=InventoryStates.InventorySetFilters, func=lambda call: call.data.startswith('inventory_filter'), private=True)
@HDCallback
async def filter_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    if call_data[1] == 'close':
        # Данная функция не открывает новый инвентарь, а возвращает к меню
        async with bot.retrieve_data(userid, chatid) as data:
            filters = data['filters']
            sett = data['settings']
            items = data['items_data']
            itm_fil = data['items']
            data['settings']['page'] = 0

        if 'edited_message' in sett:
            await bot.delete_message(chatid, sett['edited_message'])

        new_items = filter_items_data(items, filters, itm_fil)
        pages, _ = await generate(new_items, *sett['view'])

        await bot.set_state(userid, InventoryStates.Inventory, chatid)
        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
        await swipe_page(userid, chatid)

    elif call_data[1] == 'filter':
        async with bot.retrieve_data(userid, chatid) as data:
            filters = data['filters']

        filters_data = get_data('inventory.filters_data', lang)
        if call_data[2] == 'null':
            async with bot.retrieve_data(userid, chatid) as data:
                data['filters'] = []
            if filters:
                await filter_menu(userid, chatid, False)
        else:
            data_list_filters = filters_data[call_data[2]]['keys']

            if data_list_filters[0] in filters:
                for i in data_list_filters:
                    filters.remove(i)
            else:
                for i in data_list_filters:
                    filters.append(i)

            async with bot.retrieve_data(userid, chatid) as data:
                data['filters'] = filters

            await filter_menu(userid, chatid, False)

@bot.callback_query(func=lambda call: call.data.startswith('book'), private=True)
@HDCallback
async def book(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    book_id = call_data[1]
    page = int(call_data[2])
    text, markup = book_page(book_id, page, lang)
    try:
        await bot.edit_message_text(text, chatid, call.message.id, reply_markup=markup, parse_mode='Markdown')
    except Exception as e: 
        log(message=f'Book edit error {e}', lvl=2)

@bot.callback_query(func=lambda call: call.data.startswith('ns_craft'), private=True)
@HDCallback
async def ns_craft(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_ns = decode_item(call_data[1])
    item = get_item_data(item_ns['item_id'])
    ns_id = call_data[2]

    transmitted_data = {
        'item': item,
        'ns_id': ns_id
    }
    await ChooseIntState(ns_end, userid, chatid, lang, max_int=25, transmitted_data=transmitted_data)
    await bot.send_message(chatid, t('css.wait_count', lang), 
                       reply_markup=count_markup(25, lang))


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

        elif isinstance(i, dict):
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

        if 'time_craft' in item['ns_craft'][ns_id]:

            for key, value in materials.items():
                await RemoveItemFromUser(userid, key, value)

            items_tcraft = []
            for iid in item['ns_craft'][ns_id]['create']:
                if isinstance(iid, dict):
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

            await bot.send_message(chatid, text, parse_mode='Markdown', 
                           reply_markup = markup)

            text = t('time_craft.text2', lang,
                    command='/craftlist')
            markup = await markups_menu(userid, 'last_menu', lang)
            await bot.send_message(chatid, text, parse_mode='Markdown', 
                            reply_markup = markup)
        
        else:
            for iid in item['ns_craft'][ns_id]['create']:
                if isinstance(iid, dict):
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


@bot.callback_query(func=lambda call: call.data.startswith('buyer'), private=True)
@HDCallback
async def buyer(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_decode = decode_item(call_data[1])
    item = get_item_data(item_decode['item_id'])
    item_rank = item['rank']

    buyer_data = GAME_SETTINGS['buyer'][item_rank]
    one_col = buyer_data['one_col']
    price = buyer_data['price']
    emoji = get_name(item_decode['item_id'], lang)[0]

    transmitted_data = {
        'item': item_decode,
        'one_col': one_col,
        'price': price
    }
    await ChooseIntState(buyer_end, userid, chatid, lang, max_int=25, transmitted_data=transmitted_data)

    await bot.send_message(chatid, t('buyer.choose', lang,
                                 emoji=emoji, one_col=one_col,
                                 price=price), 
                       reply_markup=count_markup(25, lang),
                       parse_mode='Markdown')


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

        await RemoveItemFromUser(userid, item['item_id'], need_col, preabil)
        await take_coins(userid, price, True)

        await bot.send_message(chatid, t('buyer.ok', lang), 
                           reply_markup=await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('buyer.no', lang), 
                           reply_markup=await m(userid, 'last_menu', lang))


@bot.callback_query(state=InventoryStates.Inventory, is_authorized=True, func=lambda call: call.data.startswith('inventoryinline'))
@HDCallback
async def InventoryInline(callback: CallbackQuery):
    code = callback.data.split()
    chatid = callback.message.chat.id
    userid = callback.from_user.id

    async with bot.retrieve_data(userid, chatid) as data:
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
        if len(code) == 1: code = code[0]

        transmitted_data['temp'] = {}
        transmitted_data['temp']['message_data'] = callback.message

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            try:
                transmitted_data['steps'][transmitted_data['process']]['bmessageid'] = callback.message.id
            except Exception as e:
                log(f'Inline edit error {e}', lvl=2, prefix='InventoryInline')
        else: transmitted_data['bmessageid'] = callback.message.id
        del transmitted_data['inline_code']

        try:
            await function(decode_item(code), transmitted_data=transmitted_data)
        except Exception as e:
            log(f'InventoryInline error {e}', lvl=2, prefix='InventoryInline')
