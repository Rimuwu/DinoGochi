

import pprint
from typing import Any, Union
from bot.config import mongo_client
from bot.modules.data_format import list_to_inline, random_code
from bot.modules.inventory_tools import inventory_pages
from bot.modules.items.item import check_and_return_dif, get_name, get_data, item_code, item_info
from bot.modules.items.items_groups import get_group
from bot.modules.localization import t
from bot.modules.markup import markups_menu
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import get_inventory_from_i
from bot.exec import bot

from bot.modules.overwriting.DataCalsses import DBconstructor
items = DBconstructor(mongo_client.items.items)

async def craft_recipe(userid: int, chatid: int, lang: str, item: dict, count: int=1):
    """ Сформировать список проверяемых предметов, подготовить данные для выбора предметов
    """
    add_choose_item = False

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)

    materials, steps = [], []
    a = -1

    for material in data_item['materials']:
        if 'col' not in material: material['col'] = 1
        a += 1

        material['col'] *= count
        if not isinstance(material['item'], str):
            add_choose_item = True

            if isinstance(material['item'], dict):
                # В материалах указана группа
                find_items = get_group(material['item']['group'])

            elif isinstance(material['item'], list):
                # В материалах указан список предметов которых можно использовать
                find_items = material['item']

            inv = await get_inventory_from_i(userid, find_items)

            if not inv:
                await bot.send_message(chatid, 
                    t('item_use.recipe.not_choosed', lang), 
                    parse_mode='Markdown', 
                    reply_markup=await markups_menu(userid, 'last_menu', lang))
                return

            steps.append(
                {
                    'type': 'inv',
                    'name': str(a)+'_step',
                    'data': {
                        'inventory': inv,
                        'changing_filters': False
                    },
                    'translate_message': True,
                    'message': {'text': 'item_use.recipe.consumable_item'}
                }
            )

            material['item'] = str(a)+'_step'
        materials.append(material)

    if add_choose_item:

        transmitted_data = {
            'materials': materials,
            'count': count,
            'item': item
        }

        await ChooseStepState(end_choose_items, userid, chatid, lang, steps, transmitted_data)

    else:
        await check_items_in_inventory(materials, item, count, userid, chatid, lang)


async def end_choose_items(items: Union[dict, list[dict]], transmitted_data: dict[str, Any]):
    """ Смотрим на данные, преобразовываем так, чтобы они подошли под check_items_in_inventory
    """
    if isinstance(items, dict): items = [items]
    materials, count, item, userid, chatid, lang, steps = transmitted_data.values()

    choosed_items = [] # Записываем какие предметы были выбраны

    # Заменяем данные в материалах на выбранные предметы
    data_of_keys = {}
    for choosed in items:
        choosed: dict
        key_material = list(choosed.keys())[0]

        data_of_keys[key_material] = choosed[key_material]
        choosed_items.append(data_of_keys[key_material]['item_id'])

    for material in materials:
        material: dict

        if material['item'] in data_of_keys:
            material['item'] = data_of_keys[ material['item'] ]['item_id']

    way = '-'.join(choosed_items) # Вариация рецепта (По умолчанию main)
    await check_items_in_inventory(materials, item, count, userid, chatid, lang, way)


async def check_items_in_inventory(materials, item, count, 
                                   userid, chatid, lang, way = 'main'):
    
    """ Должна проверить предметы, выявить есть ли у игрока для каждого предмета разные вариации и если да - дать выбрать их (сделать через выдачу краткой информации и кнопки - применить)
    """

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    finded_items, steps = [], []
    not_find = []

    if way not in data_item['create']: 
        way = 'main' # Если не найдена вариация, возвращаемся к базовой

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
                    finded_items.append(i['items_data'])
                else:
                    not_find.append({'item': i['items_data'], 
                                     'diff': material['col'] - count_material})
                    continue

            # Есть варианты для выбора
            elif len(find_set) > 1:
                a += 1
                steps.append(
                    {
                        'type': 'inv',
                        'name': str(a)+'_step',
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
                finded_items.append(str(a)+'_step')

    if not_find:
        nt_materials = []
        for i in not_find:
            nt_materials.append(
                f'{get_name(i["item"]["item_id"], lang)} x{i["diff"]}'
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
            'count': count,
            'item': item
        }

        await ChooseStepState(pre_end, userid, chatid, lang, steps, transmitted_data)
    
    else:
        await end_craft()

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

async def pre_end(items: Union[dict, list[dict]], transmitted_data):
    print('2333333333333333')
    pprint.pprint(transmitted_data)
    finded_items, count, item, userid, chatid, lang, steps = transmitted_data.values()
    print(items)


async def end_craft():
    ...