""" Файл с логикой распределения предметов

    #1 Если мы хотим положить предмет динозавру:
        - Есть ли место в рюкзаке динозавра
        - - Да - добавляем в инвентарь динозавра (backpack)
        - - Нет 
            - Если есть возможность, то говорим о том, что положить нельзя, иначе удаляем предметы
            - Если динозавр на клетке с домом, то кладём в дом (home)

    Если мы хотим положить предмет в / market / guild:
        - Есть ли место на складе
        - - Да - добавляем в склад
        - - Нет - Если есть возможность, то говорим о том, что положить нельзя, иначе удаляем предметы
"""


from bson import ObjectId
from bot.const import GAME_SETTINGS as GS
from bot.const import STRUCTURE_LEVELS as SL
from bot.modules.dinosaur.dinosaur import Dino, get_dino_inventory, get_dino_transfer_count
from bot.modules.items.item import AddItemToUser, ItemData
from bot.modules.map.home import get_home, home_location
from bot.modules.map.location import is_within_tolerance
from bot.modules.user.user import get_inventory

async def check_home_item_limit(user_id: int) -> int:
    """ Проверяем, есть ли место в доме пользователя для добавления предмета.
        Возвращает количество свободных мест в доме.
    """
    home = await get_home(user_id)
    if home:
        home_lvl = home['upgrades']['inventory']
        max_count = SL['home']['inventory'][str(home_lvl)]['max_items']

        user_inventory, count = await get_inventory(user_id,
                                             location_type='home')
        return max_count - count if count >= 0 else 0

    return 0

async def check_backpack_item_limit(dino_id: ObjectId | Dino):
    """ Проверяем, есть ли место в рюкзаке динозавра для добавления предмета.
        Возвращает количество свободных мест в рюкзаке.
    """

    if isinstance(dino_id, ObjectId):
        dino = await Dino().create(dino_id)
        if not dino: return 0
    else:
        dino = dino_id

    max_count = await get_dino_transfer_count(dino)
    inv, count = await get_dino_inventory(dino._id)

    return max_count - count if count >= 0 else 0

async def check_market_item_limit():
    ...

async def check_guild_item_limit():
    ...

async def where_add_item(userid: int, dino_id: ObjectId, left: int ):
    """ Функция отвечает на вопрос, куда положить добавляемый предмет.
        Приоритеты:
            1. Home
            2. Backpack

        Логика: 
            1. Проверяем, есть ли место в доме. Если да, то кладем туда. 
            -> return home
            2. Если в доме нет места, проверяем рюкзак. Если там есть место, кладем в рюкзак.
            -> return backpack
            3. Если нет места ни в доме, ни в рюкзаке, сообщаем об этом пользователю.
            -> return {}

        Результат: {'home': int, 'backpack': int, 'remains': int}
        Ключей может быть от 0 до 3
        remains - остаток, который не получилось распределить
    """

    result = {}
    dino = await Dino().create(dino_id)
    if dino:
        dino_loc = dino.my_location
        dino_distance = dino.location['percent']
        home_loc = await home_location(userid)

        # Проверяем, находится ли динозавр в доме
        if dino_loc == home_loc and is_within_tolerance(50, dino_distance):
            home_free = await check_home_item_limit(userid)
            to_home = min(home_free, left) if home_free > 0 else 0
            if to_home > 0:
                result['home'] = to_home
                left -= to_home

        # Если после дома что-то осталось, пробуем положить в рюкзак
        if left > 0:
            backpack_free = await check_backpack_item_limit(dino)
            to_backpack = min(backpack_free, left) if backpack_free > 0 else 0
            if to_backpack > 0:
                result['backpack'] = to_backpack

        if left > 0: result['remains'] = left

    return result

async def AddItemToDino(userid: int, 
                        dino_id: ObjectId | Dino, 
                        item: ItemData, 
                        count: int = 1
                        ):

    """ Добавляет предмет в инвентарь динозавра или в дом пользователя.
        Если предмет не помещается в инвентарь динозавра, то добавляет в дом.
        
        return: 
        - False - предметы не добавлены
        - True - часть или все предметы добавлены
    """

    if isinstance(dino_id, ObjectId):
        dino = await Dino().create(dino_id)
        if not dino: return False
    else:
        dino = dino_id
    
    where = await where_add_item(userid, dino._id, count)
    
    print('===================', where)
    
    for place, count in where.items():

        if place == 'home':
            await AddItemToUser(
                owner_id=userid,
                item_data=item,
                count=count,
                location_type='home'
            )

        elif place == 'backpack':
            # Добавляем в рюкзак
            await AddItemToUser(
                owner_id=userid,
                item_data=item,
                count=count,
                location_type='backpack',
                location_link=dino._id
            )

    return True
