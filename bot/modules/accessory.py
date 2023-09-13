from random import randint

from bot.modules.dinosaur import Dino
from bot.modules.item import get_data
from bot.modules.notifications import dino_notification


async def downgrade_accessory(dino: Dino, acc_type: str, max_unit: int = 2):
    """Понижает прочность аксесуара
       Return
       >>> True - прочность понижена
       >>> False - неправильный предмет / нет предмета
    """
    item = dino.activ_items[acc_type]

    if item:
        if 'abilities' in item and 'endurance' in item['abilities']:
            num = randint(0, max_unit)

            if item['abilities']['endurance'] <= 0:
                await dino.update({"$set": {f'activ_items.{acc_type}': None}})
                await dino_notification(dino._id, 'broke_accessory', item_id=item['item_id'])
            else:
                await dino.update({"$inc": {f'activ_items.{acc_type}.abilities.endurance': -num}})
            return True
        else: return False
    return False

async def check_accessory(dino: Dino, item_id: str, downgrade: bool=False) -> bool:
    """Проверяет, активирован ли аксессуар с id - item_id
       downgrade - если активирован, то вызывает понижение прочности предмета
    """
    data_item = get_data(item_id) #Получаем данные из json
    acces_item = dino.activ_items[data_item['type']] #предмет / None

    if acces_item:
        if acces_item['item_id'] == item_id:
            if downgrade:
                return await downgrade_accessory(dino, data_item['type'])
            else:
                return True
        else:
            return False
    return False

async def weapon_damage(dino: Dino, downgrade: bool = False):
    """ Функция возвращает урон и понижает прочность при downgrade - True
    """
    weapon_item = dino.activ_items['weapon']
    if weapon_item:
        data_item = get_data(weapon_item['item_id'])
        damage = data_item['damage']
        if not downgrade or await downgrade_accessory(dino, 'weapon'):
            res = randint(damage['min'], damage['max'])
            if res > 0: return res
    return 1

async def armor_protection(dino: Dino, downgrade: bool = False):
    """ Функция возвращает защиту и понижает прочность при downgrade - True
    """
    weapon_item = dino.activ_items['armor']
    if weapon_item:
        data_item = get_data(weapon_item['item_id'])
        if not downgrade or await downgrade_accessory(dino, 'armor'):
            return data_item['reflection']
    return 0