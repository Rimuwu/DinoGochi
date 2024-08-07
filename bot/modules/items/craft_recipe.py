
import random
from bot.const import GAME_SETTINGS
import pprint
from typing import Any, Union
from bot.config import mongo_client
from bot.modules.data_format import list_to_inline, random_code, random_data
from bot.modules.inventory_tools import inventory_pages
from bot.modules.items.item import AddItemToUser, CheckCountItemFromUser, DeleteAbilItem, RemoveItemFromUser, UseAutoRemove, check_and_return_dif, counts_items, get_name, get_data, item_code, item_info
from bot.modules.items.items_groups import get_group
from bot.modules.localization import t
from bot.modules.markup import markups_menu
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import get_inventory_from_i
from bot.exec import bot
from bot.modules.user.user import experience_enhancement

from bot.modules.overwriting.DataCalsses import DBconstructor
items = DBconstructor(mongo_client.items.items)

"""
    "clothing_recipe_new": {
        "create": {
            "main": [ // Тип создаваемого рецепта, main используется для отображения в инфо, создаётся по умолчанию и должен быть всегда
                {
                    "item": "leather_clothing", // Создаваемый предмет
                    "type": "create", // Тут create | repair (не создан)
                    "abilities": {}, // Характеристики предмета
                    "col": 1 // Количество создания вместо повторов
                }
            ],
            "carrot": [ // Тип создаваемого рецепта, main используется для отображения в инфо, создаётся по умолчанию и должен быть всегда
                {
                    "item": "leather_clothing", // Создаваемый предмет
                    "type": "create", // Тут create | repair (не создан)
                    "abilities": {"act": { "random-int": [2, 10] }}, // Рандомная число от 2 до 10
                    // После, если в списке 2 элемента - и оба число - randint иначе choice
                    "col": 1 // Количество создания вместо повторов
                }
            ]
        },
        "materials": [
            {
                "item": "skin", // Удаляемый предмет
                "type": "delete", // delete | endurance удаление | понижение характеристики предмета 
                "col": 5 // col - delete | act - сколько нужно отнять 
                "abilities": {}, // Характеристики предмета
            },
            {
                "item": {"group": "vegetables"}, // Предложит выбрать из группы предметов овощей (те что есть в инвентаре)
                "type": "delete", // delete | endurance удаление | понижение характеристики предмета 
                "col": 5, // col - delete | act - сколько нужно отнять 
                "save_choose": true // По умолчанию поставить в коде False
                // В случае если true, код будет искать в create ключ с выбранным предметом
                // Например выбрали carrot - будут выданы предметы не из main, а carrot
                // Если нет ключа carrot создать main
                // Если выбора несколько ставить между выбором "-"
            },
            {
                "item": ["carrot", "leather"], // Предложет выбрать из списка предметов (те что есть в инвентаре)
                "type": "delete", // delete | endurance удаление | понижение характеристики предмета 
                "col": 5, // col - delete | act - сколько нужно отнять 
                "copy_abilitie": "key" // Будет копировать ключь из выбранного предмета и добавлять к новому
                // код будет искать в create ключ с выбранным предметом
                // Например выбрали carrot - будут выданы предметы не из main, а carrot
                // Если нет ключа carrot создать main
                // Если выбора несколько ставить между выбором "-"
            }
        ],
        "abilities": { // Характеристики самого рецепта
            "uses": 3
        },

        "rank": "rare",
        "image": "recipe",
        "type": "recipe",
        "ignore_preview": [], // Указать какие итоги крафта не отображать в инфо о крафте
        
        "time_craft": 10000, # Время крафта 

        "groups": [] // Группы которые могут быть использованы для отображения
    }
"""

async def craft_recipe(userid: int, chatid: int, lang: str, item: dict, count: int=1):
    """ Сформировать список проверяемых предметов, подготовить данные для выбора предметов
    """

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)

    materials, steps = [], []
    a = -1

    for material in data_item['materials']:
        if 'col' not in material: material['col'] = 1

        material['col'] *= count
        if not isinstance(material['item'], str):

            if isinstance(material['item'], dict):
                # В материалах указана группа
                find_items = get_group(material['item']['group'])

            elif isinstance(material['item'], list):
                # В материалах указан список предметов которых можно использовать
                find_items = material['item']


            if 'abilities' in material:
                find_items = list(
                        map(lambda i: {'item_id': i, 
                                       'abilities': material['abilities']}, 
                            find_items)
                    )
            else:
                find_items = list(
                        map(lambda i: {'item_id': i}, find_items)
                    )

            inv = await get_inventory_from_i(userid, find_items)

            if not inv:
                await bot.send_message(chatid, 
                    t('item_use.recipe.not_choosed', lang), 
                    parse_mode='Markdown', 
                    reply_markup=await markups_menu(userid, 'last_menu', lang))
                return

            elif len(inv) == 1:
                material['item'] = inv[0]['item']['item_id']
                materials.append(material)

            elif len(inv) > 1:
                a += 1
                name = f'{a}_step'
                steps.append(
                    {
                        'type': 'inv',
                        'name': name,
                        'data': {
                            'inventory': inv,
                            'changing_filters': False
                        },
                        'translate_message': True,
                        'message': {'text': 'item_use.recipe.consumable_item'}
                    }
                )

                material['item'] = name
                materials.append(material)
        else:
            materials.append(material)

    if len(steps) > 0:

        transmitted_data = {
            'materials': materials,
            'count': count,
            'item': item
        }

        await ChooseStepState(end_choose_items, userid, chatid, lang, steps, transmitted_data)

    else:
        data = {
            "choosed_items": []
        }
        await check_items_in_inventory(materials, item, count, 
                                       userid, chatid, lang, data)


async def end_choose_items(items: dict, transmitted_data: dict[str, Any]):
    """ Смотрим на данные, преобразовываем так, чтобы они подошли под check_items_in_inventory
    """
    materials, count, item, userid, chatid, lang, steps = transmitted_data.values()
    choosed_items = [] # Записываем какие предметы были выбраны

    # Заменяем данные в материалах на выбранные предметы
    data_of_keys = {}
    for key_material, choosed in items.items():
        choosed: dict

        data_of_keys[key_material] = choosed
        choosed_items.append(choosed['item_id'])

    for material in materials:
        material: dict

        if material['item'] in data_of_keys:
            material['item'] = data_of_keys[ material['item'] ]['item_id']

    data = {
        "choosed_items": choosed_items
    }
    await check_items_in_inventory(materials, item, count, 
                                   userid, chatid, lang, data)


async def check_items_in_inventory(materials, item, count, 
                                   userid, chatid, lang, data: dict):
    
    """ Должна проверить предметы, выявить есть ли у игрока для каждого предмета разные вариации и если да - дать выбрать их (сделать через выдачу краткой информации и кнопки - применить)
    """
    finded_items, steps, not_find = [], [], []

    a = -1
    for material in materials:
        find_items = await items.find({'owner_id': userid, 
                                       'items_data.item_id': material['item']},
                                      {'_id': 0, 'owner_id': 0},
                     comment='check_items_in_inventory')

        # Нет предметов
        if len(find_items) == 0:
            not_find.append({'item': material['item'], 'diff': material['col']})
            continue

        else:
            find_set = []
            for i in find_items:
                if i['items_data'] not in find_set:
                    find_set.append(i['items_data'])

            # У предметов нет альтернатив
            if len(find_set) == 1:
                count_material = await check_and_return_dif(userid, **i['items_data'])
                if count_material >= material['col']:
                    finded_items.append(
                        {'item': i['items_data'],
                         'count': material['col']}
                    )
                else:
                    not_find.append({'item': i['items_data'], 
                                     'diff': material['col'] - count_material})
                    continue

            # Есть варианты для выбора
            elif len(find_set) > 1:
                a += 1
                name = f'{a}_step'
                steps.append(
                    {
                        'type': 'inv',
                        'name': name,
                        'data': {
                            'inventory': find_items,
                            'changing_filters': False,
                            'inline_func': send_item_info,
                            'inline_code': random_code()
                        },
                        'translate_message': False,
                        'message': {'text': t('item_use.recipe.choose_copy', lang, 
                                              item_name=get_name(material['item'], lang))}
                    }
                )
                finded_items.append({'item': name, 
                                     'count': material['col']})

    if not_find:
        nt_materials = []
        for i in not_find:
            nt_materials.append(
                f'{get_name(i["item"], lang)} x{i["diff"]}'
            )

        text = t('item_use.recipe.not_enough_m', lang, materials=', '.join(nt_materials))
        await bot.send_message(chatid, 
                    text, 
                    parse_mode='Markdown', 
                    reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    elif steps:
        transmitted_data = {
            'finded_items': finded_items,
            'data': data,
            'count': count,
            'item': item
        }

        await ChooseStepState(pre_check, userid, chatid, lang, 
                              steps, transmitted_data)

    else:
        await check_endurance_and_col(finded_items, count, item, 
                                      userid, chatid, lang, data)

async def send_item_info(item: dict, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    custom_code = transmitted_data['inline_code']

    text, image = await item_info(item, lang)
    markup = list_to_inline([
        {t('item_use.recipe.inl_button_conf', lang): 
            f'inventoryinline {custom_code} {item_code(item)}'}
    ])

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

async def pre_check(items: dict, transmitted_data):
    finded_items, data, count, item, userid, chatid, lang, steps = transmitted_data.values()
    result_list = []

    for i in finded_items:
        if isinstance(i['item'], dict):
            result_list.append(i)

        elif isinstance(i['item'], str):
            result_list.append({'item': items[i['item']]})

    await check_endurance_and_col(result_list, count, 
                                  item, userid, chatid, lang, data)

async def check_endurance_and_col(finded_items, count, item,
                                  userid, chatid, lang, data):

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    materials = finded_items

    data['end'] = []

    for material in data_item['materials']:
        ind = data_item['materials'].index(material)
        materials[ind]['type'] = material['type']

    not_found = [] 
    for material in materials:
        ind = materials.index(material)

        if material['type'] == 'delete':
            mat_col = await check_and_return_dif(userid, **material['item'])
            if mat_col < material['count']:
                not_found.append(
                    {'item': material['item']['item_id'], 'type': material['type'],
                     'count': material['count'] - mat_col
                     }
                )
            else:
                dct_data = material
                dct_data['type'] = material['type']
                data['end'].append(dct_data)

        elif material['type'] == 'endurance':
            status, dct_data = await DeleteAbilItem(material['item'], 'endurance', 
                                data_item['materials'][ind]['act'], count, userid)
            if not status:
                not_found.append(
                    {'item': material['item']['item_id'], 'type': material['type'],
                     'count': dct_data['ost']
                     }
                )
            else:
                dct_data['type'] = material['type']
                data['end'].append(dct_data)

    if not_found:
        nt_materials = []
        for i in not_found:
            if i['type'] == 'delete':
                nt_materials.append(
                    f'{get_name(i["item"], lang)} x{i["count"]}'
                )
        if i['type'] == 'endurance':
            nt_materials.append(
                    f'{get_name(i["item"], lang)} (⬇ -{i["count"]} )'
                )

        text = t('item_use.recipe.not_enough_m', lang, materials=', '.join(nt_materials))
        await bot.send_message(chatid, 
                    text, 
                    parse_mode='Markdown', 
                    reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    else:
        await end_craft(count, item, userid, chatid, lang, data)

async def end_craft(count, item, userid, chatid, lang, data):

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)

    # Оперделение цели крафта
    choosed_items = data['choosed_items']
    temp_way, way = '', ''
    if choosed_items == []:
        way = 'main'
    else:
        for i in choosed_items:
            if not temp_way:
                temp_way = i
            else:
                temp_way += f'-{i}'
            if temp_way in data_item['create'].keys():
                way = temp_way
        if not way:
            way = 'main'

    # Удаление материалов
    for material in data['end']:

        if material['type'] == 'delete':
            await UseAutoRemove(userid, material['item'], material['count'])

        elif material['type'] == 'endurance':
            for i in material['delete']:
                await items.delete_one({'_id': i})

            if material['edit']:
                await items.update_one({'_id': material['edit']}, 
                         {'$set': {'items_data.abilities.endurance': 
                             material['set']} })

    # Выдача крафта
    created_items = []
    for create_data in data_item['create'][way]:

        if create_data['type'] == 'create':
            preabil = create_data.get('abilities', {}) # Берёт характеристики если они есть

            if preabil:
                for key, value in preabil.items():
                    preabil[key] = random_data(value)

            add_count = create_data.get('count', 0)
            await AddItemToUser(userid, create_data['item'],
                                count + add_count, preabil)

            for _ in range(count + add_count):
                created_items.append(create_data['item'])

    # Понижение прочности рецепта
    await UseAutoRemove(userid, item, count)

    # Вычисление опыта за крафт
    if 'rank' in data_item.keys():
        xp = GAME_SETTINGS['xp_craft'][data_item['rank']] * count
    else:
        xp = GAME_SETTINGS['xp_craft']['common'] * count

    # Начисление опыта за крафт
    await experience_enhancement(userid, xp)

    # Создание сообщения
    await bot.send_message(chatid, t('item_use.recipe.create', lang, 
                                     items=counts_items(created_items, lang)), 
                           parse_mode='Markdown', reply_markup=await markups_menu(userid, 'last_menu', lang))