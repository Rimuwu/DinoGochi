from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import User
from typing import Union
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from bot.dbmanager import mongo_client, conf
from bot.const import GAME_SETTINGS as gs
from bot.exec import main_router, bot
from bot.modules.data_format import (chunks, deepcopy, filling_with_emptiness,
                                     list_to_inline, list_to_keyboard)
from bot.modules.get_state import get_state
from bot.modules.images_save import send_SmartPhoto
from bot.modules.inline import item_info_markup
from bot.modules.items.item import (get_data, get_name, is_standart, item_code,
                              item_info, get_lvl_data)
from bot.modules.localization import get_data as get_loc_data
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import markups_menu as m, down_menu



users = LazyCollection(User)

back_button, forward_button = gs['back_button'], gs['forward_button']

class InventoryStates(StatesGroup):
    Inventory = State() # Состояние открытого инвентаря
    InventorySearch = State() # Состояние поиска в инвентаре
    InventorySetFilters = State() # Состояние настройки фильтров в инвентаре

# Per-type primary stat key for sorting
_TYPE_STAT_KEY = {
    'weapon': 'damage_min',
    'armor': 'defence',
    'backpack': 'capacity',
    'eat': 'act',
    'sleep': 'endurance_max',
    'journey': 'endurance_max',
    'collecting': 'endurance_max',
    'game': 'endurance_max',
}

def sort_items_data(items_data: dict, sort_key: str = 'name', direction: str = 'asc',
                    meta_data: dict | None = None) -> dict:
    """Sort the items_data display dict by the given key and direction.
    meta_data: optional dict mapping display_name -> {'count': int, '_id': ObjectId}
    """
    reverse = direction == 'desc'
    if meta_data is None:
        meta_data = {}

    def key_func(entry):
        name, item = entry
        meta = meta_data.get(name, {})
        if sort_key == 'name':
            return name.lower()
        elif sort_key == 'count':
            return meta.get('count', 1)
        elif sort_key == 'type':
            return get_data(item['item_id']).get('type', '')
        elif sort_key == 'novelty':
            val = meta.get('_id')
            return str(val) if val else name
        elif sort_key == 'stat':
            item_type = get_data(item['item_id']).get('type', '')
            stat_key = _TYPE_STAT_KEY.get(item_type, 'act')
            # Check lvl data first
            data = get_data(item['item_id'])
            lvl = item.get('abilities', {}).get('lvl', 0)
            if lvl:
                lvl_data = get_lvl_data(data, lvl)
                if lvl_data and stat_key in lvl_data:
                    return lvl_data[stat_key]
                # If stat_key is not in the closest level, let's search even lower levels
                elif lvl_data:
                    lvls = data.get('lvls', {})
                    valid_lvls = []
                    for k, lvl_info in lvls.items():
                        try:
                            k_int = int(k)
                            if k_int <= lvl and stat_key in lvl_info:
                                valid_lvls.append(k_int)
                        except ValueError:
                            continue
                    if valid_lvls:
                        best_lvl = max(valid_lvls)
                        return lvls[str(best_lvl)][stat_key]
            return data.get(stat_key, data.get('abilities', {}).get(stat_key, 0))
        return name.lower()

    sorted_pairs = sorted(items_data.items(), key=key_func, reverse=reverse)
    return dict(sorted_pairs)

async def generate(items_data: dict, horizontal: int, vertical: int,
                   sort_key: str = 'name', direction: str = 'asc',
                   meta_data: dict | None = None):
    sorted_data = sort_items_data(items_data, sort_key, direction, meta_data=meta_data)
    items_names = list(sorted_data.keys())
    # No default alphabetic sort — order preserved from sort_items_data

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

                key_code_parts = []
                for k, v in item.items():
                    if k == 'abilities' and isinstance(v, dict):
                        for ability_key, ability_value in v.items():
                            key_code_parts.append(f"{ability_key}-{ability_value}")
                    else:
                        key_code_parts.append(f"{k}-{v}")
                key_code = ":".join(key_code_parts)

                db_id = base_item.get('_id', None)
                if key_code in code_items:
                    code_items[key_code]['count'] += count
                    if db_id and (not code_items[key_code]['_id'] or db_id > code_items[key_code]['_id']):
                        code_items[key_code]['_id'] = db_id
                else:
                    code_items[key_code] = {'item': item, 'count': count, '_id': db_id}

    a = -1
    for code, data_item in code_items.items():
        item = data_item['item']  # keep original item dict clean (no count/_id)
        count = data_item['count']
        db_id = data_item['_id']
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
        # Store sort metadata separately — never pollute item dict with count/_id
        items_data.setdefault('__meta__', {})[end_name] = {'count': count, '_id': db_id}

    # Extract and remove __meta__ from items_data — return it separately
    meta_data = items_data.pop('__meta__', {})
    return items_data, meta_data

def name_end(item, name, count_name):
    from bot.modules.items.item import get_data, get_item_endurance_max
    standart = is_standart(item)
    if standart:
        end_name = f"{name}{count_name}"
    else:
        display_str = ''
        abilities = item.get('abilities', {})
        
        for key in ['endurance', 'uses']:
            if key in abilities:
                val = abilities[key]
                if key == 'endurance':
                    max_val = get_item_endurance_max(item)
                else:
                    data_item = get_data(item['item_id'])
                    max_val = data_item.get('abilities', {}).get('uses', 0)
                    
                if max_val > 0:
                    if val < max_val:
                        pct = int((val / max_val) * 100)
                        display_str = f" ({pct}%)"
                break
                
        end_name = f"{name}{display_str}{count_name}"
    return end_name

async def send_item_info(item: dict, transmitted_data: dict, mark: bool=True):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']

    dev = userid in conf.bot_devs

    text, image = await item_info(item, lang, dev)

    if mark: markup = await item_info_markup(item, 
                        lang, userid)
    else:
        markup = list_to_inline([{t("buttons_name.delete_message", lang): "delete_message"}])

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
        '🔃': 'inventory_menu sort', '⚙️': 'inventory_menu filters', '⏭': 'inventory_menu end_page',
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

async def sort_menu(chatid: int, userid: int):
    """ Панель-сообщение сортировки
    """
    state = await get_state(userid, chatid)
    if data := await state.get_data():
        settings = data['settings']
        main_message = data['main_message']

    lang = settings['lang']
    menu_text = t('inventory.sort_menu', lang)

    sort_opts = [
        ('name_asc', t('inventory.sort_options.name_asc', lang)),
        ('name_desc', t('inventory.sort_options.name_desc', lang)),
        ('novelty_asc', t('inventory.sort_options.novelty_asc', lang)),
        ('novelty_desc', t('inventory.sort_options.novelty_desc', lang)),
        ('count_asc', t('inventory.sort_options.count_asc', lang)),
        ('count_desc', t('inventory.sort_options.count_desc', lang)),
        ('type_asc', t('inventory.sort_options.type_asc', lang)),
        ('type_desc', t('inventory.sort_options.type_desc', lang)),
        ('stat_asc', t('inventory.sort_options.stat_asc', lang)),
        ('stat_desc', t('inventory.sort_options.stat_desc', lang))
    ]

    buttons = []
    for i in range(0, len(sort_opts), 2):
        row = {
            sort_opts[i][1]: f'inventory_sort {sort_opts[i][0]}',
            sort_opts[i+1][1]: f'inventory_sort {sort_opts[i+1][0]}'
        }
        buttons.append(row)

    buttons.append({'❌': 'inventory_sort cancel'})
    inl_menu = list_to_inline(buttons, 2)

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

async def open_inv(chatid: int, userid: int):
    """ Внутренняя фунция для возврата в инвентарь
    """

    state = await get_state(userid, chatid)
    await state.clear()
    await state.set_state(InventoryStates.Inventory)
    await swipe_page(chatid, userid)


