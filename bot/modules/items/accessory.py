from random import randint
from typing import Optional

from bson import ObjectId

from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import RemoveItemFromUser, get_data
from bot.modules.notifications import dino_notification


async def find_accessory(dino: Dino, acc_type: Optional[str] = None) -> list[list]:
    """Поиск аксессуара в активных предметах по типу
       Return
       >>> [(item, index), ...]
       >>> []
    """
    
    result = []
    ind = -1
    for item in dino.activ_items:
        if 'item_id' not in item: continue

        data_item = get_data(item['item_id']) #Получаем данные из json
        ind += 1
        if data_item['type'] == acc_type or acc_type is None:
            result.append([item, ind])
    return result

async def downgrade_accessory(dino: Dino, item_id: str, max_unit: int = 2):
    """Понижает прочность аксессуара с указанным item_id
       Return
       >>> True - прочность понижена
       >>> False - неправильный предмет / нет предмета

    """
    old_acs = dino.activ_items.copy()
    for item in old_acs:
        index = dino.activ_items.index(item)

        if item['item_id'] == item_id:
            if 'abilities' in item and 'endurance' in item['abilities']:
                num = randint(0, max_unit)
                item['abilities']['endurance'] -= num
                if item['abilities']['endurance'] < 0: item['abilities']['endurance'] = 0

                if item['abilities']['endurance'] <= 0:
                    await remove_accessory(dino._id, dino.activ_items[index]['item_id'])
                    del dino.activ_items[index]

                    await dino_notification(dino._id, 'broke_accessory', item_id=item['item_id'])
                else:
                    new_dino = await Dino().create(dino._id)
                    if new_dino:
                        if index >= len(new_dino.activ_items) or new_dino.activ_items[index]['item_id'] != item['item_id']:
                            continue

                        # Понижаем прочность аксессуара
                        await dino.update({"$inc": {f'activ_items.{index}.abilities.endurance': -num}})
                return True
            return False
    return False

async def downgrade_type_accessory(dino: Dino, acc_type: str, max_unit: int = 2):
    """Понижает прочность всем аксессуарам указанного типа
       Return
       >>> True - хотя бы один аксессуар понижен
       >>> False - аксессуары указанного типа отсутствуют
       
       acc_type:
       - armor - броня
       - weapon - оружие
       - journey - путешествие
       - collecting - сбор пищи
       - game - игры
       

    """
    accessories = await find_accessory(dino, acc_type)
    if not accessories:
        return False  # Нет аксессуаров указанного типа

    updated = False
    for item, _ in accessories:
        index = dino.activ_items.index(item)

        if 'abilities' in item and 'endurance' in item['abilities']:
            num = randint(0, max_unit)
            item['abilities']['endurance'] -= num
            if item['abilities']['endurance'] < 0: 
                item['abilities']['endurance'] = 0

            if item['abilities']['endurance'] <= 0:
                await remove_accessory(dino._id, dino.activ_items[index]['item_id'])
                del dino.activ_items[index]

                item_id = item['item_id']
                await dino_notification(dino._id, 'broke_accessory', item_id=item_id)

            else:
                new_dino = await Dino().create(dino._id)
                if new_dino:
                    if index >= len(new_dino.activ_items) or new_dino.activ_items[index]['item_id'] != item['item_id']:
                        continue

                    # Понижаем прочность аксессуара
                    await dino.update({"$inc": {f'activ_items.{index}.abilities.endurance': -num}})
            updated = True

    return updated

async def check_accessory(dino: Dino, item_id: str, downgrade: bool = False,
                          max_down: int = 2) -> bool:
    """Проверяет, активирован ли аксессуар с id - item_id
       downgrade - если активирован, то вызывает понижение прочности предмета
    """
    data_item = get_data(item_id)  # Получаем данные из json
    acces_items = await find_accessory(dino, data_item['type'])

    for acces_item, _ in acces_items:
        if not acces_item: continue
        if 'item_id' not in acces_item: continue

        if acces_item['item_id'] == item_id:
            if downgrade:
                return await downgrade_accessory(dino, item_id, max_down)
            return True
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

            if not downgrade or await downgrade_type_accessory(dino, 'weapon'):
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
            if not downgrade or await downgrade_type_accessory(dino, 'armor'):
                armor += data_item['reflection']
    return armor

async def add_accsessory(dino: Dino, item_data: dict) -> bool:
    """Добавляет аксессуар в активные предметы динозавра и удаляет его у игрока
        Так же с условием, что у динозавра не может быть 2 одинаковых аксессуаров (item_id == item_id)
        А так же аксессуаров может быть не больше 5-ти штук

        item_data: {
            'item_id': str,
            'abilities': {
                'endurance': int,
                'reflection': int,
            },
        }
        return: bool
        >>> True - аксессуар добавлен и удалён из инвентаря человека
        >>> False - аксессуар не добавлен, так как он уже есть у динозавра или не может быть больше 5-ти аксессуаров
    """
    # Проверяем, есть ли уже аксессуар с таким item_id
    for item in dino.activ_items:
        if item['item_id'] == item_data['item_id']:
            return False  # Аксессуар уже есть

    # Проверяем, что количество активных аксессуаров не превышает 5
    if len(dino.activ_items) >= 5:
        return False  # Превышено максимальное количество аксессуаров

    # Добавляем аксессуар в активные предметы
    dino.activ_items.append(item_data)
    await dino.update({"$push": {"activ_items": item_data}})

    return True

async def remove_accessory(dino_id: ObjectId, item_id: str) -> bool:
    """Удаляет аксессуар из активных предметов динозавра
       Возвращает True, если аксессуар был успешно удалён, иначе False
    """
    dino = await Dino().create(dino_id)
    if not dino:
        return False  # Динозавр не найден

    for index, item in enumerate(dino.activ_items):
        if item['item_id'] == item_id:
            # Удаляем аксессуар из активных предметов

            await dino.update({"$pull": 
                {"activ_items": dino.activ_items[index]}})
            del dino.activ_items[index]

            return True  # Аксессуар успешно удалён
    return False  # Аксессуар не найден