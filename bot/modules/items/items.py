"""Пояснение:
    >>> Стандартный предмет - предмет никак не изменённый пользователем, сгенерированный из json.
    >>> abilities - словарь с индивидуальными харрактеристиками предмета, прочность, использования и тд.
    >>> abilities - используется только для предмета создаваемого из базы, используется для создания нестандартного предмета.
    
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

import json
from typing import Any, Literal, Optional, Union

from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.modules.data_format import deepcopy, escape_markdown, random_dict, seconds_to_str, near_key_number
from bot.modules.localization import get_all_locales, t
from bot.modules.localization import get_data as get_loc_data
from bot.modules.logs import log
from bot.modules.items.collect_items import get_all_items

from bot.modules.overwriting.DataCalsses import DBconstructor

items = DBconstructor(mongo_client.items.items)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
users = DBconstructor(mongo_client.user.users)

ITEMS: dict = get_all_items()

def get_data(item_id: str) -> dict:
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if item_id in ITEMS.keys():
        item_data = deepcopy(ITEMS[item_id])
        return item_data # type: ignore
    else: 
        raise ValueError(f"Предмет с ID {item_id} не найден в базе данных предметов.")

def load_items_names() -> dict:
    """Загружает все имена предметов из локализации в один словарь. 
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

ITEMS_NAMES = load_items_names()
LOCATIONS_TYPES = Literal["home", "market", "dino", "guild"]
ABILITIES_DATA_TYPES = Union[int, float, str, bool]

class ItemData:
    """Класс предмета, используется для создания предметов и их взаимодействия с пользователем"""

    def __init__(self, item_id: str, abilities: Optional[dict] = None):

        self.item_id = item_id
        self.data = get_data(self.item_id)

        self.abilities = self.abilities_processing(abilities)

    def abilities_processing(self, abilities: Optional[dict]) -> dict:
        """ Обрабатывает характеристики предмета, если они есть и добавляет стандартные харрактеристики из json файла предметов """

        abl: dict = self.data.get('abilities', {})
        abl.update(abilities or {})

        if abl:
            for ak in abl:
                if type(abl[ak]) == dict:
                    # Если предмет имеет рандомные 
                    # харрактеристики при создании, то выбираем случайные значения
                    abl[ak] = random_dict(abl[ak])
                else:
                    abl[ak] = abl[ak]

        for key in abl:
            assert isinstance(key, ABILITIES_DATA_TYPES), f"Ключ {key} в характеристиках предмета должен быть из типов {ABILITIES_DATA_TYPES}"

            # Обновляем локальные данные предмета данными харрактеристик
            if key in self.data:
                self.data[key] = abl[key]

        return abl

    def to_dict(self) -> dict:
        """Преобразование в словарь для сохранения в базу данных"""
        return {
            "item_id": self.item_id,
            "abilities": self.abilities
        }

    @property
    def name(self, lang: str = 'en') -> str:
        """Получение имени предмета (c кешированием)"""
        if not hasattr(self, '_name'):
            self._name = self.get_name(lang)
        return self._name

    def get_name(self, lang: str='en') -> str:
        """Получение имени предмета"""
        name = ''

        if 'endurance' in self.abilities:
            endurance = self.abilities['endurance']
        else: endurance = 0

        if self.item_id in ITEMS_NAMES:
            if lang not in ITEMS_NAMES[self.item_id]: lang = 'en'

            if 'name' in self.abilities: name = self.abilities['name']

            elif endurance and 'alternative_name' in ITEMS_NAMES[self.item_id][lang]:
                if str(endurance) in ITEMS_NAMES[self.item_id][lang]['alternative_name']:
                    name = ITEMS_NAMES[self.item_id][lang]['alternative_name'][str(endurance)]
                else: 
                    name = near_key_number(endurance, 
                                           ITEMS_NAMES[self.item_id][lang], 'name')
            else:
                try:
                    name = ITEMS_NAMES[self.item_id][lang]['name']
                except:
                    log(f'Имя для {self.item_id} {lang} не найдено!', 4)
        else:
            log(f'Имя для {self.item_id} не найдено')

        return name

    @property
    def description(self, lang: str = 'en') -> str:
        """Получение описания предмета (c кешированием)"""
        if not hasattr(self, '_description'):
            self._description = self.get_description(lang)
        return self._description

    def get_description(self, lang: str='en') -> str:
        """Получение описания предмета"""
        description = ''

        if self.item_id in ITEMS_NAMES:
            if lang not in ITEMS_NAMES[self.item_id]:
                lang = 'en'
            description = ITEMS_NAMES[self.item_id][lang].get('description', '')
        return description

    def is_standart(self) -> bool:
        """Определяем стандартный ли предмет*.

        Для этого проверяем есть ли у него свои харрактеристик.\n
        Если их нет - значит он точно стандартный.\n
        Если они есть и не изменены - стандартный.
        Если есть и изменены - изменённый.
        """
        if not self.abilities:
            return True

        # Проверяем, что все характеристики соответствуют стандартным
        for key, value in self.abilities.items():
            if key not in self.data.get('abilities', {}):
                return False
            if self.data['abilities'][key] != value:
                return False

        return True


class ItemInBase:
    """Класс предмета в базе данных"""

    def __init__(self, 
                 owner_id: int = 0,
                 item_id: str = 'cookie', 
                 abilities: Optional[dict] = None, 
                 count: int = 1,
                 location_type: LOCATIONS_TYPES = "home",
                 location_link: Any = None
                 ):

        assert location_type in LOCATIONS_TYPES.__args__, \
            f"Неверный тип места хранения: {location_type}. Доступные типы: {LOCATIONS_TYPES.__args__}"

        assert isinstance(owner_id, int), "owner_id должен быть целым числом"
        assert isinstance(item_id, str), "item_id должен быть строкой"
        assert isinstance(count, int) and count > 0, "count должен быть положительным целым числом"
        assert isinstance(location_link, (str, int, ObjectId, type(None))), "location_link должен быть строкой, целым числом, ObjectId или None"

        self._id: Optional[ObjectId] = None
        self.owner_id = owner_id
        self.items_data: ItemData = ItemData(item_id, abilities)
        self.count = count

        # Данные для удобства
        self.item_id = item_id

        self.location = {
            "type": location_type,  # Тип места хранения (home, market, dino)
            "link": location_link,  # Ссылка на место хранения (Id динозавра, клетка с магазином, ...)
        }

    def to_dict(self) -> dict:
        """Преобразование в словарь для сохранения в базу данных"""
        return {
            "owner_id": self.owner_id,
            "count": self.count,
            "items_data": {
                "item_id": self.items_data.item_id,
                "abilities": self.items_data.abilities
            },
            "location": self.location
        }

    @property
    def link_with_real_item(self) -> bool:
        """Проверка, что предмет связан с реальным предметом в базе данных"""
        return self._id is not None

    async def link_for_id(self, _id: ObjectId) -> "ItemInBase":
        """Связывает предмет с реальным предметом в базе данных"""

        result = await items.find_one({"_id": _id}, comment='link_item_for_id')
        if result is None:
            raise ValueError(f"Предмет с ID {_id} не найден в базе данных.")

        self._id = _id
        self.__dict__.update(result)
        self.items_data = ItemData(**result['items_data'])
        self.item_id = self.items_data.item_id
        return self

    async def link_yourself(self) -> bool:
        """Связывает предмет с реальным предметом в базе данных по своим данным"""

        find_dct = self.to_dict()
        find_dct.pop('_id', None)

        result = await items.find_one(find_dct, comment='link_item_yourself')
        if result is None: return False

        self._id = result['_id']
        self.__dict__.update(result)
        self.items_data = ItemData(**result['items_data'])
        self.item_id = self.items_data.item_id
        return True

    async def link(self, 
                   owner_id: int, item_id: str, 
                   abilities: Optional[dict] = None,
                   count: Optional[int] = None,
                   location_type: LOCATIONS_TYPES = 'home',
                   location_link: Any = None,
                   min_count: bool = False
                   ) -> "ItemInBase":
        """Связывает предмет с реальным предметом в базе по его данным
           
           - min_count: bool - если True, то ищем предмет с >= count, иначе ищем с count == count
        """

        find_dct = {
            "owner_id": owner_id,
            "items_data.item_id": item_id,
        }
        if abilities:
            find_dct["items_data.abilities"] = abilities

        if count:
            if min_count:
                find_dct["count"] = {"$gte": count}
            else:
                find_dct["count"] = count

        if location_type:
            assert location_type in LOCATIONS_TYPES.__args__, \
                f"Неверный тип места хранения: {location_type}. Доступные типы: {LOCATIONS_TYPES.__args__}"
            find_dct["location.type"] = location_type

        if location_link:
            find_dct["location.link"] = location_link

        result = await items.find_one(find_dct)
        if result is None:
            raise ValueError(f"Предмет с данными {find_dct} не найден в базе данных.")

        self._id = result['_id']
        self.__dict__.update(result)
        self.items_data = ItemData(**result['items_data'])
        self.item_id = self.items_data.item_id
        return self

    async def add_to_db(self) -> ObjectId:
        """Добавляет предмет в базу данных и возвращает его ID"""

        assert self.link_with_real_item is False, "Предмет уже связан с реальным предметом в базе данных"
        assert isinstance(self.owner_id, int) and self.owner_id > 0, "owner_id должен быть привязан к реальному пользователю"

        if not self.items_data.is_standart():
            raise ValueError("Предмет должен быть стандартным для добавления в базу данных")

        result = await items.insert_one(self.to_dict(), comment='add_item_to_db')
        self._id = result.inserted_id
        return self._id

    async def plus(self, count: int = 1) -> int:
        """Увеличивает количество предметов в базе данных"""
        assert isinstance(count, int) and count > 0, "count должен быть положительным целым числом"
        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"

        self.count += count
        await items.update_one({"_id": self._id}, {"$set": {"count": self.count}})
        return self.count

    async def minus(self, count: int = 1) -> int:
        """Уменьшает количество предметов в базе данных"""

        assert isinstance(count, int) and count > 0, "count должен быть положительным целым числом"
        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"

        if self.count < count:
            raise ValueError("Недостаточно предметов для уменьшения количества.")

        if self.count == count:
            await items.delete_one({"_id": self._id})
            self._id = None
            self.count = 0

        else:
            self.count -= count
            await items.update_one({"_id": self._id}, {"$set": {"count": self.count}})
        return self.count

    async def downgrade(self, characteristic: str, amount: int) -> dict:
        """
        Понижает характеристику предмета (например, прочность) на заданное значение amount.
        Если характеристика становится <= 0, предмет удаляется из базы.
        Если харрактеристика > 0, то удаляем 1 предмет из базы, ищем новый предмет с такой же характеристикой и обновляем его значение количества на 1.
        Возвращает словарь с результатом операции.
        """

        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"
        assert characteristic in self.items_data.abilities, f"Характеристика {characteristic} не найдена в предметах"
        assert isinstance(amount, int) and amount > 0, "amount должен быть положительным целым числом"

        item = {
            'item_id': self.items_data.item_id,
            'abilities': self.items_data.abilities
        }

        if not self.link_with_real_item:
            return {'status': False, 'action': 'unit', 'difference': amount}

        durability = self.items_data.abilities[characteristic]
        count = self.count
        total_durability = durability * count

        if total_durability < amount:
            return {'status': False, 'action': 'unit', 'difference': amount - total_durability}

        full_remove = amount // durability
        remainder = amount % durability
        actions = []

        if full_remove > 0:
            await self.minus(full_remove)
            actions.append({'delete_count': full_remove})

        if remainder > 0:
            # Удаляем ещё 1 предмет и добавляем с остатком
            await self.minus(1)

            new_abilities = dict(self.items_data.abilities)
            new_abilities[characteristic] = durability - remainder

            await AddItemToUser(self.owner_id, 
                                self.items_data.item_id, 1, 
                                new_abilities, self.location['type'],
                                self.location['link']
                            )
            actions.append({'edit': durability - remainder})

        log(f'DowngradeItem {self.owner_id} {item} {characteristic} {amount} {actions}', 0, 'DowngradeItem')
        return {'status': True, 'action': 'deleted_edited', 'details': actions}

    async def update(self):
        """Обновляет данные предмета в базе данных"""
        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"

        await items.update_one({"_id": self._id}, {"$set": self.to_dict()})
        return self


async def AddItemToUser(owner_id: int, 
                        item_data: ItemData,
                        count: int = 1, 
                        location_type: LOCATIONS_TYPES = "home",
                        location_link: Any = None
                        ):
    """Добавление стандартного предмета в инвентарь
    """

    assert count >= 0, f'AddItemToUser, count == {count}'
    log(f"owner_id {owner_id}, item_id {item_data.item_id}, count {count}", 0, "Add item")

    item = ItemInBase(owner_id=owner_id, 
                      item_id=item_data.item_id, 
                      abilities=item_data.abilities, 
                      count=count, 
                      location_type=location_type, 
                      location_link=location_link)
    await item.link_yourself()

    if item.link_with_real_item:
        # Предмет уже существует в базе, увеличиваем его количество
        await item.plus(count)
        action = 'plus_count'

    else:
        # Предмет не существует в базе, добавляем его
        await item.add_to_db()
        action = 'new_item'

    return action, item._id

async def RemoveItemFromUser(owner_id: int, 
                             item_data: ItemData,
                             count: int = 1, 
                             location_type: LOCATIONS_TYPES = "home",
                             location_link: Any = None
                             ) -> Union[bool, str]:
    """Удаление предмета из инвентаря пользователя"""

    assert count >= 0, f'RemoveItemFromUser, count == {count}'
    log(f"owner_id {owner_id}, item_id {item_data.item_id}, count {count}", 0, "Remove item")

    item = ItemInBase(owner_id=owner_id, 
                      item_id=item_data.item_id, 
                      abilities=item_data.abilities, 
                      count=count, 
                      location_type=location_type, 
                      location_link=location_link)
    await item.link_yourself()

    if not item.link_with_real_item: return False
    if item.count < count: return 'not_enough_items'

    await item.minus(count)
    return True

async def DeleteAbilItem(
        owner_id: int,
        item_data: ItemData,
        location_type: LOCATIONS_TYPES,
        location_link: Any,
        characteristic: str,
        unit: int,
        count: int
    ):
    """
    Функция рассчитывает нужно ли удалять предметы или понижать прочность.
    Возвращает:
        - False, {'ost': ...} - не хватает прочности
        - True, {'delete_count': int, 'edit_id': ObjectId или None, 'set': int или None}
    """
    
    item = ItemInBase(
        owner_id=owner_id,
        item_id=item_data.item_id,
        abilities=item_data.abilities,
        count=count,
        location_type=location_type,
        location_link=location_link
    )
    await item.link_yourself()
    need_char = unit * count
    
    if not item.link_with_real_item:
        return False, {'ost': need_char}

    durability = item.items_data.abilities[characteristic]
    total = durability * item.count

    if total < need_char:
        return False, {'ost': need_char - total}

    delete_count = need_char // durability
    remainder = need_char % durability

    set_value = None

    if remainder > 0:
        if delete_count >= item.count:
            # Не может быть, т.к. total >= need_char, но на всякий случай
            return False, {'ost': 0}

        set_value = durability - remainder

    return True, {
        'delete_count': delete_count,
        'set': set_value
    }

async def CheckItemFromUser(owner_id: int, item_id: str, 
                            abilities: dict | None,
                            count: int = 1,
                            location_type: LOCATIONS_TYPES = "home",
                            location_link: Any = None
                            ) -> dict:
    """Проверяет есть ли count предметов у человека, если предмета с таким количеством нет, то возвращает разницу
    """

    item = ItemInBase(owner_id=owner_id, 
                      item_id=item_id, 
                      abilities=abilities, 
                      count=count, 
                      location_type=location_type, 
                      location_link=location_link)
    await item.link_yourself()

    if item.link_with_real_item: 
        return {"status": True, 'item': item}
    else:
        await item.link(owner_id, item_id, abilities, count, location_type, location_link, min_count=True)

        if item.link_with_real_item:
            return {"status": False, "difference": count - item.count}
        else:
            return {"status": False, "difference": count}

async def CheckCountItemFromUser(owner_id: int, 
                                 item_data: ItemData, 
                                 count: int,
                                 location_type: LOCATIONS_TYPES = "home",
                                 location_link: Any = None
                                 ) -> bool:
    """ TODO: удалить. Проверяет есть ли count предметов у человека """

    result = await CheckItemFromUser(
        owner_id, 
        item_data.item_id, 
        item_data.abilities, 
        count, 
        location_type, 
        location_link
    )
    return result['status']

async def check_and_return_dif(owner_id: int, 
                               item_data: ItemData, 
                               count: int,
                               location_type: LOCATIONS_TYPES = "home",
                               location_link: Any = None
                            ) -> int:
    """ TODO: удалить. Проверяет не конкретный документ на count а всю базу, возвращая количество
    """
    item = ItemInBase(owner_id=owner_id, 
                      item_id=item_data.item_id, 
                      abilities=item_data.abilities, 
                      count=count, 
                      location_type=location_type, 
                      location_link=location_link)
    await item.link_yourself()

    if item.link_with_real_item: return item.count
    else: return 0

async def EditItemFromUser(owner_id: int, 
                           location_type: LOCATIONS_TYPES,
                           location_link: Any,
                           now_item: ItemData, new_data: ItemData
                           ) -> bool:
    """ TODO: удалить.
       Функция ищет предмет по now_item и в случае успеха изменяет его данные на new_data.
       Если предметов больше одного, то создаёт новый предмет с новыми данными и удаляет старый.
       (Или добавляет колличество, если новый предмет уже в базе)
    
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
    item = ItemInBase(owner_id=owner_id, 
                     item_id=now_item.item_id, 
                     abilities=now_item.abilities, 
                     count=1, 
                     location_type=location_type, 
                     location_link=location_link)
    await item.link_yourself()

    if item.link_with_real_item:
        if item.count > 1:

            await item.minus(1)
            await AddItemToUser(
                owner_id, 
                new_data, 
                count=1, 
                location_type=location_type, 
                location_link=location_link
            )

        else:
            item.items_data = new_data
            await item.update()
        return True
    return False