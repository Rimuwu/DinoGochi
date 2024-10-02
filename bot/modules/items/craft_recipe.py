

from copy import deepcopy
from operator import add
from typing import Any
from bot.const import GAME_SETTINGS
from bot.dbmanager import mongo_client
from bot.modules.data_format import list_to_inline, random_code, random_data, seconds_to_str
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.item import AddItemToUser, DeleteAbilItem, UseAutoRemove, check_and_return_dif, get_item_dict, get_items_names, get_name, get_data, item_code, item_info
from bot.modules.items.items_groups import get_group
from bot.modules.items.time_craft import add_time_craft
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import markups_menu
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import get_inventory_from_i
from bot.exec import main_router, bot
from bot.modules.user.user import experience_enhancement

from bot.modules.overwriting.DataCalsses import DBconstructor
items = DBconstructor(mongo_client.items.items)

"""
    "clothing_recipe_new": {
        "create": {
            "main": [ // Тип создаваемого рецепта, main используется для отображения в инфо, создаётся по умолчанию и должен быть всегда
                {
                    "item": "leather_clothing", // Создаваемый предмет
                    "type": "create", // Тут create | preview (не создаётся, только превью)
                    "abilities": {}, // Характеристики предмета
                    "count": 1 // Количество создания вместо повторов
                }
            ],
            "carrot": [ // Тип создаваемого рецепта, main используется для отображения в инфо, создаётся по умолчанию и должен быть всегда
                {
                    "item": "leather_clothing", // Создаваемый предмет
                    "type": "create", // Тут create 
                    "abilities": {"act": { "random-int": [2, 10] }}, // Рандомная число от 2 до 10
                    // После, если в списке 2 элемента - и оба число - randint иначе choice
                    "count": 1 // Количество создания вместо повторов
                }
            ]
        },
        "materials": [
            {
                "item": "skin", // Удаляемый предмет
                "type": "delete", // delete | endurance удаление | понижение характеристики предмета | to_create
                # to_create - переносит предмет в создаваемые (удаляет как материал и создаёт его с теме же хар )
                "count": 5 // count - delete | act - сколько нужно отнять 
                "abilities": {}, // Характеристики предмета (используются для поиска)
            },
            {
                "item": {"group": "vegetables"}, // Предложит выбрать из группы предметов овощей (те что есть в инвентаре)
                "type": "delete", // delete | endurance удаление | понижение характеристики предмета 
                "count": 5, // count - delete | act - сколько нужно отнять 
                "save_choose": true // По умолчанию поставить в коде False
                // В случае если true, код будет искать в create ключ с выбранным предметом
                // Например выбрали carrot - будут выданы предметы не из main, а carrot
                // Если нет ключа carrot создать main
                // Если выбора несколько ставить между выбором "-"
            },
            {
                "item": ["carrot", "leather"], // Предложет выбрать из списка предметов (те что есть в инвентаре)
                "type": "delete", // delete | endurance удаление | понижение характеристики предмета 
                "count": 5, // count - delete | act - сколько нужно отнять 
                "copy_abilities": [
                    {
                        "copy": ["endurance"], // Копирует указанную хар предмета
                        "max_unit": 50, // Сколько максимально может быть передано единиц (для inc)
                        "to_items": [0], // Устанавливает её указанным предметам
                        "action": "set" | "inc" 
                    }
                ]
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
    choosed_items = []
    a = -1

    for material in data_item['materials']:
        if 'count' not in material: material['count'] = 1
        copy_mat = {**material}

        copy_mat['count'] *= count
        if 'abilities' in material:
            copy_mat['abilities'] = {**material['abilities']}

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

            inv = await get_inventory_from_i(userid, find_items, one_count=True)

            if not inv:
                await bot.send_message(chatid, 
                    t('item_use.recipe.not_choosed', lang), 
                    parse_mode='Markdown', 
                    reply_markup=await markups_menu(userid, 'last_menu', lang))
                return

            elif len(inv) == 1:
                copy_mat['item'] = inv[0]['item']['item_id']
                choosed_items.append(inv[0]['item'])

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

                copy_mat['item'] = name

        materials.append(copy_mat)

    if len(steps) > 0:

        transmitted_data = {
            'materials': materials,
            'count': count,
            'item': item
        }

        await ChooseStepState(end_choose_items, userid, chatid, lang, steps, transmitted_data)

    else:
        data = {
            "choosed_items": choosed_items
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
        choosed_items.append(choosed)

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
        if 'abilities' in material:
            find_data = {'owner_id': userid, 
                         'items_data.item_id': material['item'],
                         'items_data.abilities': material['abilities']
                         }
        else:
            find_data = {'owner_id': userid, 
                         'items_data.item_id': material['item']}

        find_items = await items.find(find_data, {'_id': 0, 'owner_id': 0},
                     comment='check_items_in_inventory')

        # Нет предметов
        if len(find_items) == 0:
            not_find.append({'item': material['item'], 'diff': material['count']})

        else:
            find_set = []
            for i in find_items:
                if i['items_data'] not in find_set:
                    find_set.append(i['items_data'])

            # У предметов нет альтернатив
            if len(find_set) == 1:

                if material['type'] in ['delete', 'to_create']:
                    count_material = await check_and_return_dif(userid, **find_set[a])
                    if count_material >= material['count']:
                        finded_items.append(
                            {'item': i['items_data'],
                            'count': material['count']}
                        )
                    else:
                        not_find.append({'item': i['items_data'], 
                                        'diff': material['count'] - count_material})

                elif material['type'] == 'endurance':
                    status, dct_data = await DeleteAbilItem(find_set[a], 'endurance', 
                                material['act'], count, userid)
                    if status:
                        finded_items.append(
                            {'item': i['items_data'],
                            'count': material['count']}
                        )
                    else:
                        count_material = len(dct_data['delete'])
                        not_find.append({'item': i['items_data'], 
                                        'diff': material['count'] - count_material})

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
                                              item_name=get_name(
                                                  material['item'], lang, 
                                                  material.get('abilities', {})))}
                    }
                )
                finded_items.append({'item': name, 
                                     'count': material['count']})

    if not_find:
        nt_materials = []
        for i in not_find:
            if type(i['item']) == dict:
                item_id = i["item"]["item_id"]
                abil = i["item"]
            else: 
                item_id = i['item']
                abil = {}

            nt_materials.append(
                f'{get_name(item_id, lang, abil)} x{i["diff"]}'
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
        await send_SmartPhoto(chatid, image, text, 'Markdown', markup)

async def pre_check(items: dict, transmitted_data):
    finded_items, data, count, item, userid, chatid, lang, steps = transmitted_data.values()
    result_list = []

    for i in finded_items:
        if isinstance(i['item'], dict):
            result_list.append(i)

        elif isinstance(i['item'], str):
            result_list.append({'item': items[i['item']], 'count': i['count']})

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

        if material['type'] in ['delete', 'to_create']:
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
                dct_data['item'] = material['item']
                data['end'].append(dct_data)

    if not_found:
        nt_materials = []
        for i in not_found:
            if i['type'] in ['delete', 'to_create']:
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
    super_create = deepcopy(data_item['create'])

    # Оперделение цели крафта
    choosed_items = data['choosed_items']
    temp_way, way = '', ''

    if choosed_items == []:
        way = 'main'
    else:
        for i in choosed_items:
            if not temp_way:
                temp_way = i['item_id']
            else:
                temp_way += f'-{i["item_id"]}'
            if temp_way in list(super_create.keys()):
                way = temp_way
        if not way:
            way = 'main'

    if way == 'main':
        for i in choosed_items:
            if choosed_items in list(super_create.keys()):
                way = i
                break

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
                             material['set']} 
                          })

        elif material['type'] == 'to_create':
            r = await UseAutoRemove(userid, material['item'], material['count'])
            if r:
                super_create[way].append( {
                    "type": "create",
                    "item": material['item']['item_id'],
                    "count": material['count'],
                    "abilities": material['item'].get('abilities', {})
                } )

    # Очищаем создание от ненужных предметов
    to_create: list = super_create[way]
    for create in super_create[way]:

        if create['type'] == 'preview':
            to_create.remove(create)

    # Сохранение характеристик предмета и подготовка создаваемых редметов
    for material in data['end']:
        ind = data['end'].index(material)
        material_data = data_item['materials'][ind]

        if 'copy_abilities' in material_data and 'abilities' in material['item']:
            data_cop = material_data['copy_abilities']

            for cr_item in data_cop['to_items']:
                standart_item = get_item_dict(to_create[cr_item]['item'])
                standart_abil = standart_item.get('abilities', {})

                for abil in data_cop['copy']:
                    if abil in material['item']['abilities']:
                        if 'abilities' not in to_create[cr_item]:
                            to_create[cr_item]['abilities'] = {}

                        if data_cop['action'] == 'set':
                            to_create[cr_item]['abilities'][abil] = material['item']['abilities'][abil]

                        elif data_cop['action'] == 'inc':
                            if abil in standart_abil and to_create[cr_item]['abilities'][abil] != standart_abil[abil]:
                                abil_unit = material['item']['abilities'][abil]
                                if 'max_unit' in data_cop:
                                    if abil_unit > data_cop['max_unit']:
                                        abil_unit = data_cop['max_unit']

                                if abil in to_create[cr_item]['abilities']:
                                    to_create[cr_item]['abilities'][abil] += abil_unit
                                else:
                                    to_create[cr_item]['abilities'][abil] = abil_unit

                                if abil in standart_abil and \
                                    to_create[cr_item]['abilities'][abil] > standart_abil[abil]:
                                    to_create[cr_item]['abilities'][abil] = standart_abil[abil]

    # Выдача крафта
    create = []
    a = -1
    for create_data in to_create:
        a += 1

        if create_data['type'] == 'create':
            preabil = create_data.get('abilities', {}) # Берёт характеристики если они есть

            if preabil:
                for key, value in preabil.items():
                    preabil[key] = random_data(value)

            add_count = count * data_item['create'][way][a]['count']

            create.append({'item': {'item_id': create_data['item'], 
                                    'abilities': preabil}, 
                           'count': add_count
                           })

    # Понижение прочности рецепта
    await UseAutoRemove(userid, item, count)

    # Вычисление опыта за крафт
    if 'rank' in data_item.keys():
        xp = GAME_SETTINGS['xp_craft'][data_item['rank']] * count
    else:
        xp = GAME_SETTINGS['xp_craft']['common'] * count

    # Начисление опыта за крафт
    await experience_enhancement(userid, xp)

    if 'time_craft' in data_item:
        tc = await add_time_craft(userid, data_item['time_craft'], create)
        text = t('time_craft.text_start', lang, 
                 items=get_items_names(create, lang),
                 craft_time=seconds_to_str(data_item['time_craft'], lang)
                 )
        markup = list_to_inline(
            [
                {t('time_craft.button', lang): f"time_craft {tc['alt_code']}  send_dino"}
            ]
        )

    else:
        for i in create:
            await AddItemToUser(userid, i['item']['item_id'], 
                                i['count'], i['item']['abilities'])
        text = t('item_use.recipe.create', lang, 
                 items=get_items_names(create, lang))
        markup = await markups_menu(userid, 'last_menu', lang)

    # Создание сообщения
    await bot.send_message(chatid, text, parse_mode='Markdown', 
                           reply_markup = markup)

    if 'time_craft' in data_item:
        text = t('time_craft.text2', lang,
                 command='/craftlist')
        markup = await markups_menu(userid, 'last_menu', lang)
        await bot.send_message(chatid, text, parse_mode='Markdown', 
                           reply_markup = markup)