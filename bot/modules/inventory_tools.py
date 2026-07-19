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

def get_group_type(item_type: str) -> str:
    if item_type in ['collecting', 'game', 'journey', 'sleep', 'accessory']:
        return 'accessory'
    if item_type in ['material', 'dummy']:
        return 'material'
    if item_type in ['booster', 'incubation_boost', 'training_boost']:
        return 'booster'
    if item_type in ['weapon', 'ammunition', 'backpack', 'armor', 'combat']:
        return 'combat'
    if item_type in ['runes', 'rune']:
        return 'rune'
    return item_type

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
                if get_group_type(data['type']) in type_filter: add_item = True
                if item['item_id'] in item_filter: add_item = True
            except: log(str(data), 2)

        # Если предмет показывается на страницах
        if not add_item: del new_items[key]

    return new_items



def filter_and_sort_inventory(items: list, lang: str = 'en', type_filter: list | None = None,
                               item_filter: list | None = None, sort_key: str = 'name', direction: str = 'asc',
                               rare_emoji: bool = True, only_emoji: bool = False, numbered: bool = False, html: bool = False):
    if type_filter is None: type_filter = []
    if item_filter is None: item_filter = []

    code_items = {}
    for base_item in items:
        if 'item' in base_item:
            item = base_item['item']
        else:
            item = base_item['items_data']

        data = get_data(item['item_id'])
        if not data:
            continue

        add_item = False
        if not (type_filter or item_filter):
            add_item = True
        else:
            try:
                if get_group_type(data['type']) in type_filter or data['type'] in type_filter: add_item = True
                if item['item_id'] in item_filter: add_item = True
            except:
                log(f'{data} filter_and_sort_inventory', 2)

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

    items_data = {}
    a = -1
    for code, data_item in code_items.items():
        item = data_item['item']
        count = data_item['count']
        db_id = data_item['_id']

        from bot.modules.items.item import get_emoji, get_name, get_emoji_html
        if only_emoji:
            if html:
                name = get_emoji_html(item['item_id'], rare_emoji=rare_emoji)
            else:
                name = get_emoji(item['item_id'], lang, rare_emoji=rare_emoji)
            if not name:
                name = get_name(item['item_id'], lang, item.get('abilities', {}), rare_emoji=rare_emoji, html=html)
        else:
            name = get_name(item['item_id'], lang, item.get('abilities', {}), rare_emoji=rare_emoji, html=html)

        count_name = f' x{count}'
        if count == 1: count_name = ''

        end_name = name_end(item, name, count_name)

        if end_name in items_data and items_data[end_name] != item:
            a += 1
            name += f' #{a}'
            end_name = name_end(item, name, count_name)

        items_data[end_name] = item
        items_data.setdefault('__meta__', {})[end_name] = {'count': count, '_id': db_id}

    meta_data = items_data.pop('__meta__', {})
    sorted_data = sort_items_data(items_data, sort_key, direction, meta_data=meta_data)
    
    result = []
    index = 1
    for name, item in sorted_data.items():
        if numbered:
            numbered_name = f"{index}. {name}"
            result.append((numbered_name, item, meta_data.get(name, {})))
            index += 1
        else:
            result.append((name, item, meta_data.get(name, {})))
    return result





async def inventory_pages(items: list, lang: str = 'en', type_filter: list | None = None,
                    item_filter: list | None = None, rare_emoji: bool = True, only_emoji: bool = False):
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

        from bot.modules.items.item import get_emoji, get_name
        if only_emoji:
            name = get_emoji(item['item_id'], lang, rare_emoji=rare_emoji)
            if not name:
                name = get_name(item['item_id'], lang, item.get('abilities', {}), rare_emoji=rare_emoji)
        else:
            name = get_name(item['item_id'], lang, item.get('abilities', {}), rare_emoji=rare_emoji)

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
                    max_val = get_item_endurance_max(item) or 0
                else:
                    data_item = get_data(item['item_id'])
                    max_val = data_item.get('abilities', {}).get('uses', 0) or 0
                    
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

    text, image = await item_info(item, lang, dev, html=True)

    if mark: markup = await item_info_markup(item, 
                        lang, userid)
    else:
        markup = list_to_inline([{t("buttons_name.delete_message", lang): {"callback_data": "delete_message", "style": "danger", "custom_emoji_id": "trash"}}])

    if not image:
        await bot.send_message(chatid, text, parse_mode='HTML',
                            reply_markup=markup)
    else:
        try:
            await send_SmartPhoto(chatid, image, text, 'HTML', markup)
        except Exception as e:
            log(f'send_SmartPhoto error for image {image}: {e}', lvl=2)
            await bot.send_message(chatid, text, parse_mode='HTML',
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

    current_page = settings['page']
    if current_page >= len(pages):
        current_page = 0
        settings['page'] = 0

    virtual_pages = data.get('virtual_pages', [])
    if not virtual_pages:
        from bot.models.user import User
        raw_inv, _ = await User.get_inventory(userid, data.get('exclude_ids', []))
        inv_sort = settings.get('inv_sort', 'name_asc')
        sort_key, direction = inv_sort.split('_')
        sorted_items = filter_and_sort_inventory(
            raw_inv, settings['lang'], filters, items, sort_key, direction,
            rare_emoji=settings.get('rare_emoji', True),
            only_emoji=settings.get('only_emoji', False),
            numbered=settings.get('only_emoji', False)
        )
        view = settings['view']
        items_per_page = view[0] * view[1]
        from bot.modules.data_format import chunks
        virtual_pages = chunks(sorted_items, items_per_page)
        if len(pages) != len(virtual_pages):
            pages = [None] * len(virtual_pages)
            if current_page >= len(pages):
                current_page = 0
                settings['page'] = 0

    if virtual_pages:
        view = settings['view']
        inv_sort = settings.get('inv_sort', 'name_asc')
        sort_key, direction = inv_sort.split('_')
        
        total_pages = len(virtual_pages)
        active_indices = {current_page}
        if current_page - 1 >= 0: active_indices.add(current_page - 1)
        else: active_indices.add(total_pages - 1)
        if current_page + 1 < total_pages: active_indices.add(current_page + 1)
        else: active_indices.add(0)
        
        items_data = data.get('items_data', {})
        meta_data = data.get('meta_data', {})
        
        needs_update = False
        for idx in active_indices:
            if idx >= total_pages or idx < 0: continue
            if pages[idx] is not None: continue
            
            page_items = virtual_pages[idx]
            page_items_data = {}
            page_meta_data = {}
            for name, item, meta in page_items:
                page_items_data[name] = item
                page_meta_data[name] = meta
                items_data[name] = item
                meta_data[name] = meta
                
            page_layout, _ = await generate(page_items_data, *view, sort_key=sort_key, direction=direction, meta_data=page_meta_data)
            if page_layout:
                pages[idx] = page_layout[0]
                needs_update = True
                
        if needs_update:
            await state.update_data(pages=pages, items_data=items_data, meta_data=meta_data)



    keyboard = list_to_keyboard(pages[current_page], settings['row'], is_premium=settings.get('is_premium', False))

    # Добавляем стрелочки
    keyboard = down_menu(keyboard, len(pages) > 1, settings['lang'], is_premium=settings.get('is_premium', False))

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

    try:
        from bot.modules.tutorial import get_tutorial_step, update_pinned_message
        if await get_tutorial_step(userid) == "profile_inventory":
            await update_pinned_message(userid, chatid, "profile_inventory", settings['lang'], bot, resend=True)
    except Exception as e:
        log(f"swipe_page tutorial resend error: {e}", lvl=2)


async def search_menu(chatid: int, userid: int):
    """ Панель-сообщение поиска
    """

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        settings = data['settings']
        main_message = data['main_message']
        up_message = data['up_message']

    menu_text = t('inventory.search', settings['lang'])
    buttons = {'❌': {"callback_data": 'inventory_search close', "style": "danger"}}
    inl_menu = list_to_inline([buttons])

    text = t('inventory.update_search', settings['lang'])
    keyboard = list_to_keyboard([ {"text": t('buttons_name.cancel', settings['lang']), "style": "danger", "custom_emoji_id": "forbidden"} ], is_premium=settings.get('is_premium', False))
    
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

    buttons.append({'❌': {"callback_data": 'inventory_sort cancel', "style": "danger"}})
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
        filters = data.get('filters', []) or []
        main_message = data['main_message']
        up_message = data['up_message']

    menu_text = t('inventory.choice_filter', settings['lang'])
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    
    # 1. Available types from raw_inventory or DB
    raw_inventory = data.get('raw_inventory', [])
    if not raw_inventory:
        from bot.models.user import User
        raw_inventory, _ = await User.get_inventory(chatid, data.get('exclude_ids', []))
    
    available_types = set()
    for item in raw_inventory:
        i_data = item.get('items_data', {})
        item_id = i_data.get('item_id', '')
        item_cfg = get_data(item_id) if item_id else {}
        itype = item_cfg.get('type')
        if itype:
            available_types.add(get_group_type(itype))

    # Add toggle buttons
    for itype in sorted(available_types):
        type_label = t(f"inventory.filter_types.{itype}", settings['lang'], default=itype)
        if itype in filters:
            builder.button(
                text=type_label,
                callback_data=f"inventory_filter toggle {itype}",
                style="success"
            )
        else:
            builder.button(
                text=type_label,
                callback_data=f"inventory_filter toggle {itype}"
            )

    # Adjust to 2 columns
    builder.adjust(2)

    # Add Clear and Confirm buttons
    all_label = t('inventory.all_filter', settings['lang'], default='Все')
    if not filters:
        builder.row(InlineKeyboardButton(
            text=f"✅ {all_label}",
            callback_data="inventory_filter clear",
            style="success"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=all_label,
            callback_data="inventory_filter clear"
        ))

    builder.row(InlineKeyboardButton(
        text=t('buttons_name.confirm', settings['lang'], default='✅ Подтвердить'),
        callback_data="inventory_filter close",
        style="success"
    ))
    
    inl_menu = builder.as_markup()

    text = t('inventory.update_filter', settings['lang'])
    keyboard = list_to_keyboard([ t('buttons_name.cancel', settings['lang']) ], is_premium=settings.get('is_premium', False))

    if upd_up_m:
        if up_message == 0:
            await bot.send_message(chatid, text, reply_markup=keyboard)
        else:
            new_up = await bot.send_message(chatid, text, reply_markup=keyboard)
            await bot.delete_message(chatid, up_message)

            await state.update_data(up_message=new_up.message_id)

    if main_message == 0:
        new_main = await bot.send_message(
            chatid, menu_text, reply_markup=inl_menu, 
            parse_mode='Markdown')
        await state.update_data(main_message=new_main.message_id)
    else:
        await bot.edit_message_text(
            menu_text, None, chatid, main_message, 
            reply_markup=inl_menu, parse_mode='Markdown')

async def open_inv(chatid: int, userid: int):
    """ Внутренняя фунция для возврата в инвентарь
    """

    state = await get_state(userid, chatid)
    await state.clear()
    await state.set_state(InventoryStates.Inventory)
    await swipe_page(chatid, userid)


