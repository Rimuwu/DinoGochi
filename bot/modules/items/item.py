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
from bot.config import mongo_client
from bot.const import ITEMS
from bot.modules.data_format import random_dict, seconds_to_str, near_key_number
from bot.modules.images import async_open
from bot.modules.localization import get_all_locales, t
from bot.modules.localization import get_data as get_loc_data
from bot.modules.logs import log

from bot.modules.overwriting.DataCalsses import DBconstructor
items = DBconstructor(mongo_client.items.items)

def get_data(item_id: str) -> dict:
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if item_id in ITEMS.keys():
        return ITEMS[item_id]
    else: return {}

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

def get_name(item_id: str, lang: str='en', abilities: dict = {}) -> str:
    """Получение имени предмета"""
    name = ''

    if 'endurance' in abilities:
        endurance = abilities['endurance']
    else: endurance = 0

    if item_id in items_names:
        if lang not in items_names[item_id]: lang = 'en'

        if endurance and 'alternative_name' in items_names[item_id][lang]:
            if str(endurance) in items_names[item_id][lang]['alternative_name']:
                name = items_names[item_id][lang]['alternative_name'][str(endurance)]
            else: 
                name = near_key_number(endurance, items_names[item_id][lang], 'name') #type: ignore
        else:
            name = items_names[item_id][lang]['name']
    else:
        log(f'Имя для {item_id} не найдено')
    return name

def get_description(item_id: str, lang: str='en') -> str:
    """Получение описания предмета"""
    description = ''
   
    if item_id in items_names:
        if lang not in items_names[item_id]:
            lang = 'en'
        description = items_names[item_id][lang].get('description', '')
    return description

def get_item_dict(item_id: str, abilities: dict = {}) -> dict:
    ''' Создание словаря, хранящийся в инвентаре пользователя.\n

        Примеры: 
            Просто предмет
                >>> f(12)
                >>> {'item_id': "12"}

            Предмет с предустоновленными данными
                >>> f(30, {'uses': 10})
                >>> {'item_id': "30", 'abilities': {'uses': 10}}
    '''
    d_it = {'item_id': item_id}
    data = get_data(item_id)

    if 'abilities' in data.keys():
        abl = {}
        for k in data['abilities'].keys():

            if type(data['abilities'][k]) == dict:
                abl[k] = random_dict(data['abilities'][k])

            else:
                abl[k] = data['abilities'][k]

        d_it['abilities'] = abl  # type: ignore

    if abilities != {}:
        if 'abilities' in d_it.keys():
            for ak in abilities:

                if type(abilities[ak]) == dict:
                    d_it['abilities'][ak] = random_dict(abilities[ak])  # type: ignore

                else:
                    d_it['abilities'][ak] = abilities[ak]  # type: ignore
        else: 
            d_it['abilities'] = abilities  # type: ignore

    return d_it

def is_standart(item: dict) -> bool:
    """Определяем ли стандартный ли предмет*.

    Для этого проверяем есть ли у него свои харрактеристик.\n
    Если их нет - значит он точно стандартный.\n
    Если они есть и не изменены - стандартный.
    Если есть и изменены - изменённый.
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

async def AddItemToUser(userid: int, item_id: str, count: int = 1, abilities: dict = {}):
    """Добавление стандартного предмета в инвентарь
    """
    assert count >= 0, f'AddItemToUser, count == {count}'
    log(f"userid {userid}, item_id {item_id}, count {count}", 0, "Add item")

    item = get_item_dict(item_id, abilities)
    find_res = await items.find_one({'owner_id': userid, 
                                     'items_data': item}, {'_id': 1}, comment='AddItemToUser_find_res')
    action = ''

    if find_res: action = 'plus_count'
    if 'abilities' in item or abilities: action = 'new_edited_item' # Хочешь сломать всего бота? Поменяй if на elif
    if not action: action = 'new_item'

    if action == 'plus_count' and find_res:
        await items.update_one({'_id': find_res['_id']}, {'$inc': {'count': count}}, comment='AddItemToUser_1')

    elif action == 'new_edited_item':
        for _ in range(count):
            item_dict = {
                'owner_id': userid,
                'items_data': item,
                'count': 1
            }
            await items.insert_one(item_dict, True, comment='AddItemToUser_new_edited_item')
    else:
        item_dict = {
            'owner_id': userid,
            'items_data': item,
            'count': count
        }
        await items.insert_one(item_dict, comment='AddItemToUser_1')
    return action

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
            count: int = 1, abilities: dict = {}):
    """Удаление предмета из инвентаря
       return
       True - всё нормально, удалил

       False - предмета нет или количесвто слишком большое
    """
    assert count >= 0, f'RemoveItemFromUser, count == {count}'
    log(f"userid {userid}, item_id {item_id}, count {count}", 0, "Remove item")

    item = get_item_dict(item_id, abilities)
    max_count = 0
    find_items = await items.find({'owner_id': userid, 'items_data': item}, 
                            {'_id': 1, 'count': 1}, comment='RemoveItemFromUser_find_items')
    find_list = list(find_items)

    for iterable_item in find_list: max_count += iterable_item['count']
    if count > max_count: return False
    else:
        for iterable_item in find_list:
            if count > 0:
                if count >= iterable_item['count']:
                    await items.delete_one({'_id': iterable_item['_id']}, comment='RemoveItemFromUser_1')

                elif count < iterable_item['count']:
                    await items.update_one({'_id': iterable_item['_id']}, 
                                {'$inc': 
                                    {'count': count * -1}}, comment='RemoveItemFromUser')

                count -= iterable_item['count']
            else: break
        return True

def CalculateDowngradeitem(item: dict, characteristic: str, unit: int):
    """Объясняет что надо сделать с 1-им предметом
       Удалить / изменить или данные действия сделать нельзя
    """
    if item['abilities'][characteristic] > unit:
        new_item = get_item_dict(item['item_id'], item['abilities'])
        new_item['abilities'][characteristic] -= unit

        return {'status': 'edit', 'item': new_item, 'ost': 0}

    else: # <= 
        return {'status': 'remove', 'item': item, 
                'ost': unit - item['abilities'][characteristic]}

async def DeleteAbilItem(item_data: dict, characteristic: str, 
                         unit: int, count: int, userid: int):
    """ return
        - False, {} - Не хватает предметов, {'ost'} - сколько прочности не хватает\n
        - True,  {} - delete (то что надо удалить)\n
                      edit (предмет, что надо изменить)\n
                      set (сколько надо установить хар предмету из edit)
    """
    need_char = unit * count
    retur_dict = {'delete': [], 'edit': '', 'set': 0}
    find_items = await items.find({'owner_id': userid, 
                                   'items_data': item_data}, comment='DeleteAbilItem')

    for item in find_items:
        if need_char <= 0: break
        data: dict = item['items_data']

        if 'abilities' in data and characteristic in data['abilities']:
            item_unit = data['abilities'][characteristic]

            if item_unit > need_char:
                retur_dict['edit'] = item['_id']
                retur_dict['set'] = item_unit - need_char

            elif item_unit == need_char:
                retur_dict['delete'].append(item['_id'])

            elif item_unit < need_char:
                retur_dict['delete'].append(item['_id'])

            need_char -= item_unit

    if need_char > 0:
        # Значит предметов недостаточно 
        return False, {'ost': need_char}

    else:
        # Значит у игрока предметов с хар больше чем надо или именно столько сколько надо.
        return True, retur_dict


async def DowngradeItem(userid: int, item: dict, characteristic: str, unit: int):
    """
        Понижает харрактеристику для предметов с одинаковыми данными из базы
        unit - число понижения харрактеристики для всех предметов
    """
    max_count, max_char = 0, 0
    find_items = await items.find({'owner_id': userid, 
                                   'items_data': item}, comment='DowngradeItem_1')
    find_list = list(find_items)

    for iterable_item in find_list:
        max_count += iterable_item['count']
        max_char += iterable_item['items_data']['abilities'][characteristic]

    if unit > max_char * max_count:
        return {'status': False, 'action': 'unit', 
                'difference': unit - max_char}

    for iterable_item in find_list:
        item_char = iterable_item['items_data']['abilities'][characteristic]
        if unit > 0:
            if unit >= item_char:
                await items.delete_one({'_id': iterable_item['_id']}, comment='DowngradeItem_2')

            elif unit < item_char:
                await items.update_one({'_id': iterable_item['_id']}, 
                            {'$inc': 
                                {f'items_data.abilities.{characteristic}': 
                                    unit * -1}
                                }, comment='DowngradeItem_3')
            unit -= item_char
        else: break

    return {'status': True, 'action': 'deleted_edited'}

async def CheckItemFromUser(userid: int, item_data: dict, count: int = 1) -> dict:
    """Проверяет есть ли count предметов у человека
    """

    find_res = await items.find_one({'owner_id': userid, 
                               'items_data': item_data,
                               'count': {'$gte': count}
                               }, comment='CheckItemFromUser')
    if find_res: 
        return {"status": True, 'item': find_res}
    else:
        find_res = await items.find_one({'owner_id': userid, 
                               'items_data': item_data,
                               'count': {'$gt': 1}
                               }, comment='CheckItemFromUser_1')
        if find_res: difference = count - find_res['count']
        else: difference = count
        return {"status": False, "item": find_res, 'difference': difference}

async def CheckCountItemFromUser(userid: int, count: int, item_id: str, 
                           abilities: dict = {}):
    """ Проверяет не конкретный документ на count а всю базу, возвращая ответ на вопрос - Есть ли у человек count предметов
    """
    item = get_item_dict(item_id, abilities)
    max_count = 0
    find_items = await items.find({'owner_id': userid, 'items_data': item}, 
                            {'_id': 1, 'count': 1}, comment='CheckCountItemFromUser')
    find_list = list(find_items)

    for iterable_item in find_list: max_count += iterable_item['count']
    if count > max_count: return False
    return True

async def check_and_return_dif(userid: int, item_id: str, abilities: dict = {}):
    """ Проверяет не конкретный документ на count а всю базу, возвращая количество
    """
    item = get_item_dict(item_id, abilities)
    max_count = 0
    find_items = await items.find({'owner_id': userid, 'items_data': item}, 
                            {'_id': 1, 'count': 1}, comment='CheckCountItemFromUser')
    find_list = list(find_items)
    for iterable_item in find_list: 
        max_count += iterable_item['count']
    return max_count

async def EditItemFromUser(userid: int, now_item: dict, new_data: dict):
    """Функция ищет предмет по now_item и в случае успеха изменяет его данные на new_data.
    
        now_item - 
        "items_data": {
            "item_id": str,
            "abilities": dict #Есть не всегда
        }
        
        new_data - 
        "items_data": {
            "item_id": str,
            "abilities": dict #Есть не всегда
        }
    }
    """
    find_res = await items.find_one({'owner_id': userid, 
                               'items_data': now_item,
                               }, {'_id': 1}, comment='EditItemFromUser_find_res')
    if find_res:
        await items.update_one({'_id': find_res['_id']}, 
                         {'$set': {'items_data': new_data}}, comment='EditItemFromUser_1')
        return True
    else:
        return False

async def UseAutoRemove(userid: int, item: dict, count: int):
    """Автоматически определяет что делать с предметом, 
       удалить или понизить количество использований
    """

    if 'abilities' in item and 'uses' in item['abilities']:
        # Если предмет имеет свои харрактеристики, а в частности количество использований, то снимаем их, при том мы знаем что предмета в инвентаре и так count
        if item['abilities']['uses'] != -666: # Бесконечный предмет
            res = await DowngradeItem(userid, item, 'uses', count)
            if not res['status']: 
                log(f'Item downgrade error - {res} {userid} {item}', 0)
                return False
    else:
        # В остальных случаях просто снимаем нужное количество
        if 'abilities' in item:
            res = await RemoveItemFromUser(userid, item['item_id'], count, 
                                     item['abilities'])
        else:
            res = await RemoveItemFromUser(userid, item['item_id'], count)
        if not res: 
            log(f'Item remove error {userid} {item}', 3)
            return False
    return True



ids = { # первые 2 символа
    'us': 'uses', 'en': 'endurance',
    'ma': 'mana', 'st': 'stack',
    'in': 'interact', 'da': 'data_id',
    'ty': 'type'
}

def item_code(item: dict, v_id: bool = True) -> str:
    """Создаёт код-строку предмета, основываясь на его
       харрактеристиках.
       
       v_id - определяет добавлять ли буквенный индефикатор
    """
    text = ''

    if v_id: text = f"id{item['item_id']}"

    if 'abilities' in item.keys():
        for key, item in item['abilities'].items():
            if v_id:
                text += f".{key[:2]}{item}"
            else:
                if key[:2] in ids:
                    text += '.'
                    if type(item) == bool:
                        text += str(int(item))
                    else: text += str(item)

    if not v_id: text = text[1:]

    if len(text) > 128:
        log("item_code получился больше чем 128 символов, возможно что он не будет работать в callback data", 4)

    return text

def decode_item(code: str) -> dict:
    """Превращает код в словарь
    """
    split = code.split('.')
    data = {}

    for part in split:
        scode = part[:2]
        value = part[2:]

        if scode == 'id': data['item_id'] = value
        else:
            if 'abilities' not in data.keys(): data['abilities'] = {}
            if value in ['True', 'False']:
                if value == 'True': value = True
                else: value = False

                data['abilities'][ ids[scode] ] = value
            else: 
                if value.isdigit():
                    data['abilities'][ ids[scode] ] = int(value)
                else: data['abilities'][ ids[scode] ] = value
    return data



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
            if 'col' in i:
                col_dict[item] = i['col']
            else: col_dict[item] = 1
        else: 
            if 'col' in i:
                col_dict[item] += i['col']
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
        name = get_name(item['id'], lang)
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
    for i in id_list: dct[i] = dct.get(i, 0) + 1

    for item, col in dct.items():
        name = get_name(item, lang)
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
            example: [{'items_data': {'item_id'}}]
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

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    item_name: str = get_name(item_id, lang)
    rank_item: str = data_item['rank']
    type_item: str = data_item['type']
    loc_d = get_loc_data('item_info', lang)

    if 'class' in data_item and data_item['class'] in loc_d['type_info']:
        type_loc: str = data_item['class']
    else:
        type_loc: str = data_item['type']

    text = ''
    dp_text = ''

    # Шапка и название
    text += loc_d['static']['cap'] + '\n'
    text += loc_d['static']['name'].format(name=item_name) + '\n'

    # Ранг предмета
    rank = loc_d['rank'][rank_item]
    text += loc_d['static']['rank'].format(rank=rank) + '\n'

    # Тип предмета
    type_name = loc_d['type_info'][type_loc]['type_name']
    text += loc_d['static']['type'].format(type=type_name) + '\n'

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
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                item_description=get_description(item_id, lang))

    # Рецепты
    elif type_item == 'recipe':
        cr_list = []
        ignore_craft = data_item.get('ignore_preview', [])
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
        if type_loc == 'near':
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    endurance=item['abilities']['endurance'],
                    min=data_item['damage']['min'],
                    max=data_item['damage']['max'])
        else:
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    ammunition=counts_items(data_item['ammunition'], lang),
                    min=data_item['damage']['min'],
                    max=data_item['damage']['max'])
    # Боеприпасы
    elif type_item == 'ammunition':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                add_damage=data_item['add_damage'])
    # Броня
    elif type_item == 'armor':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                reflection=data_item['reflection'])
    # Рюкзаки
    elif type_item == 'backpack':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                capacity=data_item['capacity'])
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

    # Информация о внутренних свойствах
    if 'abilities' in item.keys():
        for iterable_key in ['uses', 'endurance', 'mana']:
            if iterable_key in item['abilities'].keys():
                text += loc_d['static'][iterable_key].format(
                    item['abilities'][iterable_key], data_item['abilities'][iterable_key]
                ) + '\n'

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

    # Картиночка
    if 'image' in data_item.keys():
        try:
            image = await async_open(f"images/items/{data_item['image']}.png", True)
        except:
            log(f'Item {item_id} image incorrect', 4)

    if type_item == 'special' and data_item['class'] == 'background':
        data_id = item['abilities']['data_id']
        image = await async_open(f"images/backgrounds/{data_id}.png", True)

    if owner:
        text += f'\n\n`{item} {data_item}`'

    return text, image