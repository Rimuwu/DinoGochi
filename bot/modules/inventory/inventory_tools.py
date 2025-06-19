
from typing import Union
from aiogram.fsm.state import StatesGroup, State
from bson import ObjectId

from bot.dbmanager import mongo_client, conf
from bot.const import GAME_SETTINGS as gs
from bot.exec import bot
from bot.modules.data_format import (chunks, deepcopy, filling_with_emptiness,
                                     list_to_inline)
from bot.modules.get_state import get_state
from bot.modules.images_save import send_SmartPhoto
from bot.modules.inline import item_info_markup
from bot.modules.items.item import (ItemData, ItemInBase,  get_name, item_info)
from bot.modules.items.json_item import Ammunition, Armor, Backpack, Book, Case, Collecting, Eat, Egg, Game, GetItem, Journey, Recipe, Sleep, Special, Weapon
from bot.modules.localization import get_data as get_loc_data
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import list_to_keyboard, down_menu


from bot.modules.overwriting.DataCalsses import DBconstructor

users = DBconstructor(mongo_client.user.users)

back_button, forward_button = gs['back_button'], gs['forward_button']

class InventoryStates(StatesGroup):
    Inventory = State() # Состояние открытого инвентаря
    InventorySearch = State() # Состояние поиска в инвентаре
    InventorySetFilters = State() # Состояние настройки фильтров в инвентаре
    InventorySort = State() # Состояние сортировки в инвентаре

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

async def filter_items_data(items: dict, 
                      type_filter: list | None = None, 
                      item_filter: list | None = None):
    if type_filter is None: type_filter = []
    if item_filter is None: item_filter = []

    new_items = items.copy()

    for key, item in items.items():
        add_item = False

        if isinstance(item, ObjectId):
            item_base = await ItemInBase().link_for_id(item)
            data = item_base.items_data
            item_id = item_base.item_id
        else:
            data = ItemData(**item)
            item_id = item['item_id']

        if not (type_filter or item_filter):
            # Фильтры пустые
            add_item = True
        else:
            if item_id in item_filter: add_item = True
            if str(data.data.type) in type_filter: add_item = True

        # Если предмет показывается на страницах
        if not add_item: del new_items[key]

    return new_items

def effectiveness_key(item):
    data = item.items_data.data
    if isinstance(data, Book):
        return (0, data.rank)
    elif isinstance(data, Case):
        return (1, len(data.drop_items))
    elif isinstance(data, Collecting):
        return (2, data.rank)
    elif isinstance(data, Game):
        return (3, data.rank)
    elif isinstance(data, Journey):
        return (4, data.rank)
    elif isinstance(data, Sleep):
        return (5, data.rank)
    elif isinstance(data, Weapon):
        return (6, 
            data.effectiv + data.damage['min'] + data.damage['max'])
    elif isinstance(data, Backpack):
        return (7, data.capacity)
    elif isinstance(data, Ammunition):
        return (8, data.add_damage)
    elif isinstance(data, Armor):
        return (9, data.reflection)
    elif isinstance(data, Eat):
        return (10, data.act)
    elif isinstance(data, Egg):
        return (11, data.inc_type)
    elif isinstance(data, Recipe):
        return (12, data.time_craft)
    elif isinstance(data, Special):

        if data.item_class == 'premium':
            return (13, data.premium_time)
        elif data.item_class == 'freezing':
            return (14, data.time)
        else:
            return (15, data.rank)
    else:
        # Для остальных типов сортируем по имени
        return (16, data.rank)

def sort_items(items: list[ItemInBase], 
               sort_type: str = 'default', 
               sort_up: bool = True,
               lang: str = 'en'
               ) -> list[ItemInBase]:
    """ Сортирует предметы в инвентаре по заданному типу
    """

    if sort_type == 'default':
        items = sorted(items, key=lambda x: x.items_data.name(lang)[2:], 
                       reverse=sort_up)
    elif sort_type == 'rarity':
        items = sorted(items, key=lambda x: x.items_data.data.rank, 
                       reverse=sort_up)
    elif sort_type == 'type':
        items = sorted(items, key=lambda x: x.items_data.data.type, 
                       reverse=sort_up)
    elif sort_type == 'date':
        items = sorted(items, key=lambda x: x._id.generation_time, 
                       reverse=sort_up)
    elif sort_type == 'count':
        items = sorted(items, key=lambda x: x.count, 
                       reverse=sort_up)

    elif sort_type == 'effectiveness':
        # Сортировка по эффективности для каждого типа предмета
        items = sorted(items, key=effectiveness_key)

    else:
        raise ValueError(f'Invalid sort type: {sort_type}')

    if not sort_up:
        items.reverse()

    return items

async def inventory_pages(
    items: list[Union[ItemInBase, ItemData, ObjectId]], lang: str = 'en', 
    type_filter: list | None = None,
    item_filter: list | None = None,
    sort_type: str = 'default',
    sort_up: bool = True,
    return_objectids: bool = False
    ):
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

    items_base_list: list[ItemInBase] = []
    for base_item in items:
        if isinstance(base_item, (ObjectId, ItemInBase)):
            if isinstance(base_item, ObjectId):
                base_item = await ItemInBase().link_for_id(base_item)
            items_base_list.append(base_item)

        elif isinstance(base_item, ItemData):
            item = ItemInBase(**base_item.to_dict())
            items_base_list.append(item)

        else:
            raise TypeError(
                f'Invalid type of item: {type(base_item)}. '
                'Expected ItemInBase, ItemData or ObjectId.'
            )

    items_sorted = sort_items(items_base_list, sort_type, sort_up, lang)

    for base_item in items_sorted:
        data = base_item.items_data.data
        count = base_item.count
        item_id = base_item.item_id
        item = base_item.items_data.to_dict()
        add_item = False

        # Если предмет найден в базе
        if data:
            # Проверка на соответсвие фильтров
            if not (type_filter or item_filter):
                # Фильтры пустые
                add_item = True
            else:
                try:
                    if data.type in type_filter: add_item = True
                    if item_id in item_filter: add_item = True
                except: log(f'{data} inventory_pages', 2)

            # Если предмет показывается на страницах
            if add_item:

                key_code_parts = []
                for k, v in item.items():

                    if k == 'abilities' and isinstance(v, dict):
                        for ability_key, ability_value in v.items():
                            key_code_parts.append(f"{ability_key}-{ability_value}")
                    else:
                        key_code_parts.append(f"{k}-{v}")

                key_code = ":".join(key_code_parts)

                if key_code in code_items:
                    code_items[key_code]['count'] += count
                else:
                    code_items[key_code] = {'item': item, 'count': count, 'base_item': base_item}

    a = -1
    for code, data_item in code_items.items():
        item = data_item['item']
        count = data_item['count']
        name = get_name(item['item_id'], 
                        lang, item.get('abilities', {}))

        count_name = f' x{count}'
        if count == 1: count_name = ''

        end_name = name_end(item, name, count_name)

        if end_name in items_data and items_data[end_name] != item:
            a += 1
            name += f' #{a}'
            end_name = name_end(item, name, count_name)

        items_data[end_name] = item

        if return_objectids:
            if isinstance(data_item['base_item'], ItemInBase):
                if data_item['base_item'].link_with_real_item:
                    items_data[end_name] = data_item['base_item']._id
                else:
                    items_data[end_name] = None

    return items_data

def name_end(item, name, count_name):
    item = ItemData(**item)

    if item.is_standart:
        end_name = f"{name}{count_name}"
    else:
        code = ''

        if 'endurance' in item.abilities:
            code = item.abilities['endurance']
        elif 'uses' in item.abilities:
            code = item.abilities['uses']

        if code != '':
            end_name = f"{name} ({code}){count_name}"
        else:
            end_name = f"{name}{count_name}"
    return end_name

async def send_item_info(item: dict | ObjectId,
                         transmitted_data: dict, mark: bool=True):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']

    dev = userid in conf.bot_devs
    
    if isinstance(item, ObjectId):
        item_cls = await ItemInBase().link_for_id(item)
    else:
        item_cls = ItemInBase(owner_id=userid, **item)
        await item_cls.link_yourself()
        if not item_cls.link_with_real_item:
            item_cls = ItemData(**item)

    text, image = await item_info(item_cls, lang, dev)
    if mark and isinstance(item_cls, ItemInBase): 
        markup = await item_info_markup(item_cls, lang)
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
        '🔃': 'inventory_menu sort', '♻️': 'inventory_menu remessage'
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
            name = f'> {name} <'

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

async def open_inv(chatid: int, userid: int):
    """ Внутренняя фунция для возврата в инвентарь
    """

    state = await get_state(userid, chatid)
    await state.clear()
    await state.set_state(InventoryStates.Inventory)
    await swipe_page(chatid, userid)

async def sort_menu(chatid: int, upd_up_m: bool = True):
    """ Панель-сообщение выбора сортировки
    """
    # TODO доделать сортировку
    state = await get_state(chatid, chatid)

    if data := await state.get_data():
        settings = data['settings']
        main_message = data['main_message']
        up_message = data['up_message']

    menu_text = t('inventory.choice_sort', settings['lang'])
    filters_data = get_loc_data('inventory.sort_data', settings['lang'])
    sort_up_data = get_loc_data('inventory.sort_flag', settings['lang'])
    buttons = {}
    for key, name in filters_data.items():
        if settings['sort_type'] == key:
            name = f'> {name} <'

        buttons[name] = f'inventory_sort filter {key}'

    for key, name in sort_up_data.items():
        if settings['sort_up'] == (key == 'up'):
            name = f'> {name} <'

        buttons[name] = f'inventory_sort filter_up {key}'

    cancel = {'✅': 'inventory_sort close'}
    inl_menu = list_to_inline([buttons, cancel])

    text = t('inventory.update_sort', settings['lang'])
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