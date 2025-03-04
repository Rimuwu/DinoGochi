from typing import Union
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from bot.dbmanager import mongo_client, conf
from bot.const import GAME_SETTINGS as gs
from bot.exec import main_router, bot
from bot.modules.data_format import (chunks, deepcopy, filling_with_emptiness,
                                     list_to_inline)
from bot.modules.get_state import get_state
from bot.modules.images_save import send_SmartPhoto
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

async def generate(items_data: dict, horizontal: int, vertical: int):
    items_names = list(items_data.keys())
    items_names.sort()

    # Создаёт список, со структурой инвентаря
    pages = chunks(chunks(items_names, horizontal), vertical)

    # Добавляет пустые панели для поддержания структуры
    pages = filling_with_emptiness(pages, horizontal, vertical)

    # Нужно, чтобы стрелки корректно отображались
    if horizontal < 3 and len(pages) > 1: horizontal = 3
    return pages, horizontal

def filter_items_data(items: dict, type_filter: list | None = None, 
                      item_filter: list | None = None):
    if type_filter is None: type_filter = []
    if item_filter is None: item_filter = []

    new_items = deepcopy(items) # type: dict

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

async def inventory_pages(items: list, lang: str = 'en', type_filter: list | None = None,
                    item_filter: list | None = None):
    """ Создаёт и сортируем страницы инвентаря

    type_filter - если не пустой то отбирает предметы по их типу
    item_filter - если не пустой то отбирает предметы по id
    !: Предмет добавляется если соответствует хотя бы одному фильтру

    base_item: {
        item: {
            item_id: str
            abilities: dict (может отсутствовать)
        },
        count: int
    }
    """
    if type_filter is None: type_filter = []
    if item_filter is None: item_filter = []
    
    items_data = {}

    code_items = {}
    for base_item in items:
        if 'item' in base_item:
            item = base_item['item'] # Сам предмет
        else: item = base_item['items_data'] # Сам предмет (для закидки туда предметов из базы)

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
                except: log(f'{data} inventory_pages', 2)

            # Если предмет показывается на страницах
            if add_item:
                count = base_item['count']
                code = item_code(item)

                if code in code_items:
                    code_items[code]['count'] += count
                else:
                    code_items[code] = {'item': item, 'count': count}

    a = -1
    for code, data_item in code_items.items():
        item = data_item['item']
        count = data_item['count']
        name = get_name(item['item_id'], 
                        lang, item.get('abilities', {}))
        standart = is_standart(item)

        count_name = f' x{count}'
        if count == 1: count_name = ''

        end_name = name_end(item, standart, name, count_name)

        if end_name in items_data and items_data[end_name] != item:
            a =+ 1
            name += f' #{a}'
            end_name = name_end(item, standart, name, count_name)

        items_data[end_name] = item

    return items_data

def name_end(item, standart, name, count_name):
    if standart: 
        end_name = f"{name}{count_name}"
    else:
        code = item_code(item, False)
        if code != '':
            end_name = f"{name} ({code}){count_name}"
        else:
            end_name = f"{name}{count_name}"
    return end_name

async def send_item_info(item: dict, transmitted_data: dict, mark: bool=True):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    dev = userid in conf.bot_devs

    text, image = await item_info(item, lang, dev)

    if mark: markup = item_info_markup(item, lang)
    else: markup = None

    if not image:
        await bot.send_message(chatid, text, parse_mode='Markdown',
                            reply_markup=markup)
    else:
        try:
            await send_SmartPhoto(chatid, image, text, 'Markdown', markup)
        except: 
             await bot.send_message(chatid, text,
                            reply_markup=markup)

async def swipe_page(chatid: int, userid: int):
    """ Панель-сообщение смены страницы инвентаря
    """

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        pages = data['pages']
        settings = data['settings']
        items = data['items']
        filters = data['filters']
        main_message = data['main_message']
        up_message = data['up_message']

    if settings['page'] >= len(pages): settings['page'] = 0

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
        if '🔎' in buttons:
            del buttons['🔎']

    if filters:
        if settings['changing_filters']:
            buttons['🗑'] = 'inventory_menu clear_filters'
            menu_text += t('inventory.clear_filters', settings['lang'])

    if items and settings['changing_filters']:
        buttons['❌🔎'] = 'inventory_menu clear_search'

    inl_menu = list_to_inline([buttons], 4)
    if main_message == 0:
        new_main = await bot.send_message(chatid, menu_text, reply_markup=inl_menu, parse_mode='Markdown')
        await state.update_data(main_message=new_main.message_id)
    else:
        await bot.edit_message_text(menu_text, None, chatid, main_message, reply_markup=inl_menu, parse_mode='Markdown')

    if up_message == 0:
        new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
    else:
        new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
        try:
            await bot.delete_message(chatid, up_message)
        except: pass

    await state.update_data(up_message=new_up.message_id)


async def search_menu(chatid: int, userid: int):
    """ Панель-сообщение поиска
    """

    state = await get_state(userid, chatid)
    if data := await state.get_data():
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
        await state.update_data(up_message=new_up.message_id)

    if main_message == 0:
        new_main = await bot.send_message(chatid, menu_text, reply_markup=inl_menu, parse_mode='Markdown')
        await state.update_data(main_message=new_main.message_id)
    else:
        await bot.edit_message_text(menu_text, None, chatid, main_message, reply_markup=inl_menu, parse_mode='Markdown')

async def filter_menu(chatid: int, upd_up_m: bool = True):
    """ Панель-сообщение выбора фильтра
    """
    state = await get_state(chatid, chatid)

    if data := await state.get_data():
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

            await state.update_data(up_message=new_up.message_id)

    if main_message == 0:
        new_main = await bot.send_message(chatid, menu_text, reply_markup=inl_menu, parse_mode='Markdown')
        await state.update_data(main_message=new_main.message_id)
    else:
        await bot.edit_message_text(menu_text, None, chatid, main_message, reply_markup=inl_menu, parse_mode='Markdown')

async def start_inv(function, userid: int, chatid: int, lang: str, 
                    type_filter: list | None = None, item_filter: list | None = None, 
                    exclude_ids: list | None = None,
                    start_page: int = 0, changing_filters: bool = True,
                    inventory: list | None = None, delete_search: bool = False,
                    transmitted_data = None,
                    inline_func = None, inline_code = ''
                    ):
    """ Функция запуска инвентаря
        type_filter - фильтр типов предметов
        item_filter - фильтр по id предметам
        start_page - стартовая страница
        exclude_ids - исключаемые id
        changing_filters - разрешено ли изменять фильтры
        one_time_pages - сколько генерировать страниц за раз, все если 0
        delete_search - Убрать поиск
        inventory - Возможность закинуть уже обработанный инвентарь, если пусто - сам сгенерирует инвентарь


        >> Создано для steps, при активации перенаправляет данные при нажатии
        на inline_func, а при нажатии на кнопку начинающийся на inventoryinline {inline_code}
        перенаправляет данные, выбранные по кнопке в function

        >> В inline_func так же передаётся inline_code в transmitted_data

        inline_func - Если нужна функция для обработки калбек запросов 
            - Все кнопки должны начинаться с "inventoryinline {inline_code}" 
    """

    if type_filter is None: type_filter = []
    if item_filter is None: item_filter = []
    if exclude_ids is None: exclude_ids = []
    if inventory is None: inventory = []

    state = await get_state(userid, chatid)
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
    pages, row = await generate(items_data, *inv_view)

    if not pages:
        await bot.send_message(chatid, t('inventory.null', lang), 
                           reply_markup=await m(chatid, 'last_menu', language_code=lang))
        return False, 'cancel'
    else:
        try:
            data = await state.get_data() or {}
            if data:
                old_function = data['function']
                old_transmitted_data = data['transmitted_data']

            if old_function: function = old_function
            if old_transmitted_data: transmitted_data = old_transmitted_data
        except: 
            # Если не передана функция, то вызывается функция информация о передмете
            if function is None: function = send_item_info

        await state.set_state(InventoryStates.Inventory)

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

        if inline_func is not None:
            data['settings']['inline_func'] = inline_func
            data['settings']['inline_code'] = inline_code

        await state.set_data(data)
        log(f'open inventory userid {userid} count {count}')

        await swipe_page(chatid, userid)
        return True, 'inv'

async def open_inv(chatid: int, userid: int):
    """ Внутренняя фунция для возврата в инвентарь
    """

    state = await get_state(userid, chatid)
    await state.set_state(InventoryStates.Inventory)
    await swipe_page(chatid, userid)


