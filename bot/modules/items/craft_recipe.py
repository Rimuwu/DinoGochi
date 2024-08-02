

from typing import Any, Union

from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import get_name, get_data
from bot.modules.items.items_groups import get_group
from bot.modules.localization import t
from bot.modules.markup import markups_menu
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import get_inventory_from_i
from bot.exec import bot


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
    finded_items = []

    if way not in data_item['create']: way = 'main' # Если не найдена вариация, возвращаемся к базовой

    print(finded_items, materials)


async def end_craft():
    ...