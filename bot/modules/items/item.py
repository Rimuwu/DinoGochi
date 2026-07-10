from bot.models.items import Item
from bot.models.dinosaur import Dino
from bot.models.user import User

"""Пояснение:
    >>> Стандартный предмет - предмет никак не изменённый пользователем, сгенерированный из json.
    >>> abilities - словарь с индивидуальными харрактеристиками предмета, прочность, использования и тд.
    >>> abilities - используется только для предмета создаваемого из базы, используется для создания нестандартного предмета.
    
    >>> Формат предмета из базы данных
    {
      "owner_id": int,
      "items_data": {
        "item_id": str,
        "abilities": dict #Есть не всегда
      },
      "count": int
    }
"""

import json
from typing import Optional

from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.modules.data_format import deepcopy, escape_markdown, random_dict, seconds_to_str, near_key_number
from bot.modules.localization import get_all_locales, t
from bot.modules.localization import get_data as get_loc_data
from bot.modules.logs import log
from bot.modules.items.collect_items import get_all_items
from bot.dataclasess.ns_craft import NSmaterial

ITEMS: dict = get_all_items()

def get_data(item_id: str) -> dict:
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if item_id in ITEMS.keys():
        item_data = deepcopy(ITEMS[item_id])
        return item_data # type: ignore
    else: 
        return {}

def load_items_names() -> dict:
    """Загружает все имена предметов из локалищации в один словарь. 
    """
    items_names = {}
    loc_items_names = get_all_locales('items_names')

    for item_key in ITEMS:
        if item_key not in items_names:
            items_names[item_key] = {}

        for loc_key in loc_items_names.keys():
            loc_name = loc_items_names[loc_key].get(item_key)
            if loc_name:
                items_names[item_key][loc_key] = loc_name
            else:
                items_names[item_key][loc_key] = item_key
    return items_names

items_names = load_items_names()

def get_name(item_id: str, lang: str='en', abilities: dict | None = None) -> str:
    """Получение имени предмета"""
    if abilities is None: abilities = {}

    name = ''

    if 'endurance' in abilities:
        endurance = abilities['endurance']
    else: endurance = 0

    if item_id in items_names:
        if lang not in items_names[item_id]: lang = 'en'

        if 'name' in abilities: name = abilities['name']

        elif endurance and 'alternative_name' in items_names[item_id][lang]:
            if str(endurance) in items_names[item_id][lang]['alternative_name']:
                name = items_names[item_id][lang]['alternative_name'][str(endurance)]
            else: 
                name = near_key_number(endurance, items_names[item_id][lang], 'name') #type: ignore
        else:
            try:
                name = items_names[item_id][lang]['name']
            except:
                log(f'Имя для {item_id} {lang} не найдено!', 4)
    else:
        log(f'Имя для {item_id} не найдено')

    if lang == 'ru' and 'endurance' in abilities and abilities['endurance'] == 0:
        prefix = "Сломанный"
        if item_id in ['spear_regular', 'spear_piercing']:
            prefix = "Сломанная"
        elif item_id in ['shield_magical'] or 'egg' in item_id:
            prefix = "Сломанное"
        parts = name.split(" ", 1)
        if len(parts) > 1 and not parts[0].isalnum():
            name = parts[0] + " " + prefix + " " + parts[1]
        else:
            name = prefix + " " + name

    if abilities and 'lvl' in abilities and abilities['lvl'] > 0:
        name += f" +{abilities['lvl']}"
    return name

def get_description(item_id: str, lang: str='en') -> str:
    """Получение описания предмета"""
    description = ''
   
    if item_id in items_names:
        if lang not in items_names[item_id]:
            lang = 'en'
        description = items_names[item_id][lang].get('description', '')
    return description

def get_item_dict(item_id: str, abilities: dict | None = None) -> dict:
    ''' Создание словаря, хранящийся в инвентаре пользователя.\n

        Примеры: 
            Просто предмет
                >>> f(12)
                >>> {'item_id': "12"}

            Предмет с предустоновленными данными
                >>> f(30, {'uses': 10})
                >>> {'item_id': "30", 'abilities': {'uses': 10}}
    '''
    if abilities is None: abilities = {}

    d_it = {'item_id': item_id}
    data = get_data(item_id)

    # Only include abilities in the dict if the item config actually defines them (non-empty).
    # BaseItem.keys() always includes 'abilities' (Pydantic field with default {}),
    # so we must check the value, not just the key presence.
    config_abilities = data.get('abilities', {}) if hasattr(data, 'get') else {}
    if config_abilities:
        abl = {}
        for k in data['abilities'].keys():

            if type(data['abilities'][k]) == dict:
                if 'type' in data['abilities'][k]:
                    abl[k] = random_dict(data['abilities'][k])
                else:
                    abl[k] = data['abilities'][k]

            else:
                abl[k] = data['abilities'][k]

        d_it['abilities'] = abl  # type: ignore

    if abilities != {}:
        if 'abilities' in d_it.keys():
            for ak in abilities:

                if type(abilities[ak]) == dict:
                    if 'type' in abilities[ak]:
                        d_it['abilities'][ak] = random_dict(abilities[ak])  # type: ignore
                    else:
                        d_it['abilities'][ak] = abilities[ak]  # type: ignore

                else:
                    d_it['abilities'][ak] = abilities[ak]  # type: ignore
        else: 
            d_it['abilities'] = abilities  # type: ignore

    return d_it

def is_standart(item: dict) -> bool:
    """Определяем ли стандартный ли предмет*.
    """
    data = get_data(item['item_id'])

    if list(item.keys()) == ['item_id']: return True
    else:
        if 'abilities' in item.keys():
            if item['abilities']:
                if item.get('abilities', {}) == data.get('abilities', {}):
                    return True
                else: return False
            else: return True
        else: return True

async def AddItemToUser(userid: int, item_id: str, count: int = 1, abilities: dict | None = None):
    """Добавление стандартного предмета в инвентарь"""
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    if user:
        return await user.add_item(item_id, count, abilities)

    from bot.models.items import Item
    return await Item.add(userid, item_id, count, abilities)

async def AddListItems(userid: int, items_l: list[dict]):
    """ items - [ {"item_id":str, "abilities":dict} ]
        Если у предмета есть count то умножает количество 
    """
    repeat_items, res = [], []

    for item in items_l:
        if item not in repeat_items:
            repeat_items.append(item)

            col = items_l.count(item)
            if 'count' in item: col *= item['count']
            abilities = {}

            if "abilities" in item: abilities = item['abilities']
            res_s = await AddItemToUser(userid, item['item_id'], col, abilities)
            res.append(res_s)

    return res

async def RemoveItemFromUser(userid: int, item_id: str, 
            count: int = 1, abilities: dict | None = None):
    """Удаление предмета из инвентаря"""
    from bot.models.items import Item
    return await Item.remove(userid, item_id, count, abilities)

async def transfer_item(from_userid: int, to_userid: int, item_id: str, count: int = 1, abilities: dict | None = None) -> bool:
    """Передача предмета от одного пользователя к другому в рамках транзакции"""
    from bot.modules.overwriting.DataCalsses import Transaction
    async with Transaction():
        if await RemoveItemFromUser(from_userid, item_id, count, abilities):
            await AddItemToUser(to_userid, item_id, count, abilities)
            return True
    return False

async def DeleteAbilItem(item_data: dict, characteristic: str, unit: int, count: int, userid: int):
    """Удаление прочности/характеристики предмета"""
    from bot.models.items import Item
    return await Item.delete_abilities(item_data, characteristic, unit, count, userid)

async def DowngradeItem(userid: int, item: dict, characteristic: str, amount: int):
    """Понижает характеристику для предметов с одинаковыми данными из базы"""
    from bot.models.items import Item
    return await Item.downgrade(userid, item, characteristic, amount)

async def CheckItemFromUser(userid: int, item_data: dict, count: int = 1) -> dict:
    """Проверяет есть ли count предметов у человека"""
    from bot.models.items import Item
    return await Item.check_item(userid, item_data, count)

async def CheckCountItemFromUser(userid: int, count: int, item_id: str, 
                           abilities: dict | None = None):
    """Проверяет всю базу на наличие нужного количества предметов"""
    from bot.models.items import Item
    return await Item.check_count(userid, count, item_id, abilities)

async def check_and_return_dif(userid: int, item_id: str, abilities: dict | None = None):
    """Возвращает общее количество предметов игрока"""
    from bot.models.items import Item
    return await Item.check_and_return_dif(userid, item_id, abilities)

async def EditItemFromUser(userid: int, now_item: dict, new_data: dict):
    """Изменение характеристик предмета"""
    from bot.models.items import Item
    find_res = await Item.find_one(Item.owner_id == userid, Item.items_data == now_item)

    if find_res:
        if find_res.count > 1:
            now_abilities = find_res.items_data.get('abilities', {})
            now_id = find_res.items_data['item_id']

            item_id = new_data['item_id']
            new_abilities = new_data.get('abilities', {})

            await AddItemToUser(userid, item_id, 1, new_abilities)
            await RemoveItemFromUser(userid, now_id, 1, now_abilities)
        else:
            find_res.items_data = new_data
            await find_res.save()
        return True
    return False

async def UseAutoRemove(userid: int, item: dict, count: int):
    """Автоматически определяет что делать с предметом"""
    if 'abilities' in item and 'uses' in item['abilities']:
        if item['abilities']['uses'] != -666:
            res = await DowngradeItem(userid, item, 'uses', count)
            if not res['status']: 
                log(f'Item downgrade error - {res} {userid} {item}', 0)
                return False
    else:
        abil = item.get('abilities', {})
        res = await RemoveItemFromUser(userid, item['item_id'], count, abil)

        if not res:
            log(f'Item remove error {userid} {item}', 3)
            return False
    return True

async def item_code(item_dict: Optional[dict] = None, 
              item_id: Optional[ObjectId] = None, 
              userid: Optional[int] = None,
              data_mode: bool = True) -> str:
    """Создаёт код-строку предмета через Redis с TTL 24 часа.
    """
    import hashlib
    import json
    import uuid
    from bot.redismanager import redis_set, redis_get
    from bot.models.items import Item

    if item_dict is None:
        item_dict = {}

    resolved_dict = dict(item_dict)

    if item_id is not None:
        db_item = await Item.find_one(Item.id == item_id)
        if db_item:
            resolved_dict = db_item.items_data

    # Generate a deterministic hash for the resolved_dict and userid
    hash_data = {
        'resolved_dict': resolved_dict,
        'userid': userid,
        'item_id': str(item_id) if item_id else None
    }
    
    serialized = json.dumps(hash_data, sort_keys=True, default=str)
    h = hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:16]
    code = f"it:{h}"
    
    existing = await redis_get(code)
    
    # Collision detection: if the code exists but contains different data, rehash with a salt
    salt = ""
    while existing and existing != resolved_dict:
        salt = uuid.uuid4().hex[:4]
        serialized_coll = json.dumps({**hash_data, 'salt': salt}, sort_keys=True, default=str)
        h = hashlib.sha256(serialized_coll.encode('utf-8')).hexdigest()[:16]
        code = f"it:{h}"
        existing = await redis_get(code)
        
    await redis_set(code, resolved_dict, ex=86400)
    return code

async def decode_item(str_id: str) -> dict:
    """Превращает код из Redis или ObjectId из базы обратно в словарь.
    """
    from bot.redismanager import redis_get
    from bot.models.items import Item
    from bson.objectid import ObjectId

    if not str_id:
        return {}

    if str_id.startswith("it:"):
        res = await redis_get(str_id)
        if isinstance(res, dict):
            if 'items_data' in res:
                return res
            return {'items_data': res}
        return {}

    # Check if the code is a raw 24-character hexadecimal ObjectId
    if len(str_id) == 24 and all(c in '0123456789abcdefABCDEF' for c in str_id):
        try:
            db_item = await Item.find_one(Item.id == ObjectId(str_id))
            if db_item:
                return {
                    '_id': db_item.id,
                    'count': db_item.count,
                    'items_data': db_item.items_data,
                    'owner_id': db_item.owner_id
                }
        except Exception:
            pass

    return {}


def sort_materials(not_sort_list: list, lang: str, 
                   separator: str = ',') -> str:
    """Создание сообщение нужных материалов для крафта

    Args:
        not_sort_list (list): Список с материалами из базы предметов
          example: [{"item": "26", "type": "delete"}, 
                    {"item": "26", "type": "delete"}]
        lang (str): язык
        separator (str, optional): Разделитель материалов. Defaults to ','.

    Returns:
        str: Возвращает строку для вывода материалов крафта
    """
    col_dict, items_list, check_items = {}, [], []

    # Считает предметы
    for i in not_sort_list:
        item = i['item']
        if isinstance(item, list) or isinstance(item, dict):
            item = json.dumps(item)

        if item not in col_dict:
            if 'count' in i:
                col_dict[item] = i['count']
            else: col_dict[item] = 1
        else: 
            if 'count' in i:
                col_dict[item] += i['count']
            else: col_dict[item] += 1

    # Собирает текст
    for i in not_sort_list:
        item = i['item']
        abilities = i.get('abilities', {})
        text = ''

        if i not in check_items:
            if isinstance(item, str):
                col = col_dict[item]
                text = get_name(item, lang, abilities)

            elif isinstance(item, list):
                lst = []
                col = col_dict[json.dumps(i['item'])]
                for i_item in item: lst.append(get_name(i_item, lang, abilities))

                text = f'({" | ".join(lst)})'

            elif isinstance(item, dict):
                col = col_dict[json.dumps(item)]
                text = "(" + t(f'groups.{item["group"]}', lang) + ")"

            if i['type'] == 'endurance':
                text += f" (⬇ -{i['act']})"
            if col > 1:
                text += f' x{col}'

            items_list.append(text)
            check_items.append(i)

    return f"{separator} ".join(items_list)

def get_case_content(content: list, lang: str, separator: str = ' |'):
    items_list = []

    for item in content:
        
        if isinstance(item['id'], str):
            name = get_name(item['id'], lang)

        if isinstance(item['id'], dict):
            # В материалах указана группа
            group = item["id"]["group"]
            name = "(" + t(f'groups.{group}', lang) + ")"

        elif isinstance(item['id'], list):
            # В материалах указан список предметов которых можно использовать
            names = []
            for i in item['id']: names.append(get_name(i, lang))
            name = '(' + ', '.join(names) + ')'

        percent = round((item['chance'][0] / item['chance'][1]) * 100, 4)
        if item['col']['type'] == 'random':
            col = f"x({item['col']['min']} - {item['col']['max']})"
        else:
            col = f"x{item['col']['act']}"
        
        items_list.append(
            f'{name} {col} {percent}%'
        )
    return f"{separator} ".join(items_list)

def counts_items(id_list: list, lang: str, separator: str = ','):
    """Считает предмете, полученные в формате строки, 
       и преобразовывает в текс.

    Args:
        id_list (list): Список с предметами в формате строки
            example: ["1", "12"]
        lang (str): Язык
        separator (str, optional): Символы, разделяющие элементы. Defaults to ','.

    Returns:
        str: Возвращает строку для вывода материалов крафта
    """
    dct, items_list = {}, []
    for i in id_list:
        if isinstance(i, str):
            dct[i] = dct.get(i, 0) + 1

        elif isinstance(i, (dict, NSmaterial)):
            item_i = i['item_id']
            count_i = i['count']

            dct[item_i] = dct.get(item_i, 0) + count_i


    for item, col in dct.items():
        if item in items_names:
            name = get_name(item, lang)
        else:
            group_name = t(f"groups.{item}", lang)
            if "groups." not in group_name:
                name = group_name
            else:
                name = item.capitalize()
        if col > 1: name += f" x{col}"

        items_list.append(name)

    if items_list:
        return f"{separator} ".join(items_list)
    else: return '-'

def get_items_names(items_list: list[dict], lang: str, separator: str = ','):
    """Считает предмете, полученные в формате строки, 
       и преобразовывает в текс.

    Args:
        id_list (list): Список с предметами
            example: [{'items_data': {'item_id'}, 'count': Optional[int]}]
        lang (str): Язык
        separator (str, optional): Символы, разделяющие элементы. Defaults to ','.

    Returns:
        str: Возвращает строку с предметами
    """
    dct, i_names = {}, []
    for i in items_list: 
        add_count = i.get('count', 1)
        dct_to_str = json.dumps(i)
        dct[dct_to_str] = dct.get(dct_to_str, 0) + add_count

    for item_s, col in dct.items():
        item = json.loads(item_s)
        item_data = item.get(
            'items_data', item.get('item', {})
        )

        items_id = item_data['item_id']
        abilities = item_data.get('abilities', {})
        
        name = get_name(items_id, lang, abilities)
        if col > 1: name += f" x{col}"
        i_names.append(name)

    if i_names:
        return f"{separator} ".join(i_names)
    else: return '-'


async def item_info(item: dict, lang: str, owner: bool = False):
    """Собирает информацию и предмете, пригодную для чтения

    Args:
        item (dict): Сгенерированный словарь данных предмета
        lang (str): Язык

    Returns:
        Str, Image
    """
    standart = ['dummy', 'material']
    image = None
    
    if 'item_id' not in item and 'items_data' in item:
        item = item['items_data']

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    item_name: str = get_name(item_id, lang)
    rank_item: str = data_item['rank']
    type_item: str = data_item['type']
    loc_d = get_loc_data('item_info', lang)

    if 'class' in data_item and data_item['class'] in loc_d['type_info']:
        type_loc: str = data_item['class']
    elif data_item.get('type') in loc_d['type_info']:
        type_loc: str = data_item['type']
    else:
        type_loc: str = 'near' if data_item.get('type') == 'weapon' else 'dummy'

    text = ''
    dp_text = ''

    # Шапка и название
    text += loc_d['static']['cap'] + '\n'
    text += loc_d['static']['name'].format(name=item_name) + '\n'

    # Ранг предмета
    rank = loc_d['rank'][rank_item]
    text += loc_d['static']['rank'].format(rank=rank) + '\n'

    # Тип предмета
    type_info_dict = loc_d['type_info'].get(type_loc)
    if type_info_dict and 'type_name' in type_info_dict:
        type_name = type_info_dict['type_name']
    else:
        type_name = type_loc.capitalize()
    text += loc_d['static']['type'].format(type=type_name) + '\n'

    # Уровень предмета — только для аксессуаров и оружия
    accessory_types = ['game', 'sleep', 'journey', 'collecting', 'weapon', 'armor', 'backpack']
    if type_item in accessory_types:
        lvl = item.get('abilities', {}).get('lvl', 0)
        max_lvl = 10 if data_item.get('type') == 'weapon' else 5
        text += loc_d['static'].get('lvl', '├ Уровень: +{lvl}').format(lvl=lvl, max_lvl=max_lvl) + '\n'

    if 'abilities' in item.keys():
        if 'author' in item['abilities'].keys():
            author_user = await User.find_one(User.userid == item['abilities']['author'])

            if author_user: author_name = author_user.name
            else: author_name = loc_d['static']['unnamed_author']

            text += loc_d['static']['author'].format(
                author=author_name
                ) + '\n'

    # Быстрая обработка предметов без фич
    if type_item in standart:
        dp_text += loc_d['type_info'][type_loc]['add_text']

    #Еда
    elif type_item == 'eat':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(act=data_item['act'])

    # Аксы
    elif type_item in ['game', 'sleep', 'journey', 'collecting']:
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                item_description=get_description(item_id, lang))

    # Книга
    elif type_item == 'book':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                item_description=get_description(item_id, lang))

    # Специальные предметы
    elif type_item == 'special':
        if data_item.get('class') == 'custom_book' and item.get('abilities', {}).get('content'):
            book_content = item['abilities']['content']
            if len(book_content) > 300:
                book_content = book_content[:300] + "..."
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    item_description=book_content)
        else:
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    item_description=get_description(item_id, lang))

        if data_item['class'] == 'transport':
            if item.get('abilities', {}).get('data_id', 0) != 0:
                dino = await Dino.find_one(Dino.alt_id == item['abilities']['data_id'])
                if dino:
                    text += loc_d['static']['trs_dino'].format(
                        dino=escape_markdown(dino.name), hp=dino.stats['heal']
                    )

    # Рецепты
    elif type_item == 'recipe':
        cr_list = []
        ignore_craft = data_item.get('ignore_preview', [])
        if not isinstance(ignore_craft, list):
            ignore_craft = []
        for key, value in data_item['create'].items():
            if key not in ignore_craft:
                cr_list.append(sort_materials(value, lang))

        if 'time_craft' in data_item:
            dp_text += loc_d['static']['time_craft'].format(
                times=seconds_to_str(data_item['time_craft'], lang))
            dp_text += '\n'

        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                create=' | '.join(cr_list),
                materials=sort_materials(data_item['materials'], lang),
                item_description=get_description(item_id, lang))
    # Оружие
    elif type_item == 'weapon':
        damage_data = get_item_damage(item) or {"min": 0, "max": 0}
        if type_loc == 'near':
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    endurance=item.get('abilities', {}).get('endurance', 0),
                    min=damage_data['min'],
                    max=damage_data['max'])
        else:
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    ammunition=counts_items(data_item.get('ammunition', []), lang),
                    min=damage_data['min'],
                    max=damage_data['max'])
    # Боеприпасы
    elif type_item == 'ammunition':
        add_effects = data_item.get('add_effects', [])
        effects_translated = []
        for eff in add_effects:
            eff_translated = t(f"combat_properties.effects.{eff}", lang)
            if "combat_properties." in eff_translated:
                eff_translated = t(f"combat_properties.names.{eff}", lang)
                if "combat_properties." in eff_translated:
                    eff_translated = eff.capitalize()
            effects_translated.append(eff_translated)
        
        if effects_translated:
            effects_str = ", ".join(effects_translated)
        else:
            effects_str = t("item_info.static.none", lang, default="Нет")

        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                add_damage=data_item['add_damage'],
                effects=effects_str)
    # Броня
    elif type_item == 'armor':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                reflection=get_item_reflection(item))
    # Рюкзаки
    elif type_item == 'backpack':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                capacity=get_item_capacity(item))
    # Кейсы
    elif type_item == 'case':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                content=get_case_content(data_item['drop_items'], lang, '\n'))
        desc = get_description(item_id, lang)
        if desc: dp_text += f"\n\n{desc}"

    # Яйца
    elif type_item == 'egg':
        end_time = seconds_to_str(data_item['incub_time'], lang)
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                inc_time=end_time, 
                rarity=get_loc_data(f'rare.{data_item["inc_type"]}', lang)[1])

    # Ускорение инкубации
    elif type_item == 'incubation_boost':
        boost_time = seconds_to_str(data_item['time_boost'], lang)
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                boost_time=boost_time,
                item_description=get_description(item_id, lang))

    # Бустеры тренировок
    elif type_item == 'training_boost':
        boost_time = seconds_to_str(data_item['duration'], lang)
        bonus_pct = int(data_item['bonus_percent'] * 100)
        act_key = f"commands_name.skills_actions.{data_item['activity_type']}"
        act_name = t(act_key, lang)
        effect_label = loc_d['static'].get('effect', 'Effect')
        effect_format = loc_d['static'].get('training_boost_effect', '⚡ *+{bonus}%* to training in ({activity}) for {duration}')
        effect_text = effect_format.format(bonus=bonus_pct, activity=act_name, duration=boost_time)
        desc = get_description(item_id, lang)
        if desc:
            dp_text += f"*├* {effect_label}: {effect_text}\n*└* {desc}"
        else:
            dp_text += f"*└* {effect_label}: {effect_text}"

    # Руны
    elif type_item == 'rune':
        desc = get_description(item_id, lang)
        if desc: dp_text += f"*└* {desc}"

    # Информация о внутренних свойствах
    if 'abilities' in item.keys():
        for iterable_key in ['uses', 'endurance', 'mana']:
            if iterable_key in item['abilities'].keys():
                max_val = get_item_endurance_max(item) if iterable_key == 'endurance' else data_item.get('abilities', {}).get(iterable_key, 0)
                val = item['abilities'][iterable_key]
                pct_str = ""
                if iterable_key in ['uses', 'endurance'] and max_val > 0:
                    pct = int((val / max_val) * 100)
                    pct_str = f" ({pct}%)"
                text += loc_d['static'][iterable_key].format(
                    val, max_val
                ) + pct_str + '\n'

    text += dp_text
    item_bonus = data_item.get('buffs', [])
    add_bonus, add_penaltie = [], []

    for bonus in item_bonus:
        if item_bonus[bonus] > 0:
            add_bonus.append(loc_d['bonuses']['+' + bonus].format(
                item_bonus[bonus]))
        else:
            add_penaltie.append(loc_d['penalties']['-' + bonus].format(
                item_bonus[bonus]))

    if add_bonus:
        text += loc_d['static']['add_bonus']

        for i in add_bonus:
            if i == add_bonus[-1]:
                text += f'*└* {i}'
            else: 
                text += f'*├* {i}\n'

    if add_penaltie:
        text += loc_d['static']['add_penaltie']

        for i in add_penaltie:
            if i == add_penaltie[-1]:
                text += '*└* '
            else: text += '*├* '
            text += i

    item_states = data_item.get('states', [])
    if item_states:
        text += loc_d['static']['add_states']

        for state in item_states:
            unit = state.get('unit', 0)
            str_time = seconds_to_str(state['time'], lang)

            state_text: str = loc_d['item_states'][
                '-' if unit < 0 else '+' + state['char']
                ]
            state_text = state_text.format(unit, str_time)

            if state == item_states[-1]:
                text += f'*└* {state_text}'
            else:
                text += f'*├* {state_text}\n'

    # Картиночка
    if 'image' in data_item.keys() and data_item['image']:
        try:
            image = f"images/items/{data_item['image']}.png"
        except:
            log(f'Item {item_id} image incorrect', 4)

    if type_item == 'special' and data_item['class'] == 'background':
        data_id = item.get('abilities', {}).get('data_id', 0)
        image = f"images/backgrounds/{data_id}.png"

    return text, image


def get_item_level(item: dict) -> int:
    """Возвращает уровень предмета из abilities (по умолчанию 0)."""
    return item.get('abilities', {}).get('lvl', 0)


def get_lvl_data(data_item: dict, lvl: int) -> Optional[dict]:
    """Возвращает данные о ближайшем меньшем или равном уровне из lvls."""
    if lvl <= 0:
        return None
    lvls = data_item.get('lvls', {})
    if not lvls:
        return None
    if str(lvl) in lvls:
        return lvls[str(lvl)]
    
    # Находим ближайший меньший уровень
    valid_lvls = []
    for k in lvls.keys():
        try:
            k_int = int(k)
            if k_int <= lvl:
                valid_lvls.append(k_int)
        except ValueError:
            continue
    if valid_lvls:
        best_lvl = max(valid_lvls)
        return lvls[str(best_lvl)]
    return None


def get_item_damage(item: dict) -> Optional[dict]:
    """Возвращает урон предмета с учетом уровня."""
    lvl = get_item_level(item)
    data_item = get_data(item['item_id'])
    if lvl > 0:
        lvl_data = get_lvl_data(data_item, lvl)
        if lvl_data and 'damage' in lvl_data:
            return lvl_data['damage']
    return data_item.get('damage')


def get_item_endurance_max(item: dict) -> Optional[int]:
    """Возвращает максимальную прочность с учетом уровня."""
    lvl = get_item_level(item)
    data_item = get_data(item['item_id'])
    if lvl > 0:
        lvl_data = get_lvl_data(data_item, lvl)
        if lvl_data and 'endurance_max' in lvl_data:
            return lvl_data['endurance_max']
    if 'endurance_max' in data_item:
        return data_item['endurance_max']
    return data_item.get('abilities', {}).get('endurance')


def get_item_reflection(item: dict) -> int:
    """Возвращает защиту/отражение брони с учетом уровня."""
    lvl = get_item_level(item)
    data_item = get_data(item['item_id'])
    if lvl > 0:
        lvl_data = get_lvl_data(data_item, lvl)
        if lvl_data and 'reflection' in lvl_data:
            return lvl_data['reflection']
    return data_item.get('reflection', 0)


def get_item_capacity(item: dict) -> int:
    """Возвращает вместимость рюкзака с учетом уровня."""
    item_id = item.get('item_id', '')
    lvl = get_item_level(item)
    data_item = get_data(item_id)
    if lvl > 0:
        lvl_data = get_lvl_data(data_item, lvl)
        if lvl_data and 'capacity' in lvl_data:
            return lvl_data['capacity']
    return data_item.get('capacity', 0)


def get_item_effectiv(item: dict) -> int:
    """Возвращает эффективность инструментов с учетом уровня."""
    lvl = get_item_level(item)
    data_item = get_data(item['item_id'])
    if lvl > 0:
        lvl_data = get_lvl_data(data_item, lvl)
        if lvl_data and 'effectiv' in lvl_data:
            return lvl_data['effectiv']
    return data_item.get('effectiv', 1)


def get_item_ability(item: dict, key: str, default=None):
    """Возвращает значение характеристики из abilities предмета (сначала проверяется перегрузка уровня)."""
    lvl = get_item_level(item)
    data_item = get_data(item['item_id'])
    if lvl > 0:
        lvl_data = get_lvl_data(data_item, lvl)
        if lvl_data and 'abilities' in lvl_data and key in lvl_data['abilities']:
            return lvl_data['abilities'][key]
    if 'abilities' in item and key in item['abilities']:
        return item['abilities'][key]
    return data_item.get('abilities', {}).get(key, default)
