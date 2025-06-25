
from asyncio import sleep
from typing import Union

from bson import ObjectId
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.get_state import get_state
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import Egg, incubation_egg
from bot.modules.images import create_eggs_image
from bot.modules.inventory.inventory_tools import (InventoryStates, 
                                         back_button, filter_items_data,
                                         filter_menu,
                                         forward_button, generate, inventory_pages, search_menu,
                                         send_item_info, sort_menu, swipe_page)
from bot.modules.items.item import (CheckItemFromUser, ItemData, ItemInBase,
                              RemoveItemFromUser, decode_item, AddItemToUser)
from bot.modules.items.custom_book import book_page
from bot.modules.items.ns_craft import ns_craft
from bot.modules.items.use_item import data_for_use_item
from bot.modules.items.exchange import exchange_item
from bot.modules.items.delete_item import delete_item_action
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import count_markup, markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseIntHandler, ChooseInventoryHandler
from bot.modules.items.json_item import Egg as EggType

from bot.modules.user.user import User, take_coins, user_name
from fuzzywuzzy import fuzz
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text
from bot.filters.states import NothingState
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.types import InputMediaPhoto

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.dbmanager import mongo_client

incubation = DBconstructor(mongo_client.dinosaur.incubation)


async def cancel(message):
    lang = await get_lang(message.from_user.id)
    await bot.send_message(message.chat.id, "❌", 
          reply_markup= await m(message.from_user.id, 'last_menu', lang))

    state = await get_state(message.from_user.id, message.chat.id)
    if state: await state.clear()

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.profile.inventory'), IsAuthorizedUser(), NothingState())
async def open_inventory(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await ChooseInventoryHandler(None, userid, chatid, lang, return_objectid=True).start()

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('inventory_start'))
async def start_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    await ChooseInventoryHandler(None, userid, chatid, lang, return_objectid=True).start()

@HDMessage
@main_router.message(
    IsPrivateChat(), 
    StateFilter(InventoryStates.Inventory), 
    IsAuthorizedUser()
)
async def inventory(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    content = message.text

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        pages = data['pages']
        items_data = data['items_data']
        page = data['settings']['page']
        main_message = data['main_message']
        settings = data['settings']

        transmitted_data = data['transmitted_data']

    names = list(items_data.keys())

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

    elif content in names:
        if 'inline_func' in settings:
            transmitted_data['inline_code'] = settings['inline_code'] 
            await ChooseInventoryHandler(**data).call_inline_func(items_data[content], transmitted_data)
        else:
            await ChooseInventoryHandler(**data).call_function(items_data[content])
    else: await cancel(message)

@HDCallback
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

    if call_data == 'search' and changing_filter:
        # Активирует поиск
        if not ('delete_search' in data['settings'] and data['settings']['delete_search']):

            await state.set_state(InventoryStates.InventorySearch)
            await search_menu(chatid, userid)

    elif call_data == 'clear_search' and changing_filter:
        # Очищает поиск
        pages, _ = await generate(items, *sett['view'])

        await state.update_data(items=[], pages=pages)
        await swipe_page(chatid, userid)

    elif call_data == 'filters' and changing_filter:
        # Активирует настройку филтров
        await state.set_state(InventoryStates.InventorySetFilters)
        await filter_menu(chatid)

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
        # Очищает фильтры
        pages, _ = await generate(items, *sett['view'])

        await state.update_data(items=[], pages=pages, filters=[])
        await swipe_page(chatid, userid)
    
    elif call_data == 'remessage':
        # Переотправка сообщения
        if data := await state.get_data():
            main_message = data['main_message']

        await state.update_data(main_message=0)

        await swipe_page(chatid, userid)
        await bot.delete_message(chatid, main_message)

    elif call_data == 'sort':
        await state.set_state(InventoryStates.InventorySort)
        await sort_menu(chatid)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('item'))
async def item_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    lang = await get_lang(call.from_user.id)
    item_id = call_data[2]

    item_base = await decode_item(item_id)
    if isinstance(item_base, ItemInBase):
        item = item_base

    elif isinstance(item_base, ItemData):
        item = ItemInBase(userid, 
                          item_base.item_id, item_base.abilities)
        await item.link_yourself()

    if item:
        if call_data[1] == 'info':
            await send_item_info(item, 
                {'chatid': chatid, 'lang': lang, 
                 'userid': userid}, False)

        elif call_data[1] == 'use':
            if item._id:
                await data_for_use_item(item._id, userid, 
                                        chatid, lang)

        elif call_data[1] == 'delete':
            if item._id:
                await delete_item_action(userid, chatid, item._id, lang)

        elif call_data[1] == 'exchange':
            if item._id:
                await exchange_item(userid, chatid, item._id, lang, 
                                    await user_name(userid))

        elif call_data[1] == 'egg' and \
                isinstance(item.items_data.data, EggType):
            ret_data = await CheckItemFromUser(userid, 
                                item.item_id,
                                item.items_data.abilities, 1)

            if ret_data['status']:
                user = await User().create(userid)

                limit = await user.max_dino_col()
                limit_now = limit['standart']['limit'] - limit['standart']['now']

                if limit_now > 0:
                    egg_id = call_data[3]
                    end_time = seconds_to_str(
                        item.items_data.data.incub_time, lang)
                    i_name = item.items_data.name

                    if await item.minus(1):
                        await bot.send_message(chatid, 
                            t('item_use.egg.incubation', lang, 
                            item_name = i_name, end_time=end_time),  
                            reply_markup = await m(userid, 'last_menu', lang))

                        res = await incubation_egg(int(egg_id), userid, 
                                                   item.items_data.data.incub_time, 
                                                   item.items_data.data.inc_type)

                        if res is None:
                            await call.message.delete()
                            await item.add_to_db()
                            return

                        new_text = t('item_use.egg.edit_content', lang)
                        await bot.edit_message_caption(None, chat_id=chatid, message_id=call.message.message_id, 
                                    caption=new_text, reply_markup=None)
            else:
                await bot.send_message(chatid, 
                        t('item_use.cannot_be_used', lang),  
                          reply_markup= await m(userid, 'last_menu', lang))

        elif call_data[1] == 'egg_edit' and \
                isinstance(item.items_data.data, EggType):
            await call.message.delete_reply_markup()

            mag_stone = ItemData('magic_stone')

            if await RemoveItemFromUser(userid, mag_stone, 1):

                res_egg_choose = await incubation.find_one({
                    'owner_id': userid, 
                    'stage': 'choosing',
                    'quality': item.items_data.data.inc_type,
                })

                if res_egg_choose:
                    old_eggs = res_egg_choose['eggs']

                    egg = Egg()
                    egg.__dict__.update(res_egg_choose)
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
                    code = item.code()

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
                    await AddItemToUser(userid, mag_stone, 1)
                    await call.message.delete()

            else: 
                await call.message.edit_caption(
                                       caption=t('item_use.egg.no_magic_stone', lang))

        elif call_data[1] == 'custom_book_read':

            if item.items_data.abilities:
                if 'content' in item.items_data.abilities:
                    content = item.items_data.abilities['content']

                    await bot.send_message(chatid, content, reply_markup=list_to_inline([
                        {'🗑': 'delete_message'}]
                        )) 

        else: print('item_callback', call_data[1])

# Поиск внутри инвентаря
@HDCallback
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

# Поиск внутри инвентаря
@HDCallback
@main_router.callback_query(IsPrivateChat(), 
                            StateFilter(InventoryStates.InventorySort), 
                            F.data.startswith('inventory_sort'))
async def sort_callback(call: CallbackQuery):
    call_data = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id

    state = await get_state(userid, chatid)
    lang = await get_lang(call.from_user.id)
    if call_data == 'close':

        if data := await state.get_data():
            settings = data['settings']
            items_data: list[Union[dict, ObjectId]] = data['items_data']
            filters = data['filters']
            items = data['items']

        new_inv: list[ItemInBase] = []
        for key, item in items_data.items():
            if isinstance(item, ObjectId):
                item_data = await ItemInBase().link_for_id(item)
                new_inv.append(item_data)
            else:
                item_data = await ItemInBase().link(userid, **item,
                                 location_type=settings['location_type'],
                                 location_link=settings['location_link']
                                 )
                new_inv.append(item_data)

        new_items_data = await inventory_pages(new_inv, lang, 
                                        filters, items,
                                        settings['sort_type'],
                                        settings['sort_up'],
                                        settings['return_objectid']
                )

        pages, _ = await generate(new_items_data, 
                                  *settings['view'])

        await state.update_data(items_data=new_items_data,
                                pages=pages, 
                                settings=settings)

        await state.set_state(InventoryStates.Inventory)
        await swipe_page(chatid, userid)

    elif call_data == 'filter':
        
        if data := await state.get_data():
            settings = data['settings']
            settings['sort_type'] = call.data.split()[2]

        await state.update_data(settings=settings)
        await sort_menu(chatid, True)

    elif call_data == 'filter_up':

        if data := await state.get_data():
            settings = data['settings']
            settings['sort_up'] = call.data.split()[2] == 'up'

        await state.update_data(settings=settings)
        await sort_menu(chatid, True)


@HDMessage
@main_router.message(
    IsPrivateChat(), 
    StateFilter(InventoryStates.InventorySearch), 
    IsAuthorizedUser())
async def search_message(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    content = message.text
    searched = []

    state = await get_state(userid, chatid)
    if data := await state.get_data():
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
        new_items = await filter_items_data(items_data, item_filter=searched)
        pages, _ = await generate(new_items, *sett['view'])

        await state.set_state(InventoryStates.Inventory)
        data['settings']['page'] = 0
        await state.update_data(items=searched, pages=pages, settings=data['settings'])

        await swipe_page(chatid, userid)
    else:
        await bot.send_message(userid, t('inventory.search_null', lang))

#Фильтры
@HDCallback
@main_router.callback_query(
    IsPrivateChat(), 
    StateFilter(InventoryStates.InventorySetFilters), 
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
            items = data['items_data']
            itm_fil = data['items']

        sett['page'] = 0
        await state.update_data(settings=sett)

        if 'edited_message' in sett:
            await bot.delete_message(chatid, sett['edited_message'])

        new_items = await filter_items_data(items, filters, itm_fil)
        pages, _ = await generate(new_items, *sett['view'])

        if not pages:
            await state.update_data(filters=[])
            await bot.send_message(chatid, t('inventory.filter_null', lang))
            await state.set_state(InventoryStates.Inventory)
            await swipe_page(chatid, userid)

        else:
            await state.set_state(InventoryStates.Inventory)
            await state.update_data(pages=pages)
            await swipe_page(chatid, userid)

    elif call_data[1] == 'filter':
        if data := await state.get_data():
            filters = data['filters']

        filters_data = get_data('inventory.filters_data', lang)
        if call_data[2] == 'null':
            await state.update_data(filters=[])
            if filters:
                await filter_menu(chatid, False)
        else:
            data_list_filters = filters_data[call_data[2]]['keys']

            if data_list_filters[0] in filters:
                for i in data_list_filters:
                    filters.remove(i)
            else:
                for i in data_list_filters:
                    filters.append(i)

            await state.update_data(filters=filters)
            await filter_menu(chatid, False)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('book'))
async def book(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    book_id = call_data[1]
    page = int(call_data[2])
    text, markup = book_page(book_id, page, lang)
    try:
        await bot.edit_message_text(text, None, chatid, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except Exception as e: 
        log(message=f'Book edit error {e}', lvl=2)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('ns_craft'))
async def ns_craft_c(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_base = await decode_item(call_data[1])
    if not isinstance(item_base, ItemInBase): return

    ns_id = call_data[2]

    transmitted_data = {
        'item_id': item_base._id,
        'ns_id': ns_id
    }

    await ChooseIntHandler(ns_end, userid, chatid, lang, max_int=25, 
                           transmitted_data=transmitted_data).start()

    await bot.send_message(chatid, t('css.wait_count', lang), 
                       reply_markup=count_markup(25, lang))


async def ns_end(count, transmitted_data: dict):
    item_id = transmitted_data['item_id']
    ns_id = transmitted_data['ns_id']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    await ns_craft(item_id, ns_id, chatid, lang, count)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('buyer'))
async def buyer(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    item_base = await decode_item(call_data[1])
    if not isinstance(item_base, ItemInBase):
        return

    if not item_base.link_with_real_item:
        return

    item_decode = item_base.items_data.data
    item_rank = item_decode.rank

    buyer_data = GAME_SETTINGS['buyer'][item_rank]
    one_col = buyer_data['one_col']

    if item_decode.buyer_price:
        price = item_decode.buyer_price
    else:
        price = buyer_data['price']

    emoji = item_base.items_data.name(lang)[0]

    transmitted_data = {
        'item_id': item_base._id,
        'one_col': one_col,
        'price': price
    }

    await ChooseIntHandler(buyer_end, userid, chatid, lang, max_int=25, 
                           transmitted_data=transmitted_data).start()

    await bot.send_message(chatid, t('buyer.choose', lang,
                                 emoji=emoji, one_col=one_col,
                                 price=price), 
                       reply_markup=count_markup(25, lang),
                       parse_mode='Markdown')


async def buyer_end(count, transmitted_data: dict):

    userid = transmitted_data['userid']
    item_id = transmitted_data['item_id']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    one_col = transmitted_data['one_col']
    price = transmitted_data['price'] * count
    
    item = await ItemInBase().link_for_id(item_id)

    need_col = one_col * count
    status = item.count >= need_col

    if status:
        await item.minus(need_col)
        await take_coins(userid, price, True)

        await bot.send_message(chatid, t('buyer.ok', lang), 
                           reply_markup=await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('buyer.no', lang), 
                           reply_markup=await m(userid, 'last_menu', lang))

@HDCallback
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
                log(f'Inline edit error {e}', lvl=2, prefix='InventoryInline')
        else: transmitted_data['bmessageid'] = callback.message.message_id

        item_base = await decode_item(code)
        
        if isinstance(item_base, ItemInBase):
            ret_data = item_base.items_data.to_dict()
        else:
            ret_data = item_base.to_dict()

        handler = ChooseInventoryHandler(**data)
        try:
            await handler.call_function(ret_data)
        except Exception as e:
            log(f'InventoryInline error {e}', lvl=2, prefix='InventoryInline')
