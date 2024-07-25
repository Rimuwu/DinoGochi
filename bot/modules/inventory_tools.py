from telebot.asyncio_handler_backends import State, StatesGroup

from bot.config import mongo_client, conf
from bot.const import GAME_SETTINGS as gs
from bot.exec import bot
from bot.modules.data_format import (chunks, filling_with_emptiness,
                                     list_to_inline)
from bot.modules.inline import item_info_markup
from bot.modules.items.item import (get_data, get_name, is_standart, item_code,
                              item_info)
from bot.modules.localization import get_data as get_loc_data
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import list_to_keyboard, down_menu
from bot.modules.markup import markups_menu as m
from bot.modules.user.user import get_inventory


from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)

back_button, forward_button = gs['back_button'], gs['forward_button']

class InventoryStates(StatesGroup):
    Inventory = State() # Состояние открытого инвентаря
    InventorySearch = State() # Состояние поиска в инвентаре
    InventorySetFilters = State() # Состояние настройки фильтров в инвентаре

def generate(items_data: dict, horizontal: int, vertical: int):
    items_names = list(items_data.keys())
    items_names.sort()

    # Создаёт список, со структурой инвентаря
    pages = chunks(chunks(items_names, horizontal), vertical)

    # Добавляет пустые панели для поддержания структуры
    pages = filling_with_emptiness(pages, horizontal, vertical)

    # Нужно, чтобы стрелки корректно отображались
    if horizontal < 3 and len(pages) > 1: horizontal = 3
    return pages, horizontal

def filter_items_data(items: dict, type_filter: list = [], 
                      item_filter: list = []):
    new_items = items.copy()

    for key, item in items.items():
        add_item = False
        data = get_data(item['item_id'])

        if not (type_filter or item_filter):
            # Фильтры пустые
            add_item = True
        else:
            try:
                if data['type'] in type_filter: add_item = True
                if item['item_id'] in item_filter: add_item = True
            except: log(str(data), 2)

        # Если предмет показывается на страницах
        if not add_item: del new_items[key]

    return new_items

async def inventory_pages(items: list, lang: str = 'en', type_filter: list = [],
                    item_filter: list = []):
    """ Создаёт и сортируем страницы инвентаря

    type_filter - если не пустой то отбирает предметы по их типу
    item_filter - если не пустой то отбирает предметы по id
    !: Предмет добавляется если соответствует хотя бы одному фильтру

    item: {
        items_data: {
            item_id: str
            abilities: dict (может отсутствовать)
        },
        count: int
    }
    """
    items_data = {}

    code_items = {}
    for base_item in items:
        item = base_item['item'] # Сам предмет
        data = get_data(item['item_id']) # Дата из json
        add_item = False

        # Если предмет найден в базе
        if data:
            # Проверка на соответсвие фильтров
            if not (type_filter or item_filter):
                # Фильтры пустые
                add_item = True
            else:
                try:
                    if data['type'] in type_filter: add_item = True
                    if item['item_id'] in item_filter: add_item = True
                except: log(str(data), 2)

            # Если предмет показывается на страницах
            if add_item:
                count = base_item['count']
                code = item_code(item)

                if code in code_items:
                    code_items[code]['count'] += count
                else:
                    code_items[code] = {'item': item, 'count': count}

    for code, data_item in code_items.items():
        item = data_item['item']
        count = data_item['count']
        name = get_name(item['item_id'], lang)
        standart = is_standart(item)

        count_name = f' x{count}'
        if count == 1: count_name = ''

        if standart: 
            end_name = f"{name}{count_name}"
        else:
            code = item_code(item, False)
            end_name = f"{name} ({code}){count_name}"
        items_data[end_name] = item

    return items_data

async def send_item_info(item: dict, transmitted_data: dict, mark: bool=True):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    dev = userid in conf.bot_devs

    text, image = await item_info(item, lang, dev)

    if mark: markup = item_info_markup(item, lang)
    else: markup = None

    if not image:
        await bot.send_message(chatid, text, 'Markdown',
                            reply_markup=markup)
    else:
        try:
            await bot.send_photo(chatid, image, text, 'Markdown', 
                            reply_markup=markup)
        except: 
             await bot.send_message(chatid, text,
                            reply_markup=markup)

async def swipe_page(userid: int, chatid: int):
    """ Панель-сообщение смены страницы инвентаря
    """
    async with bot.retrieve_data(userid, chatid) as data:
        pages = data['pages']
        settings = data['settings']
        items = data['items']
        filters = data['filters']
        main_message = data['main_message']
        up_message = data['up_message']

    keyboard = list_to_keyboard(pages[settings['page']], settings['row'])

    # Добавляем стрелочки
    keyboard = down_menu(keyboard, len(pages) > 1, settings['lang'])

    # Генерация текста и меню
    menu_text = t('inventory.menu', settings['lang'], 
                  page=settings['page']+1, col=len(pages))
    text = t('inventory.update_page', settings['lang'])
    buttons = {
        '⏮': 'inventory_menu first_page', '🔎': 'inventory_menu search', 
        '⚙️': 'inventory_menu filters', '⏭': 'inventory_menu end_page',
        '♻️': 'inventory_menu remessage'
        }

    if not settings['changing_filters']:
        del buttons['⚙️']
        del buttons['🔎']

    if 'delete_search' in settings and settings['delete_search']:
        try:
            del buttons['🔎']
        except: pass

    if filters:
        if settings['changing_filters'] and settings['changing_filters']:
            buttons['🗑'] = 'inventory_menu clear_filters'
            menu_text += t('inventory.clear_filters', settings['lang'])

    if items and settings['changing_filters']:
        buttons['❌🔎'] = 'inventory_menu clear_search'


    inl_menu = list_to_inline([buttons], 4)
    if main_message == 0:
        new_main = await bot.send_message(chatid, menu_text, reply_markup=inl_menu, parse_mode='Markdown')
        async with bot.retrieve_data(userid, chatid) as data:
            data['main_message'] = new_main.message_id
    else:
        await bot.edit_message_text(menu_text, chatid, main_message, reply_markup=inl_menu, parse_mode='Markdown')

    if up_message == 0:
        new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
    else:
        new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
        await bot.delete_message(chatid, up_message)

    async with bot.retrieve_data(userid, chatid) as data:
        data['up_message'] = new_up.message_id


async def search_menu(userid: int, chatid: int):
    """ Панель-сообщение поиска
    """
    async with bot.retrieve_data(userid, chatid) as data:
        settings = data['settings']
        main_message = data['main_message']
        up_message = data['up_message']

    menu_text = t('inventory.search', settings['lang'])
    buttons = {'❌': 'inventory_search close'}
    inl_menu = list_to_inline([buttons])

    text = t('inventory.update_search', settings['lang'])
    keyboard = list_to_keyboard([ t('buttons_name.cancel', settings['lang']) ])
    
    if up_message == 0:
        await bot.send_message(chatid, text, reply_markup=keyboard)
    else:
        new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
        await bot.delete_message(chatid, up_message)
        async with bot.retrieve_data(userid, chatid) as data:
            data['up_message'] = new_up.message_id
    
    if main_message == 0:
        new_main = await bot.send_message(chatid, menu_text, reply_markup=inl_menu, parse_mode='Markdown')
        async with bot.retrieve_data(userid, chatid) as data:
            data['main_message'] = new_main.message_id
    else:
        await bot.edit_message_text(menu_text, chatid, main_message, reply_markup=inl_menu, parse_mode='Markdown')
    
async def filter_menu(userid: int, chatid: int, upd_up_m: bool = True):
    """ Панель-сообщение выбора фильтра
    """
    async with bot.retrieve_data(userid, chatid) as data:
        settings = data['settings']
        filters = data['filters']
        main_message = data['main_message']
        up_message = data['up_message']

    menu_text = t('inventory.choice_filter', settings['lang'])
    filters_data = get_loc_data('inventory.filters_data', settings['lang'])
    buttons = {}
    for key, item in filters_data.items():
        name = item['name']
        if list(set(filters) & set(item['keys'])):
            name = "✅" + name

        buttons[name] = f'inventory_filter filter {key}'

    cancel = {'✅': 'inventory_filter close'}
    inl_menu = list_to_inline([buttons, cancel])

    text = t('inventory.update_filter', settings['lang'])
    keyboard = list_to_keyboard([ t('buttons_name.cancel', settings['lang']) ])

    if upd_up_m:
        if up_message == 0:
            await bot.send_message(chatid, text, reply_markup=keyboard)
        else:
            new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
            await bot.delete_message(chatid, up_message)
            async with bot.retrieve_data(userid, chatid) as data:
                data['up_message'] = new_up.message_id
    
    if main_message == 0:
        new_main = await bot.send_message(chatid, menu_text, reply_markup=inl_menu, parse_mode='Markdown')
        async with bot.retrieve_data(userid, chatid) as data:
            data['main_message'] = new_main.message_id
    else:
        await bot.edit_message_text(menu_text, chatid, main_message, reply_markup=inl_menu, parse_mode='Markdown')

    # if 'edited_message' in settings and settings['edited_message']:
    #     try:
    #         await bot.edit_message_text(menu_text, chatid, settings['edited_message'], reply_markup=inl_menu, parse_mode='Markdown')
    #     except: pass
    # else:
    #     await bot.send_message(chatid, text, reply_markup=keyboard)
    #     msg = await bot.send_message(chatid, menu_text, 
    #                         parse_mode='Markdown', reply_markup=inl_menu)
        
    #     async with bot.retrieve_data(
    #         userid, chatid) as data: data['settings']['edited_message'] = msg.id

async def start_inv(function, userid: int, chatid: int, lang: str, 
                    type_filter: list = [], item_filter: list = [], 
                    exclude_ids: list = [],
                    start_page: int = 0, changing_filters: bool = True,
                    inventory: list = [], delete_search: bool = False,
                    transmitted_data = None):
    """ Функция запуска инвентаря
        type_filter - фильтр типов предметов
        item_filter - фильтр по id предметам
        start_page - стартовая страница
        exclude_ids - исключаемые id
        changing_filters - разрешено ли изменять фильтры
        one_time_pages - сколько генерировать страниц за раз, все если 0
        delete_search - Убрать поиск
        inventory - Возможность закинуть уже обработанный инвентарь, если пусто - сам сгенерирует инвентарь
    """
    if not transmitted_data: transmitted_data = {}
    count = 0

    if 'userid' not in transmitted_data: transmitted_data['userid'] = userid
    if 'chatid' not in transmitted_data: transmitted_data['chatid'] = chatid
    if 'lang' not in transmitted_data: transmitted_data['lang'] = lang

    user_settings = await users.find_one({'userid': userid}, {'settings': 1}, comment='start_inv_user_settings')
    if user_settings: inv_view = user_settings['settings']['inv_view']
    else: inv_view = [2, 3]

    if not inventory:
        inventory, count = await get_inventory(userid, exclude_ids)
    items_data = await inventory_pages(inventory, lang, type_filter, item_filter)
    pages, row = generate(items_data, *inv_view)

    if not pages:
        await bot.send_message(chatid, t('inventory.null', lang), 
                           reply_markup=await m(chatid, 'last_menu', language_code=lang))
        return False, 'cancel'
    else:
        try:
            async with bot.retrieve_data(userid, chatid) as data:
                old_function = data['function']
                old_transmitted_data = data['transmitted_data']

            if old_function: function = old_function
            if old_transmitted_data: transmitted_data = old_transmitted_data
        except: 
            # Если не передана функция, то вызывается функция информация о передмете
            if function is None: function = send_item_info
            
        await bot.set_state(userid, InventoryStates.Inventory, chatid)
        async with bot.retrieve_data(userid, chatid) as data:
            data['pages'] = pages
            data['items_data'] = items_data
            data['filters'] = type_filter
            data['items'] = item_filter

            data['settings'] = {'view': inv_view, 'lang': lang, 
                                'row': row, 'page': start_page,
                                'changing_filters': changing_filters,
                                'delete_search': delete_search
                                }
            data['main_message'] = 0
            data['up_message'] = 0

            data['function'] = function
            data['transmitted_data'] = transmitted_data
        
        log(f'open inventory userid {userid} count {count}')
        
        await swipe_page(userid, chatid)
        return True, 'inv'

async def open_inv(userid: int, chatid: int):
    """ Внутренняя фунция для возврата в инвентарь
    """
    await bot.set_state(userid, InventoryStates.Inventory, chatid)
    await swipe_page(userid, chatid)


