from random import randint

from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import get_data
from bot.modules.notifications import dino_notification


async def find_accessory(dino: Dino, acc_type: str) -> list[list]:
    """Поиск аксессуара в активных предметах по типу
       Return
       >>> [(item, index), ...]
       >>> []
    """
    
    result = []
    ind = -1
    for item in dino.activ_items:
        data_item = get_data(item['item_id']) #Получаем данные из json
        ind += 1
        if data_item['type'] == acc_type:
            result.append([item, ind])
    return result

async def downgrade_accessory(dino: Dino, acc_type: str, max_unit: int = 2, ind_item: int = -1):
    """Понижает прочность аксесуара
       Return
       >>> True - прочность понижена
       >>> False - неправильный предмет / нет предмета
       
       ind_item - Если -1 то понижает всем подходящим аксессуарам
                - Если другой индекс то ищем такой индекс
    """
    item = dino.activ_items[acc_type]

    if item:
        if 'abilities' in item and 'endurance' in item['abilities']:
            num = randint(0, max_unit)

            if item['abilities']['endurance'] <= 0:
                await dino.update({"$set": {f'activ_items.{acc_type}': None}})
                await dino_notification(dino._id, 'broke_accessory', item_id=item['item_id'])
            else:
                await dino.update({"$inc": 
                    {f'activ_items.{acc_type}.abilities.endurance': -num}})
            return True
        else: return False
    return False

async def check_accessory(dino: Dino, item_id: str, downgrade: bool=False) -> bool:
    """Проверяет, активирован ли аксессуар с id - item_id
       downgrade - если активирован, то вызывает понижение прочности предмета
    """
    data_item = get_data(item_id) #Получаем данные из json
    acces_items = await find_accessory(dino, data_item['type'])

    if acces_items:
        acces_item = acces_items[0][0]
        if acces_item['item_id'] == item_id:
            if downgrade:
                return await downgrade_accessory(dino, data_item['type'])
            else: return True
        else: return False
    return False

async def weapon_damage(dino: Dino, downgrade: bool = False):
    """ Функция возвращает урон и понижает прочность при downgrade - True
    """
    weapon_items = await find_accessory(dino, 'weapon')
    damage = 0

    for weapon, ind_weapon in weapon_items:

        if weapon:
            data_item = get_data(weapon['item_id'])
            damage_data = data_item['damage']

            if not downgrade or await downgrade_accessory(dino, 'weapon'):
                damage += randint(damage_data['min'], damage_data['max'])

    if damage == 0: damage = 1
    return damage

async def armor_protection(dino: Dino, downgrade: bool = False):
    """ Функция возвращает защиту и понижает прочность при downgrade - True
    """
    armor_items = await find_accessory(dino, 'armor')
    armor = 0

    if armor_items:
        for armor_item, ind_item in armor_items:
            data_item = get_data(armor_item['item_id'])
            if not downgrade or await downgrade_accessory(dino, 'armor'):
                armor += data_item['reflection']
    return armor