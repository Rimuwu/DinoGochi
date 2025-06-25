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
from bot.modules.data_format import escape_markdown, random_dict, seconds_to_str, near_key_number
from bot.modules.images_creators.item_image import create_item_image
from bot.modules.images_save import in_storage
from bot.modules.items.json_item import *
from bot.modules.localization import get_all_locales, t
from bot.modules.localization import get_data as get_loc_data
from bot.modules.logs import log
from bot.modules.items.collect_items import get_all_items

from bot.modules.overwriting.DataCalsses import DBconstructor

items = DBconstructor(mongo_client.items.items)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
users = DBconstructor(mongo_client.user.users)

ITEMS: dict = get_all_items()

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
LOCATIONS_TYPES = Literal["home", "market", "accessory", "guild", "backpack"]
ABILITIES_DATA_TYPES = Union[int, float, str, bool]

class ItemData:
    """Класс предмета, используется для создания предметов и их взаимодействия с пользователем"""

    def __init__(self, item_id: str, abilities: Optional[dict] = None):
        self.item_id = item_id
        self.data = GetItem(self.item_id)

        self.abilities = self.abilities_processing(abilities)

    def copy(self):
        """Создаёт копию предмета"""
        new_item = ItemData(self.item_id, self.abilities.copy())
        new_item.data.__dict__.update(self.data.__dict__)
        return new_item

    def __str__(self) -> str:
        return f"ItemData(item_id={self.item_id}, abilities={self.abilities}, data={self.data})"

    def abilities_processing(self, abilities: Optional[dict]) -> dict:
        """ Обрабатывает характеристики предмета, если они есть и добавляет стандартные харрактеристики из json файла предметов """

        abl: dict = getattr(self.data, 'abilities', {}).copy()
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
            if key in self.data.__dict__:
                self.data.__dict__[key] = abl[key]

        return abl

    def to_dict(self) -> dict:
        """Преобразование в словарь для сохранения в базу данных"""
        return {
            "item_id": self.item_id,
            "abilities": self.abilities
        }

    def name(self, lang: str) -> str:
        """Получение имени предмета (c кешированием)"""
        if not hasattr(self, '_name'):
            self._name = get_name(self.item_id, lang, self.abilities)
        return self._name

    def description(self, lang: str) -> str:
        """Получение описания предмета (c кешированием)"""
        if not hasattr(self, '_description'):
            self._description = self.get_description(lang)
        return self._description

    def get_description(self, lang: str) -> str:
        """Получение описания предмета"""
        description = ''

        if self.item_id in ITEMS_NAMES:
            if lang not in ITEMS_NAMES[self.item_id]:
                lang = 'en'
            description = ITEMS_NAMES[self.item_id][lang].get('description', '')
        return description

    @property
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
            if key not in self.data.abilities:
                return False
            if self.data.abilities[key] != value:
                return False

        return True

    def code(self):
        """Создаёт код-строку предмета, основываясь на его
           характеристиках.
        """
        return convert_dict_to_string(self.to_dict())


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
    
    def __str__(self) -> str:
        return f"ItemInBase(owner_id={self.owner_id}, item_id={self.item_id}, count={self.count}, location={self.location}, _id={self._id}, items_data={self.items_data})"

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

    async def link_yourself(self, ignore_count: bool = True) -> bool:
        """Связывает предмет с реальным предметом в базе данных по своим данным"""

        find_dct = self.to_dict()
        find_dct.pop('_id', None)
        if ignore_count:
            find_dct.pop('count', None)

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

    async def link_from_base(self, 
            owner_id: int, count: int, 
            items_data: dict, location: dict,
            _id: ObjectId | None = None,
            update_data: bool = False
        ):
        """ Линк на основе данных из базы данных. 
            update_data - если True, то обновляет данные предмета в базе данных
            Если нет, то просто заменяет данные предмета в этом классе
        """

        if _id is None or update_data:

            find_dct = {
                "owner_id": owner_id,
                "items_data.item_id": items_data['item_id'],
                "items_data.abilities": items_data['abilities'],
                "count": count,
                "location.type": location['type'],
                "location.link": location['link']
            }

            result = await items.find_one(find_dct, comment='link_item_from_base')
            if result is None:
                raise ValueError(f"Предмет с данными {find_dct} не найден в базе данных.")

            self._id = result['_id']
            self.__dict__.update(result)
            self.items_data = ItemData(**result['items_data'])
            self.item_id = self.items_data.item_id
            return self

        else:
            self._id = _id
            self.owner_id = owner_id
            self.items_data = ItemData(**items_data)
            self.count = count
            self.location = location

            self.item_id = self.items_data.item_id

            return self

    async def add_to_db(self) -> ObjectId:
        """Добавляет предмет в базу данных и возвращает его ID"""

        assert self.link_with_real_item is False, "Предмет уже связан с реальным предметом в базе данных"
        assert isinstance(self.owner_id, int) and self.owner_id > 0, "owner_id должен быть привязан к реальному пользователю"

        res = await items.find_one(self.to_dict(), comment='add_item_to_db')
        if res:
            self._id = res.inserted_id
            await self.plus(1)
            return self._id # type: ignore

        else:
            result = await items.insert_one(self.to_dict(), comment='add_item_to_db')
            self._id = result.inserted_id
            return self._id # type: ignore

    async def plus(self, count: int = 1) -> int:
        """Увеличивает количество предметов в базе данных"""
        assert isinstance(count, int) and count > 0, "count должен быть положительным целым числом"
        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"

        self.count += count
        await items.update_one(
            {"_id": self._id}, {"$set": {"count": self.count}})
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
            await items.update_one({"_id": self._id}, 
                                   {"$set": {"count": self.count}})
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
            new_item = ItemData(
                self.items_data.item_id, new_abilities)

            await AddItemToUser(self.owner_id,
                                new_item,
                                1, 
                                self.location['type'],
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

    async def UsesRemove(self, count: int = 1) -> bool:
        """Автоматически определяет что делать с предметом, удалить или понизить количество использований
        """
        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"
        
        if 'uses' not in self.items_data.abilities:
            await self.minus(count)
            return True

        else:
            res = await self.downgrade('uses', count)
            return res['status']

    async def edit(self, 
                   abilities: Optional[dict] = None,
                   location_type: Optional[LOCATIONS_TYPES] = None,
                   location_link: Any = '000'
                   ) -> "ItemInBase":
        """
            Изменяет характеристики предмета в базе данных,
            Данные возвращаемого объекта будут соответсвовать изменённой характеристике.
            location_link - '000' значение, при котором не будет меняться значение.
        """

        assert self.link_with_real_item, "Предмет должен быть связан с реальным предметом в базе данных"

        if abilities is not None:
            self.items_data.abilities.update(abilities)

        if location_type is not None:
            assert location_type in LOCATIONS_TYPES.__args__, \
                f"Неверный тип места хранения: {location_type}. Доступные типы: {LOCATIONS_TYPES.__args__}"
            self.location['type'] = location_type

        if location_link != '000':
            self.location['link'] = location_link

        if self.count > 1:
            await self.minus(1)
            st, it_id = await AddItemToUser(self.owner_id,
                                self.items_data,
                                1,
                                self.location['type'],
                                self.location['link']
                            )

            self = await ItemInBase().link_for_id(it_id)

        else:
            await self.update()
        return self

    def code(self, data_mode: bool = True) -> str:
        """Создаёт код-строку предмета, основываясь на его
           характеристиках.

           data_mode - даже если предмет есть в базе, то возвращает строку в формате ID-...:AB.uses-1:endurance-1
        """

        if self.link_with_real_item:
            if data_mode:
                return convert_dict_to_string(
                    self.items_data.to_dict())
            else:
                # Возвращает ID предмета в виде строки
                return self._id.__str__()
        
        else:
            return convert_dict_to_string(
                    self.items_data.to_dict())

def convert_dict_to_string(item_dict: dict) -> str:
    """Преобразует словарь в строку формата ID.item_id-...:uses-1-i:endurance-1-i"""

    item_id = item_dict.get("item_id", "")
    abilities = item_dict.get("abilities", {})
    abilities_str = ":".join(f"{key}#{value}#{type(value).__name__[:3]}" for key, value in abilities.items())

    return f"ID{item_id}:{abilities_str}"

type_map = {"int": int, "str": str, "flo": float, "boo": bool}

def convert_string_to_dict(item_string: str) -> ItemData:
    """Преобразует строку в словарь формата ID.item_id-...:uses-1-int:endurance-1-int"""

    item_id = item_string.split("ID")[1].split(":")[0]
    abilities_str = item_string.split("ID")[1].split(":")[1:]
    abilities = {}
    for ability in abilities_str:
        if ability == "": continue

        name, value, short_item_type = ability.split("#")

        abilities[name] = type_map[short_item_type](value)

    return ItemData(item_id, abilities)

async def decode_item(str_id: str):
    """ Превращает код в словарь
    """

    if str_id.startswith('ID'):
        return convert_string_to_dict(str_id)
    
    else:
        _id = ObjectId(str_id)
        item = ItemInBase()

        await item.link_for_id(_id)
        return item

def get_name(item_id: str, lang: str, abilities: Optional[dict] = None) -> str:
    """Получение имени предмета"""
    name = ''

    if abilities is None: abilities = {}

    if 'endurance' in abilities:
        endurance = abilities['endurance']
    else: endurance = 0

    if item_id in ITEMS_NAMES:
        if lang not in ITEMS_NAMES[item_id]: lang = 'en'

        if 'name' in abilities: name = abilities['name']

        elif endurance and 'alternative_name' in ITEMS_NAMES[item_id][lang]:
            if str(endurance) in ITEMS_NAMES[item_id][lang]['alternative_name']:
                name = ITEMS_NAMES[item_id][lang]['alternative_name'][str(endurance)]
            else: 
                name = near_key_number(endurance, 
                                        ITEMS_NAMES[item_id][lang], 'name')
        else:
            try:
                name = ITEMS_NAMES[item_id][lang]['name']
            except:
                log(f'Имя для {item_id} {lang} не найдено!', 4)
    else:
        log(f'Имя для {item_id} не найдено')

    return name

async def AddItemToUser(owner_id: int, 
                        item_data: ItemData,
                        count: int = 1, 
                        location_type: LOCATIONS_TYPES = "home",
                        location_link: Any = None
                        ) -> tuple[str, ObjectId]:
    
    """Добавление стандартного предмета в инвентарь
        TODO: Проверить все добавления предметов на передачу правильного формата и указания локации
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

    return action, item._id # type: ignore

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
        location_type: LOCATIONS_TYPES = 'home',
        location_link: Any = None,
        characteristic: str = 'endurance',
        unit: int = 1,
        count: int = 1
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

async def EditItemFromUser(owner_id: int, 
                           location_type: LOCATIONS_TYPES,
                           location_link: Any,
                           now_item: ItemData, 
                           new_data: ItemData
                           ) -> bool:
    """
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


def sort_materials(not_sort_list: list, lang: str, 
                   separator: str = ',') -> str:
    """Создание сообщение нужных материалов для крафта

    Args:
        not_sort_list (list): Список с материалами из базы предметов
          example: [{"item": "26", "type": "delete"}, 
                    {"item": "26", "type": "delete"}]
        lang (str): язык
        separator (str, optional): Разделитель материалов. Defaults to ','.

    Returns:
        str: Возвращает строку для вывода материалов крафта
    """
    col_dict, items_list, check_items = {}, [], []

    # Считает предметы
    for i in not_sort_list:
        item = i['item']

        if isinstance(item, list) or isinstance(item, dict):
            item = json.dumps(item)

        if item not in col_dict:
            if 'count' in i:
                col_dict[item] = i['count']
            else: col_dict[item] = 1
        else: 
            if 'count' in i:
                col_dict[item] += i['count']
            else: col_dict[item] += 1

    # Собирает текст
    for i in not_sort_list:
        item = i['item']
        abilities = i.get('abilities', {})
        text = ''

        if i not in check_items:
            if isinstance(item, str):
                itemdata = ItemData(item, abilities)
                col = col_dict[item]
                text = itemdata.name(lang)

            elif isinstance(item, list):
                lst = []
                col = col_dict[json.dumps(i['item'])]
                for i_item in item:
                    itemdata = ItemData(i_item, abilities)
                    lst.append(
                        itemdata.name(lang)
                    )

                text = f'({" | ".join(lst)})'

            elif isinstance(item, dict):
                col = col_dict[json.dumps(item)]
                text = "(" + t(f'groups.{item["group"]}', lang) + ")"

            if i['type'] == 'endurance':
                text += f" (⬇ -{i['act']})"
            if col > 1:
                text += f' x{col}'

            items_list.append(text)
            check_items.append(i)

    return f"{separator} ".join(items_list)

def get_case_content(content: list, lang: str, separator: str = ' |'):
    items_list = []

    for item in content:
        
        if isinstance(item['id'], str):
            itemdata = ItemData(item['id'])
            name = itemdata.name(lang)

        if isinstance(item['id'], dict):
            # В материалах указана группа
            group = item["id"]["group"]
            name = "(" + t(f'groups.{group}', lang) + ")"

        elif isinstance(item['id'], list):
            # В материалах указан список предметов которых можно использовать
            names = []
            for i in item['id']: 
                itemdata = ItemData(i)
                names.append(itemdata.name(lang))
            name = '(' + ', '.join(names) + ')'

        percent = round((item['chance'][0] / item['chance'][1]) * 100, 4)
        if item['col']['type'] == 'random':
            col = f"x({item['col']['min']} - {item['col']['max']})"
        else:
            col = f"x{item['col']['act']}"
        
        items_list.append(
            f'{name} {col} {percent}%'
        )
    return f"{separator} ".join(items_list)

def counts_items(id_list: list[str] | None, lang: str, separator: str = ','):
    """Считает предмете, полученные в формате строки, 
       и преобразовывает в текс.

    Args:
        id_list (list): Список с предметами в формате строки
            example: ["1", "12"]
        lang (str): Язык
        separator (str, optional): Символы, разделяющие элементы. Defaults to ','.

    Returns:
        str: Возвращает строку для вывода материалов крафта
    """
    dct, items_list = {}, []
    if id_list is None: return '-'
    
    for i in id_list:
        if isinstance(i, str):
            dct[i] = dct.get(i, 0) + 1

        elif isinstance(i, dict):
            item_i = i['item_id']
            count_i = i['count']

            dct[item_i] = dct.get(item_i, 0) + count_i


    for item, col in dct.items():
        itemdata = ItemData(item)
        name = itemdata.name(lang)
        if col > 1: name += f" x{col}"

        items_list.append(name)

    if items_list:
        return f"{separator} ".join(items_list)
    else: return '-'

def get_items_names(items_list: list[dict], lang: str, separator: str = ','):
    """Считает предмете, полученные в формате строки, 
       и преобразовывает в текс.

    Args:
        id_list (list): Список с предметами
            example: [{'items_data': {'item_id'}, 'count': Optional[int]}]
        lang (str): Язык
        separator (str, optional): Символы, разделяющие элементы. Defaults to ','.

    Returns:
        str: Возвращает строку с предметами
    """
    dct, i_names = {}, []
    for i in items_list: 
        add_count = i.get('count', 1)
        dct_to_str = json.dumps(i)
        dct[dct_to_str] = dct.get(dct_to_str, 0) + add_count

    for item_s, col in dct.items():
        item = json.loads(item_s)
        item_data = item.get(
            'items_data', item.get('item', {})
        )

        items_id = item_data['item_id']
        abilities = item_data.get('abilities', {})
        
        itemdata = ItemData(items_id, abilities)
        name = itemdata.name(lang)

        if col > 1: name += f" x{col}"
        i_names.append(name)

    if i_names:
        return f"{separator} ".join(i_names)
    else: return '-'


async def item_info(item: ItemData | ItemInBase, lang: str, 
                    owner: bool = False):
    """Собирает информацию и предмете, пригодную для чтения

    Args:
        item (dict): Сгенерированный словарь данных предмета
        lang (str): Язык

    Returns:
        Str, Image
    """
    standart = ['dummy', 'material']

    if isinstance(item, ItemInBase):
        # Если передан предмет из базы, то получаем его данные
        data_item = item.items_data.data
        item_name: str = item.items_data.name(lang)
        description: str = item.items_data.description(lang)
        abilities = item.items_data.abilities
    else:
        # Если передан предмет из ItemData, то получаем его данные
        data_item = item.data
        item_name: str = item.name(lang)
        description: str = item.description(lang)
        abilities = item.abilities

    rank_item: str = data_item.rank
    type_item: str = data_item.type
    loc_d = get_loc_data('item_info', lang)

    if hasattr(data_item, 'item_class') and getattr(data_item, 'item_class', None) in loc_d['type_info']:
        type_loc: str = getattr(data_item, 'item_class')
    else:
        type_loc: str = getattr(data_item, 'type')

    text = ''
    dp_text = ''

    # Шапка и название
    text += loc_d['static']['cap'] + '\n'
    text += loc_d['static']['name'].format(name=item_name) + '\n'

    # Ранг предмета
    rank = loc_d['rank'][rank_item]
    text += loc_d['static']['rank'].format(rank=rank) + '\n'

    # Тип предмета
    type_name = loc_d['type_info'][type_loc]['type_name']
    text += loc_d['static']['type'].format(type=type_name) + '\n'

    if 'author' in abilities.keys():
        author_user = await users.find_one(
            {'userid': abilities['author']})

        if author_user: author_name = author_user['name']
        else: author_name = loc_d['static']['unnamed_author']

        text += loc_d['static']['author'].format(
            author=author_name
            ) + '\n'

    # Быстрая обработка предметов без фич
    if type_item in standart:
        dp_text += loc_d['type_info'][type_loc]['add_text']

    #Еда
    elif isinstance(data_item, Eat):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(act=data_item.act)

    # Аксы
    elif isinstance(data_item, (Game, Sleep, Journey, Collecting)):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                item_description=description)

    # Книга
    elif isinstance(data_item, Book):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                item_description=description)

    # Специальные предметы
    elif isinstance(data_item, Special):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                item_description=description)

        if getattr(data_item, 'item_class', None) == 'transport':
            if abilities.get('data_id', 0) != 0:
                dino = await dinosaurs.find_one({'alt_id': abilities['data_id']})
                if dino:
                    text += loc_d['static']['trs_dino'].format(
                        dino=escape_markdown(dino['name']), hp=dino['stats']['heal']
                    )

    # Рецепты
    elif isinstance(data_item, Recipe):
        cr_list = []
        ignore_craft = data_item.ignore_preview

        for key, value in data_item.create.items():
            if key not in ignore_craft:
                cr_list.append(sort_materials(value, lang))

        if data_item.time_craft > 0:
            dp_text += loc_d['static']['time_craft'].format(
                times=seconds_to_str(data_item.time_craft, lang))
            dp_text += '\n'

        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                create=' | '.join(cr_list),
                materials=sort_materials(data_item.materials, lang),
                item_description=description)
    # Оружие
    elif isinstance(data_item, Weapon):
        if type_loc == 'near':
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    endurance=abilities['endurance'],
                    min=data_item.damage['min'],
                    max=data_item.damage['max'])
        else:
            dp_text += loc_d['type_info'][
                type_loc]['add_text'].format(
                    ammunition=counts_items(data_item.ammunition, lang),
                    min=data_item.damage['min'],
                    max=data_item.damage['max'])
    # Боеприпасы
    elif isinstance(data_item, Ammunition):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                add_damage=data_item.add_damage)
    # Броня
    elif isinstance(data_item, Armor):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                reflection=data_item.reflection)
    # Рюкзаки
    elif isinstance(data_item, Backpack):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                capacity=data_item.capacity)
    # Кейсы
    elif isinstance(data_item, Case):
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                content=get_case_content(data_item.drop_items, lang, '\n'))

        if description: dp_text += f"\n\n{description}"

    # Яйца
    elif isinstance(data_item, Egg):
        end_time = seconds_to_str(data_item.incub_time, lang)
        dp_text += loc_d['type_info'][
            type_loc]['add_text'].format(
                inc_time=end_time,
                rarity=get_loc_data(f'rare.{data_item.inc_type}', lang)[1])

    # Информация о внутренних свойствах

    for iterable_key in ['uses', 'endurance', 'mana']:
        if iterable_key in abilities.keys():
            text += loc_d['static'][iterable_key].format(
                abilities[iterable_key], data_item.abilities[iterable_key]
            ) + '\n'

    text += dp_text
    item_bonus = data_item.buffs
    add_bonus, add_penaltie = [], []

    for bonus in item_bonus:
        if item_bonus[bonus] > 0:
            add_bonus.append(loc_d['bonuses']['+' + bonus].format(
                item_bonus[bonus]))
        else:
            add_penaltie.append(loc_d['penalties']['-' + bonus].format(
                item_bonus[bonus]))

    if add_bonus:
        text += loc_d['static']['add_bonus']

        for i in add_bonus:
            if i == add_bonus[-1]:
                text += f'*└* {i}'
            else: 
                text += f'*├* {i}\n'

    if add_penaltie:
        text += loc_d['static']['add_penaltie']

        for i in add_penaltie:
            if i == add_penaltie[-1]:
                text += '*└* '
            else: text += '*├* '
            text += i

    item_states = data_item.states
    if item_states:
        text += loc_d['static']['add_states']

        for state in item_states:
            unit = state.get('unit', 0)
            str_time = seconds_to_str(state['time'], lang)

            state_text: str = loc_d['item_states'][
                '-' if unit < 0 else '+' + state['char']
                ]
            state_text = state_text.format(unit, str_time)

            if state == item_states[-1]:
                text += f'*└* {state_text}'
            else:
                text += f'*├* {state_text}\n'

    # Картиночка

    if type_item == 'special' and type_loc == 'background':
        data_id = abilities['data_id']
        image_file = f"images/backgrounds/{data_id}.png"

    else:
        item_path=data_item.image.get('icon', None)
        background_path=data_item.image.get('background') or 'green'
        element_path=data_item.image.get('element', None)

        if await in_storage(
            f'{item_path}_{background_path}_{element_path}.png'):
            image_file = f'{item_path}_{background_path}_{element_path}.png'

        else:

            image_file = create_item_image(
                item_path=item_path,
                background_path=background_path,
                element_path=element_path
            )

    if owner:
        text += f'\n\n`{item} {data_item}`'

    return text, image_file