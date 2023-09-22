
from fuzzywuzzy import fuzz
from telebot.types import CallbackQuery, Message

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.data_format import seconds_to_str, user_name
from bot.modules.dinosaur import incubation_egg
from bot.modules.inventory_tools import (InventoryStates, back_button,
                                         filter_items_data, filter_menu,
                                         forward_button, generate,
                                         inventory_pages, search_menu,
                                         send_item_info, start_inv, swipe_page)
from bot.modules.item import (CheckItemFromUser, RemoveItemFromUser,
                              counts_items, decode_item)
from bot.modules.item import get_data as get_item_data
from bot.modules.item import get_item_dict, get_name
from bot.modules.item_tools import (AddItemToUser, CheckItemFromUser,
                                    book_page, data_for_use_item,
                                    delete_item_action, exchange_item)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.over_functions import send_message

async def cancel(message):
    lang = await get_lang(message.from_user.id)
    await send_message(message.chat.id, "❌", 
          reply_markup= await m(message.from_user.id, 'last_menu', lang))
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.reset_data(message.from_user.id,  message.chat.id)

@bot.message_handler(pass_bot=True, text='commands_name.profile.inventory', is_authorized=True, state=None)
async def open_inventory(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await start_inv(None, userid, chatid, lang)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('inventory_start'), private=True)
async def start_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    await start_inv(None, userid, chatid, lang)

@bot.message_handler(state=InventoryStates.Inventory, is_authorized=True)
async def inventory(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    content = message.text

    async with bot.retrieve_data(userid, chatid) as data:
        pages = data['pages']
        items_data = data['items_data']
        page = data['settings']['page']

        function = data['function']
        transmitted_data = data['transmitted_data']

    names = list(items_data.keys())

    if content == back_button:
        if page == 0: page = len(pages) - 1
        else: page -= 1

        async with bot.retrieve_data(userid, chatid) as data: data['settings']['page'] = page
        await swipe_page(userid, chatid)

    elif content == forward_button:
        if page >= len(pages) - 1: page = 0
        else: page += 1

        async with bot.retrieve_data(userid, chatid) as data: data['settings']['page'] = page
        await swipe_page(userid, chatid)

    elif content in names:
        await function(items_data[content], transmitted_data)
    else: await cancel(message)

@bot.callback_query_handler(pass_bot=True, state=InventoryStates.Inventory, func=lambda call: call.data.startswith('inventory_menu'), private=True)
async def inv_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    async with bot.retrieve_data(userid, chatid) as data:
        changing_filter = data['settings']['changing_filters']
        sett = data['settings']
        items = data['items_data']

    if call_data == 'search' and changing_filter:
        # Активирует поиск
        if not ('delete_search' in data['settings'] and data['settings']['delete_search']):
            await bot.set_state(userid, InventoryStates.InventorySearch, chatid)
            await search_menu(chatid, chatid)

    elif call_data == 'clear_search' and changing_filter:
        # Очищает поиск
        pages, _ = generate(items, *sett['view'])

        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
            data['items'] = []
        await swipe_page(userid, chatid)

    elif call_data == 'filters' and changing_filter:
        # Активирует настройку филтров
        await bot.set_state(userid, InventoryStates.InventorySetFilters, chatid)
        await filter_menu(chatid, chatid)

    elif call_data in ['end_page', 'first_page']:
        # Быстрый переходи к 1-ой / полседней странице
        page = 0
        async with bot.retrieve_data(userid, chatid) as data:
            pages = data['pages']

        if call_data == 'first_page': page = 0
        elif call_data == 'end_page': page = len(pages) - 1

        async with bot.retrieve_data(userid, chatid) as data: data['settings']['page'] = page
        await swipe_page(chatid, chatid)

    elif call_data == 'clear_filters' and changing_filter:
        # Очищает фильтры
        pages, _ = generate(items, *sett['view'])

        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
            data['filters'] = []
        await swipe_page(userid, chatid)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('item'), private=True)
async def item_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    item = decode_item(call_data[2])
    preabil = {}

    if item:
        if call_data[1] == 'info':
            await send_item_info(item, {'chatid': chatid, 'lang': lang}, False)
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
                egg_id = call_data[3]
                item_data = get_item_data(item['item_id'])
                end_time = seconds_to_str(item_data['incub_time'], lang)
                i_name = get_name(item['item_id'], lang)

                if await RemoveItemFromUser(userid, item['item_id'], 1, preabil):
                    await send_message(chatid, 
                        t('item_use.egg.incubation', lang, 
                          item_name = i_name, end_time=end_time),  
                          reply_markup= await m(userid, 'last_menu', lang))
                    
                    await incubation_egg(int(egg_id), userid, item_data['incub_time'], item_data['inc_type'])
                
                    new_text = t('item_use.egg.edit_content', lang)
                    await bot.edit_message_caption(new_text, chatid, call.message.id, reply_markup=None)
            else:
                await send_message(chatid, 
                        t('item_use.cannot_be_used', lang),  
                          reply_markup= await m(userid, 'last_menu', lang))
        else: print('item_callback', call_data[1])

# Поиск внутри инвентаря
@bot.callback_query_handler(pass_bot=True, state=InventoryStates.InventorySearch, 
                            func=lambda call: call.data.startswith('inventory_search'), private=True)
async def search_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    if call_data == 'close':
        # Данная функция не открывает новый инвентарь, а возвращает к меню
        await bot.set_state(userid, InventoryStates.Inventory, chatid)
        await swipe_page(userid, chatid)

@bot.message_handler(pass_bot=True, state=InventoryStates.InventorySearch, is_authorized=True)
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

        if tok_s >= 60 or ratio >= 60:
            item_id = items_data[item]['item_id']
            if item_id not in searched:
                searched.append(item_id)

    if searched:
        new_items = filter_items_data(items_data, item_filter=searched)
        pages, _ = generate(new_items, *sett['view'])

        await bot.set_state(userid, InventoryStates.Inventory, chatid)
        async with bot.retrieve_data(userid, chatid) as data: 
            data['pages'] = pages
            data['items'] = searched
        await swipe_page(userid, chatid)
    else:
        await send_message(chatid, t('inventory.search_null', lang))

#Фильтры
@bot.callback_query_handler(pass_bot=True, state=InventoryStates.InventorySetFilters, func=lambda call: call.data.startswith('inventory_filter'), private=True)
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

        if 'edited_message' in sett:
            await bot.delete_message(chatid, sett['edited_message'])

        new_items = filter_items_data(items, filters, itm_fil)
        pages, _ = generate(new_items, *sett['view'])

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
                await filter_menu(userid, chatid)
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

            await filter_menu(userid, chatid)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('book'), private=True)
async def book(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    book_id = call_data[1]
    page = int(call_data[2])
    text, markup = book_page(book_id, page, lang)
    try:
        await bot.edit_message_text(text, chatid, call.message.id, reply_markup=markup, parse_mode='Markdown')
    except: pass

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('ns_craft'), private=True)
async def ns_craft(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_ns = decode_item(call_data[1])
    item = get_item_data(item_ns['item_id'])
    ns_id = call_data[2]

    nd_data = item['ns_craft'][ns_id]
    materials = {}
    for i in nd_data['materials']: materials[i] = materials.get(i, 0) + 1

    check_lst = []
    for key, value in materials.items():
        item_data = get_item_dict(key)
        res = await CheckItemFromUser(userid, item_data, value)
        check_lst.append(res['status'])

    if all(check_lst):
        for iid in item['ns_craft'][ns_id]['create']:
            await AddItemToUser(userid, iid)

        for iid in item['ns_craft'][ns_id]['materials']:
            await RemoveItemFromUser(userid, iid)

        text = t('ns_craft.create', lang, 
                  items = counts_items(item['ns_craft'][ns_id]['create'], lang))
        await send_message(chatid, text)
    else:
        await send_message(chatid, t('ns_craft.not_materials', lang))