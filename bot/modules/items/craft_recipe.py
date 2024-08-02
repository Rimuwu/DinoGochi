

from typing import Any, Union

from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import get_name, get_data
from bot.modules.items.items_groups import get_group
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import get_inventory_from_i


async def craft_recipe(userid: int, chatid: int, lang: str, item: dict, count: int=1):
    """ Сформировать список проверяемых предметов, подготовить данные для выбора предметов
    """
    add_choose_item = False

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    item_name: str = get_name(item_id, lang)

    materials, steps = [], []
    a = -1

    for material in data_item['materials']:
        a += 1
        if 'col' not in material: material['col'] = 1

        material['col'] *= count
        if isinstance(material['item'], str):
            # В материалах указан предмет

            materials.append(
                material
            )

        elif isinstance(material['item'], dict):
            # В материалах указана группа
            add_choose_item = True
            inv = await get_inventory_from_i( userid, get_group( material['item']['group'] ))

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
            materials.append(
                material
            )

        elif isinstance(material['item'], list):
            # В материалах указан список предметов которых можно использовать
            add_choose_item = True
            inv = await get_inventory_from_i( userid, material['item'])

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
            materials.append(
                material
            )
    
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
    finded_items = [] # Записываем данные выбранных предметов


    # Заменяем данные в материалах на выбранные предметы
    data_of_keys = {}
    for choosed in items:
        choosed: dict
        key_material = list(choosed.keys())[0]

        data_of_keys[key_material] = choosed[key_material]
        choosed_items.append(key_material['item_id'])

    for material in materials:
        material: dict

        if material['item'] in data_of_keys:
            material['item'] = data_of_keys[ material['item']['item_id'] ]
            finded_items.append(material['item'])

    way = '-'.join(choosed_items) # Вариация рецепта (По умолчанию main)
    await check_items_in_inventory(materials, item, count, userid, chatid, lang, finded_items, way)


async def check_items_in_inventory(materials, item, count, 
                                   userid, chatid, lang, finded_items = [], way = 'main'):
    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    finded_items = finded_items

    if way not in data_item['create']: way = 'main' # Если не найдена вариация, возвращаемся к базовой


async def end_craft():
    ...