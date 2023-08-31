"""Пояснение:
    >>> Стандартный предмет - предмет никак не изменённый пользователем, сгенерированный из json.
    >>> abilities - словарь с индивидуальными харрактеристиками предмета, прочность, использования и тд.
    >>> preabil - используется только для предмета создаваемого из базы, используется для создания нестандартного предмета.
    
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

from bot.config import mongo_client
from bot.const import ITEMS
from bot.modules.data_format import random_dict, seconds_to_str
from bot.modules.localization import get_all_locales, t
from bot.modules.localization import get_data as get_loc_data
from bot.modules.logs import log

items_names = {}
items = mongo_client.items.items

def get_data(itemid: str) -> dict:
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if itemid in ITEMS.keys():
        return ITEMS[itemid]
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

def get_name(itemid: str, lang: str='en', endurance: int=0) -> str:
    """Получение имени предмета"""
    name = ''

    if itemid in items_names:
        if lang not in items_names[itemid]: lang = 'en'
        if endurance and 'alternative_name' in items_names[itemid][lang]:
            if str(endurance) in items_names[itemid][lang]['alternative_name']:
                name = items_names[itemid][lang]['alternative_name'][endurance]
            else: 
                name = items_names[itemid][lang]['name']
        else:
            name = items_names[itemid][lang]['name']
    return name

def get_description(itemid: str, lang: str='en') -> str:
    """Получение описания предмета"""
    description = ''
   
    if itemid in items_names:
        if lang not in items_names[itemid]:
            lang = 'en'
        description = items_names[itemid][lang].get('description', '')
    return description

def get_item_dict(itemid: str, preabil: dict = {}) -> dict:
    ''' Создание словаря, хранящийся в инвентаре пользователя.\n

        Примеры: 
            Просто предмет
                >>> f(12)
                >>> {'item_id': "12"}

            Предмет с предустоновленными данными
                >>> f(30, {'uses': 10})
                >>> {'item_id': "30", 'abilities': {'uses': 10}}
    '''
    d_it = {'item_id': itemid}
    data = get_data(itemid)

    if 'abilities' in data.keys():
        abl = {}
        for k in data['abilities'].keys():

            if type(data['abilities'][k]) == int:
                abl[k] = data['abilities'][k]

            elif type(data['abilities'][k]) == dict:
                abl[k] = random_dict(data['abilities'][k])

        d_it['abilities'] = abl #type: ignore

    if preabil != {}:
        if 'abilities' in d_it.keys():
            for ak in d_it['abilities']:
                if ak in preabil.keys():

                    if type(preabil[ak]) == int:
                        d_it['abilities'][ak] = preabil[ak] #type: ignore

                    elif type(preabil[ak]) == dict:
                        d_it['abilities'][ak] = random_dict(preabil[ak]) #type: ignore
        else: 
            d_it['abilities'] = preabil #type: ignore

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
                else:
                    return False
            else:
                return True
        else:
            return True

def AddItemToUser(userid: int, itemid: str, count: int = 1, preabil: dict = {}):
    """Добавление стандартного предмета в инвентарь
    """
    assert count >= 0, f'AddItemToUser, count == {count}'

    item = get_item_dict(itemid, preabil)
    find_res = items.find_one({'owner_id': userid, 'items_data': item}, {'_id': 1})

    if find_res: action = 'plus_count'
    elif 'abilities' in item or preabil: action = 'new_edited_item'
    else: action = 'new_item'

    if action == 'plus_count' and find_res:
        items.update_one({'_id': find_res['_id']}, {'$inc': {'count': count}})
    elif action == 'new_edited_item':
        for _ in range(count):
            item_dict = {
                'owner_id': userid,
                'items_data': item,
                'count': 1
            }
            items.insert_one(item_dict, True)
    else:
        item_dict = {
            'owner_id': userid,
            'items_data': item,
            'count': count
        }
        items.insert_one(item_dict)

    return action

def RemoveItemFromUser(userid: int, itemid: str, 
            count: int = 1, preabil: dict = {}):
    """Удаление предмета из инвентаря
       return
       True - всё нормально, удалил
       
       False - предмета нет или количесвто слишком большое
    """
    assert count >= 0, f'RemoveItemFromUser, count == {count}'

    item = get_item_dict(itemid, preabil)
    max_count = 0
    find_items = items.find({'owner_id': userid, 'items_data': item}, 
                            {'_id': 1, 'count': 1})
    find_list = list(find_items)
    
    for iterable_item in find_list: max_count += iterable_item['count']
    if count > max_count: return False
    else:
        for iterable_item in find_list:
            if count > 0:
                if count >= iterable_item['count']:
                    items.delete_one({'_id': iterable_item['_id']})
                    
                elif count < iterable_item['count']:
                    items.update_one({'_id': iterable_item['_id']}, 
                                {'$inc': 
                                    {'count': count * -1}})
                
                count -= iterable_item['count']
            else: break
        return True

def ReverseCalculateAbilitie(itemid: str, unit: int, characteristic: str):
    """Обратное CalculateAbilitie функция, получает количество 
        харрактеристики и говорит какое количество соответсвует этому количеству харрактеристики.
         
       Пример:
        Предмет, макс прочность 100, переданная прочность 140,
        Вернёт количество - 2 и прочность 40.
    
       Return 
        0 - несоответсвие требованиям функции
    """
    item_data = get_item_dict(itemid)
    
    if 'abilities' not in item_data: return 0, 0 # Нет харрактеристик
    if characteristic not in item_data['abilities']: return 0, 0 # Нет харрактеристики
    
    max_abilitie = item_data['abilities'][characteristic]
    count = unit // max_abilitie
    remains = unit % max_abilitie
    if remains: 
        #Потому что не может быть у нас количество 0
        #и харрактеристика например 40
        count += 1 
    return count, remains

def CalculateDowngradeitem(item: dict, characteristic: str, unit: int):
    """Объясняет что надо сделать с 1-им предметом
       Удалить / изменить или данные действия сделать нельзя
    """
    if item['abilities'][characteristic] > unit:
        new_item = get_item_dict(item['item_id'], item['abilities'])
        new_item['abilities'][characteristic] -= unit
        
        return {'status': 'edit', 'item': new_item}

    elif item['abilities'][characteristic] == unit:
        return {'status': 'remove'}

    else:
        return {'status': 'cannot', 
                'difference': unit - item['abilities'][characteristic]}


def DowngradeItem(userid: int, item: dict, characteristic: str, unit: int):
    """
        Понижает харрактеристику для предметов с одинаковыми данными из базы
        unit - число понижения харрактеристики для всех предметов
    """

    max_count, max_char = 0, 0
    find_items = items.find({'owner_id': userid, 'items_data': item})
    find_list = list(find_items)
    
    for iterable_item in find_list:
        max_count += iterable_item['count']
        max_char += iterable_item['items_data']['abilities'][characteristic]

    if unit > max_char: return {'status': False, 'action': 'unit', 
                                        'difference': unit - max_char}
    
    for iterable_item in find_list:
        item_char = iterable_item['items_data']['abilities'][characteristic]
        if unit > 0:
            if unit >= item_char:
                items.delete_one({'_id': iterable_item['_id']})
                
            elif unit < item_char:
                items.update_one({'_id': iterable_item['_id']}, 
                            {'$inc': 
                                {f'items_data.abilities.{characteristic}': 
                                    unit * -1}
                                })
            unit -= item_char
        else: break
        
    return {'status': True, 'action': 'deleted_edited'}

def CheckItemFromUser(userid: int, item_data: dict, count: int = 1) -> dict:
    """Проверяет есть ли count предметов у человека
    """
    
    find_res = items.find_one({'owner_id': userid, 
                               'items_data': item_data,
                               'count': {'$gte': count}
                               })
    if find_res: 
        return {"status": True, 'item': find_res}
    else:
        find_res = items.find_one({'owner_id': userid, 
                               'items_data': item_data,
                               'count': {'$gt': 1}
                               })
        if find_res: difference = count - find_res['count']
        else: difference = count
        return {"status": False, "item": find_res, 'difference': difference}

def CheckCountItemFromUser(userid: int, count: int, itemid: str, 
                           preabil: dict = {}):
    """ Проверяет не конкретный документ на count а всю базу, возвращая ответ на вопрос - Есть ли у человек count предметов
    """
    item = get_item_dict(itemid, preabil)
    max_count = 0
    find_items = items.find({'owner_id': userid, 'items_data': item}, 
                            {'_id': 1, 'count': 1})
    find_list = list(find_items)
    
    for iterable_item in find_list: max_count += iterable_item['count']
    if count > max_count: return False
    return True

def EditItemFromUser(userid: int, now_item: dict, new_data: dict):
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
    find_res = items.find_one({'owner_id': userid, 
                               'items_data': now_item,
                               }, {'_id': 1})
    if find_res:
        items.update_one({'_id': find_res['_id']}, 
                         {'$set': {'items_data': new_data}})
        return True
    else:
        return False

def UseAutoRemove(userid: int, item: dict, count: int):
    """Автомаатически определяет что делать с предметом, 
       удалить или понизить количество использований
    """

    if 'abilities' in item and 'uses' in item['abilities']:
        # Если предмет имеет свои харрактеристики, а в частности количество использований, то снимаем их, при том мы знаем что предмета в инвентаре и так count
        if item['abilities']['uses'] != -666: # Бесконечный предмет
            res = DowngradeItem(userid, item, 'uses', count)
            if not res['status']: 
                log(f'Item downgrade error - {res} {userid} {item}', 0)
                return False
    else:
        # В остальных случаях просто снимаем нужное количество
        if 'abilities' in item:
            res = RemoveItemFromUser(userid, item['item_id'], count, 
                                     item['abilities'])
        else:
            res = RemoveItemFromUser(userid, item['item_id'], count)
        if not res: 
            log(f'Item remove error {userid} {item}', 3)
            return False
    return True

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
                if type(item) == bool:
                    text += str(int(item))
                else: text += str(item)
    return text

def decode_item(code: str) -> dict:
    """Превращает код в словарь
    """
    split = code.split('.')
    ids = {
        'us': 'uses', 'en': 'endurance',
        'ma': 'mana', 'st': 'stack',
        'in': 'interact'
    }
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
            else: data['abilities'][ ids[scode] ] = int(value)
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

    # Счмтает предметы
    for i in not_sort_list:
        item = i['item']
        if item not in col_dict: col_dict[item] = 1
        else: col_dict[item] += 1

    # Собирает текст
    for i in not_sort_list:
        item = i['item']
        col = col_dict[item]
        
        if i not in check_items:
            text = get_name(item, lang)
            if i['type'] == 'endurance':
                text += f" (⬇ -{i['act']})"
            if col > 1:
                text += f' x{col_dict[item]}'

            items_list.append(text)
            check_items.append(i)

    return f"{separator} ".join(items_list)

def get_case_content(content: list, lang: str, separator: str = ' |'):
    items_list = []
    
    for item in content:
        name = get_name(item['id'], lang)
        percent = int((item['chance'][0] / item['chance'][1]) * 100)
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

def item_info(item: dict, lang: str):
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
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                create=sort_materials(data_item['create'], lang),
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
    # Яйца
    elif type_item == 'egg':
        end_time = seconds_to_str(data_item['incub_time'], lang)
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                inc_time=end_time, 
                rarity=get_loc_data(f'rare.{data_item["inc_type"]}', lang)[1])

    elif type_item == 'recipe':
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                create=sort_materials(data_item['create'], lang),
                materials=sort_materials(data_item['materials'], lang),
                item_description=get_description(item_id, lang))

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
            image = open(f"images/items/{data_item['image']}.png", 'rb')
        except:
            log(f'Item {item_id} image incorrect', 4)

    return text, image