import warnings
warnings.filterwarnings("ignore", category=UserWarning, message='Field name "count" in "Item" shadows an attribute in parent "Document"')

from typing import Dict, Any, Optional, Union, List, ClassVar
from beanie import Document, PydanticObjectId, Link
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User
from bot.models.dinosaur import Dino
from bot.modules.overwriting.DataCalsses import Transaction
from pydantic import Field, model_validator, ConfigDict
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT
import time
from random import randint, choice, shuffle

class OwnerIdProxy:
    def __init__(self, owner_field):
        self.owner_field = owner_field

    def _resolve(self, other):
        from bson.objectid import ObjectId
        if isinstance(other, ObjectId):
            from bot.dbmanager import mongo_client
            db = mongo_client._real_client.delegate["dinogochi"]
            u = db.users.find_one({"_id": other})
            if u:
                return u.get("userid")
            # Accessories owned by dino store str(dino ObjectId)
            return str(other)
        return other

    def __eq__(self, other):
        return self.owner_field == self._resolve(other)

    def __ne__(self, other):
        return self.owner_field != self._resolve(other)

    def in_(self, other):
        resolved = [
            self._resolve(v) for v in other
        ] if isinstance(other, (list, tuple, set)) else other
        return self.owner_field.in_(resolved)

    def __getattr__(self, name):
        return getattr(self.owner_field, name)

from beanie.odm.fields import ExpressionField
original_getattr = ExpressionField.__getattr__

def custom_getattr(self, item):
    if str(self) == 'owner' and item == 'id':
        return OwnerIdProxy(self)
    return original_getattr(self, item)

ExpressionField.__getattr__ = custom_getattr

class OwnerIdDescriptor:
    def __get__(self, instance, owner_cls):
        if instance is None:
            return owner_cls.owner
        return instance.owner

    def __set__(self, instance, value):
        if value is None:
            instance.owner = None
        elif hasattr(value, 'userid'):
            instance.owner = value.userid
        elif hasattr(value, 'alt_id'):
            instance.owner = value.alt_id
        else:
            instance.owner = value

class Item(PrivateModelMixin, Document):
    owner: Optional[Union[int, str]] = None
    owner_id: ClassVar[Any] = OwnerIdDescriptor()
    items_data: Dict[str, Any] = Field(default_factory=dict)
    count: int = 1

    @property
    def _id(self) -> ObjectId:
        return self.id

    class Settings:
        name = "items"
        is_root = True
        indexes = [
            IndexModel([("owner", ASCENDING)], name="owner")
        ]

    @classmethod
    def find(cls, *args, **kwargs):
        if cls == Item and 'with_children' not in kwargs:
            kwargs['with_children'] = True
        return super().find(*args, **kwargs)

    @classmethod
    def find_one(cls, *args, **kwargs):
        if cls == Item and 'with_children' not in kwargs:
            kwargs['with_children'] = True
        return super().find_one(*args, **kwargs)

    @property
    def item_id(self) -> str:
        return self.items_data['item_id']

    @property
    def abilities(self) -> dict:
        return self.items_data.get('abilities', {})

    @property
    def type(self) -> str:
        from bot.modules.items.item import get_data
        return get_data(self.item_id).get('type', '')

    @property
    def data(self) -> dict:
        from bot.modules.items.item import get_data
        return get_data(self.item_id)

    def get_level(self) -> int:
        from bot.modules.items.item import get_item_level
        return get_item_level(self.items_data)

    def get_damage(self) -> Optional[dict]:
        from bot.modules.items.item import get_item_damage
        return get_item_damage(self.items_data)

    def get_endurance_max(self) -> Optional[int]:
        from bot.modules.items.item import get_item_endurance_max
        return get_item_endurance_max(self.items_data)

    def get_reflection(self) -> int:
        from bot.modules.items.item import get_item_reflection
        return get_item_reflection(self.items_data)

    def get_capacity(self) -> int:
        from bot.modules.items.item import get_item_capacity
        return get_item_capacity(self.items_data)

    def get_effectiv(self) -> int:
        from bot.modules.items.item import get_item_effectiv
        return get_item_effectiv(self.items_data)

    def get_ability(self, key: str, default=None):
        from bot.modules.items.item import get_item_ability
        return get_item_ability(self.items_data, key, default)

    @classmethod
    async def add(cls, 
        userid: Union[int, str], 
        item_id: str, 
        count: int = 1, 
        abilities: Optional[dict[str, Any]] = None
    ):
        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.items.item import get_item_dict
        from bot.modules.logs import log
        if abilities is None: abilities = {}
        assert count >= 0, f'AddItemToUser, count == {count}'
        log(f"userid {userid}, item_id {item_id}, count {count}", 1, "Add item")

        item_dict = get_item_dict(item_id, abilities)
        if not abilities:
            existing = await cls.find_one({
                "owner": userid,
                "items_data.item_id": item_id,
                "$or": [
                    {"items_data": item_dict},
                    {"items_data.abilities": {"$exists": False}},
                    {"items_data.abilities": {}}
                ]
            })
        else:
            existing = await cls.find_one({
                "owner": userid,
                "items_data": item_dict
            })

        if existing:
            await existing.update({"$inc": {"count": count}})
            return 'plus_count', existing.id
        else:
            new_item = cls(owner=userid, items_data=item_dict, count=count)
            await new_item.insert()
            return 'new_item', new_item.id

    @classmethod
    async def remove(cls, userid: Union[int, str], item_id: str, count: int = 1, abilities: dict | None = None):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
                uid = user_obj.userid
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.items.item import get_item_dict
        from bot.modules.logs import log
        if abilities is None: abilities = {}
        assert count >= 0, f'RemoveItemFromUser, count == {count}'
        log(f"userid {userid}, item_id {item_id}, count {count}", 1, "Remove item")

        # Build query safely avoiding key-order sensitivity and matching all possible owner formats
        owners_list = [uid, str(uid), user_obj.id, str(user_obj.id)]
        query = {
            "owner": {"$in": owners_list},
            "items_data.item_id": item_id
        }
        from bot.modules.items.item import is_standart, get_data
        temp_item = {"item_id": item_id, "abilities": abilities or {}}
        if is_standart(temp_item):
            std_conditions = [
                {"items_data.abilities": {"$exists": False}},
                {"items_data.abilities": {}}
            ]
            config_abilities = get_data(item_id).get('abilities', {})
            if config_abilities:
                std_conditions.append({"items_data.abilities": config_abilities})
            if abilities:
                match_default = {}
                for k, v in abilities.items():
                    match_default[f"items_data.abilities.{k}"] = v
                std_conditions.append(match_default)
            query["$or"] = std_conditions
        else:
            for k, v in abilities.items():
                query[f"items_data.abilities.{k}"] = v

        find_items = await cls.find(query).to_list()
        
        max_count = sum(item.count for item in find_items)
        if count > max_count:
            return False
        
        async with Transaction():
            for item in find_items:
                if count > 0:
                    if count >= item.count:
                        count -= item.count
                        await item.delete()
                    else:
                        await item.update({"$inc": {"count": -count}})
                        count = 0
                else:
                    break
        return True

    @classmethod
    async def check_item(cls, userid: Union[int, str], item_data: dict, count: int = 1) -> dict:

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
                uid = user_obj.userid
            except Exception:
                pass
        if not user_obj:
            return False

        item_id = item_data['item_id']
        abilities = item_data.get('abilities', {})

        # Build query safely avoiding key-order sensitivity and matching all possible owner formats
        owners_list = [uid, str(uid), user_obj.id, str(user_obj.id)]
        query = {
            "owner": {"$in": owners_list},
            "items_data.item_id": item_id
        }
        from bot.modules.items.item import is_standart, get_data
        temp_item = {"item_id": item_id, "abilities": abilities or {}}
        if is_standart(temp_item):
            std_conditions = [
                {"items_data.abilities": {"$exists": False}},
                {"items_data.abilities": {}}
            ]
            config_abilities = get_data(item_id).get('abilities', {})
            if config_abilities:
                std_conditions.append({"items_data.abilities": config_abilities})
            if abilities:
                match_default = {}
                for k, v in abilities.items():
                    match_default[f"items_data.abilities.{k}"] = v
                std_conditions.append(match_default)
            query["$or"] = std_conditions
        else:
            for k, v in abilities.items():
                query[f"items_data.abilities.{k}"] = v

        find_items = await cls.find(query).to_list()
        total_count = sum(item.count for item in find_items)
        if total_count >= count:
            return {"status": True, 'item': find_items[0] if find_items else None}
        else:
            return {"status": False, "item": find_items[0] if find_items else None, 'difference': count - total_count}

    @classmethod
    async def check_count(cls, userid: Union[int, str], count: int, item_id: str, abilities: dict | None = None) -> bool:

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
                uid = user_obj.userid
            except Exception:
                pass
        if not user_obj:
            return False

        if abilities is None: abilities = {}

        # Build query safely avoiding key-order sensitivity and matching all possible owner formats
        owners_list = [uid, str(uid), user_obj.id, str(user_obj.id)]
        query = {
            "owner": {"$in": owners_list},
            "items_data.item_id": item_id
        }
        from bot.modules.items.item import is_standart, get_data
        temp_item = {"item_id": item_id, "abilities": abilities or {}}
        if is_standart(temp_item):
            std_conditions = [
                {"items_data.abilities": {"$exists": False}},
                {"items_data.abilities": {}}
            ]
            config_abilities = get_data(item_id).get('abilities', {})
            if config_abilities:
                std_conditions.append({"items_data.abilities": config_abilities})
            if abilities:
                match_default = {}
                for k, v in abilities.items():
                    match_default[f"items_data.abilities.{k}"] = v
                std_conditions.append(match_default)
            query["$or"] = std_conditions
        else:
            for k, v in abilities.items():
                query[f"items_data.abilities.{k}"] = v

        find_items = await cls.find(query).to_list()
        from bot.modules.logs import log
        log(f"Item.check_count userid={userid} (uid={uid}) query: {query}", 1, "Check count")
        log(f"Item.check_count found items: {[{'id': str(i.id), 'owner': i.owner, 'count': i.count, 'items_data': i.items_data} for i in find_items]}", 1, "Check count")
        max_count = sum(item.count for item in find_items)
        return max_count >= count

    @classmethod
    async def check_and_return_dif(cls, userid: Union[int, str], item_id: str, abilities: dict | None = None) -> int:

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.items.item import get_item_dict
        if abilities is None: abilities = {}
        item_dict = get_item_dict(item_id, abilities)
        if not abilities:
            find_items = await cls.find({
                "owner": uid,
                "items_data.item_id": item_id,
                "$or": [
                    {"items_data": item_dict},
                    {"items_data.abilities": {"$exists": False}},
                    {"items_data.abilities": {}}
                ]
            }).to_list()
        else:
            find_items = await cls.find({
                "owner": uid,
                "items_data": item_dict
            }).to_list()
        return sum(item.count for item in find_items)

    @classmethod
    async def delete_abilities(cls, item_data: dict, characteristic: str, unit: int, count: int, userid: Union[int, str]):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        need_char = unit * count
        find_item = await cls.find_one({"owner": uid, "items_data": item_data})
        if not find_item:
            return False, {'ost': need_char}

        durability = find_item.items_data['abilities'][characteristic]
        total = durability * find_item.count
        if total < need_char:
            return False, {'ost': need_char - total}

        delete_count = need_char // durability
        remainder = need_char % durability
        set_value = None
        if remainder > 0:
            if delete_count >= find_item.count:
                return False, {'ost': 0}
            set_value = durability - remainder

        return True, {
            'delete_count': delete_count,
            'set': set_value
        }

    @classmethod
    async def downgrade(cls, userid: Union[int, str], item: dict, characteristic: str, amount: int):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.logs import log
        doc = await cls.find_one({"owner": uid, "items_data": item})
        if not doc:
            return {'status': False, 'action': 'unit', 'difference': amount}

        durability = doc.items_data['abilities'][characteristic]
        count = doc.count
        total_durability = durability * count

        if total_durability < amount:
            return {'status': False, 'action': 'unit', 'difference': amount - total_durability}

        full_remove = amount // durability
        remainder = amount % durability
        actions = []

        async with Transaction():
            if full_remove > 0:
                await cls.remove(userid, doc.items_data['item_id'], full_remove, doc.items_data['abilities'])
                actions.append({'delete_count': full_remove})

            if remainder > 0:
                await cls.remove(userid, doc.items_data['item_id'], 1, doc.items_data['abilities'])
                new_abilities = dict(doc.items_data['abilities'])
                new_abilities[characteristic] = durability - remainder
                await cls.add(userid, doc.items_data['item_id'], 1, new_abilities)
                actions.append({'edit': durability - remainder})

        log(f'DowngradeItem {userid} {item} {characteristic} {amount} {actions}', 0, 'DowngradeItem')
        return {'status': True, 'action': 'deleted_edited', 'details': actions}

    # Accessory Logic Methods
    @classmethod
    async def find_accessory(cls, dino_id: ObjectId, acc_type: Optional[str] = None) -> List["Item"]:
        items = await cls.find({"owner": str(dino_id)}).to_list()
        if acc_type:
            return [i for i in items if i.data['type'] == acc_type]
        return items

    @classmethod
    async def downgrade_accessory(cls, dino_id: ObjectId, item_id: str, max_unit: int = 2) -> bool:
        from bot.modules.notifications import dino_notification
        item = await cls.find_one({"owner": str(dino_id), "items_data.item_id": item_id})
        if item and 'abilities' in item.items_data and 'endurance' in item.items_data['abilities']:
            num = randint(0, max_unit)
            async with Transaction():
                item.items_data['abilities']['endurance'] -= num
                if item.items_data['abilities']['endurance'] <= 0:
                    await item.delete()
                    await dino_notification(dino_id, 'broke_accessory', item_id=item_id)
                else:
                    await item.save()
            return True
        return False

    async def update_skills_priority(self, skills_priority: dict):
        if 'abilities' not in self.items_data:
            self.items_data['abilities'] = {}
        self.items_data['abilities']['skills_priority'] = skills_priority
        await self.save()

    async def clear_skills_priority(self):
        if 'abilities' in self.items_data and 'skills_priority' in self.items_data['abilities']:
            self.items_data['abilities'].pop('skills_priority', None)
            await self.save()

    @classmethod
    async def downgrade_type_accessory(cls, dino_id: ObjectId, acc_type: str, max_unit: int = 2) -> bool:
        accessories = await cls.find_accessory(dino_id, acc_type)
        if not accessories:
            return False
        
        async with Transaction():
            for item in accessories:
                await cls.downgrade_accessory(dino_id, item.item_id, max_unit)
        return True

    @classmethod
    async def check_accessory(cls, 
            dino_id: Union[ObjectId, Any], 
            item_id: str, 
            downgrade: bool = False, 
            max_down: int = 2) -> Union[bool, "Item"]:
        if hasattr(dino_id, 'id'):
            d_id = dino_id.id
        elif hasattr(dino_id, '_id'):
            d_id = dino_id._id
        else:
            d_id = dino_id

        item = await cls.find_one(cls.owner.id == d_id, {"items_data.item_id": item_id})
        if item:
            if downgrade:
                res = await cls.downgrade_accessory(d_id, item_id, max_down)
                if res:
                    still_exists = await cls.find_one(cls.id == item.id)
                    return still_exists if still_exists else False
                return False
            return item
        return False

    @classmethod
    async def weapon_damage(cls, dino_id: ObjectId, downgrade: bool = False) -> int:
        weapon_items = await cls.find_accessory(dino_id, 'weapon')
        damage = 0
        for weapon in weapon_items:
            damage_data = weapon.get_damage()
            if not damage_data:
                continue
            if not downgrade or await cls.downgrade_type_accessory(dino_id, 'weapon'):
                damage += randint(damage_data['min'], damage_data['max'])
        return max(1, damage)

    @classmethod
    async def armor_protection(cls, dino_id: ObjectId, downgrade: bool = False) -> int:
        armor_items = await cls.find_accessory(dino_id, 'armor')
        armor = 0
        for armor_item in armor_items:
            if not downgrade or await cls.downgrade_type_accessory(dino_id, 'armor'):
                armor += armor_item.get_reflection()
        return armor

    @classmethod
    async def add_accessory(cls, userid: int, dino_id: ObjectId, item_data: dict) -> bool:

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.const import GAME_SETTINGS
        dino_obj = await Dino.find_one(Dino.id == dino_id)
        if not dino_obj:
            return False
        existing = await cls.find_one({"owner": str(dino_id), "items_data.item_id": item_data['item_id']})
        if existing:
            return False
        
        total = await cls.find({"owner": str(dino_id)}).count()
        if total >= GAME_SETTINGS.get('max_accessories', 5):
            return False

        item = await cls.find_one({"owner": userid, "items_data": item_data})
        if item:
            async with Transaction():
                if item.count > 1:
                    item.count -= 1
                    await item.save()
                    new_item = cls(owner=str(dino_id), items_data=item_data, count=1)
                    await new_item.insert()
                else:
                    item.owner = str(dino_id)
                    await item.save()
            return True
        return False

    @classmethod
    async def remove_accessory(cls, userid: int, dino_id: ObjectId, item_id: str) -> bool:

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        item = await cls.find_one({"owner": str(dino_id), "items_data.item_id": item_id})
        if item:
            abilities = item.abilities
            async with Transaction():
                await item.delete()
                from bot.modules.items.item import AddItemToUser
                await AddItemToUser(userid, item_id, 1, abilities)
            return True
        return False

    # Dispatch use_item to specific subclasses
    async def use_item(self, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        item_type = self.type
        if item_type == 'eat':
            return await EatItem._use_item(self, userid, chatid, lang, count, dino, **kwargs)
        elif item_type in ['game', 'journey', 'collecting', 'sleep', 'weapon', 'armor', 'backpack']:
            return await AccessoryItem._use_item(self, userid, chatid, lang, count, dino, **kwargs)
        elif item_type == 'recipe':
            return await RecipeItem._use_item(self, userid, chatid, lang, count, dino, **kwargs)
        elif item_type == 'case':
            return await CaseItem._use_item(self, userid, chatid, lang, count, dino, **kwargs)
        elif item_type == 'egg':
            return await EggItem._use_item(self, userid, chatid, lang, count, dino, **kwargs)
        elif item_type == 'special':
            return await SpecialItem._use_item(self, userid, chatid, lang, count, dino, **kwargs)
        return 'Unknown item type', None

class EatItem(Item):
    @classmethod
    async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.localization import t
        from bot.modules.quests import quest_process
        from bot.models.dinosaur import Dino
        from bot.models.dinosaur import DinoMood
        from bot.modules.items.item import get_name as _get_name
        
        if not dino:
            return 'dino_required', None

        dino_status = await dino.status
        if dino_status == 'sleep':
            return t('item_use.eat.sleep', lang), False
        elif dino_status == 'journey':
            return t('item_use.eat.journey', lang), False

        data_item = item.data
        if data_item['class'] == 'ALL' or (data_item['class'] == dino.data['class']):
            percent = 1
            age = await dino.age()
            repeat_text = ''
            if age.days >= 10:
                percent, repeat = await dino.memory_percent('eat', item.item_id)
                repeat_text = t(
                    f'item_use.eat.repeat.m{repeat}', 
                    lang, percent=int(percent*100)) + '\n'
                if repeat >= 3: 
                    await DinoMood.add(dino.id, 'repeat_eat', -1, 900)

            dino.stats['eat'] = Dino.edited_stats(
                dino.stats['eat'], int((data_item['act'] * count)*percent))
            update_data = {'stats.eat': dino.stats['eat']}

            buffs_text = ''
            if 'buffs' in data_item:
                for stat_name, buff_val in data_item['buffs'].items():
                    if stat_name in dino.stats:
                        val = int(buff_val * count)
                        dino.stats[stat_name] = Dino.edited_stats(
                            dino.stats[stat_name], val)
                        update_data[f'stats.{stat_name}'] = dino.stats[stat_name]
                        if val != 0:
                            sign = '+' if val > 0 else '-'
                            buffs_text += t(
                                f'item_use.buff.{sign}{stat_name}', 
                                lang, unit=abs(val))

            await dino.update_data({'$set': update_data})

            activ_text = t(f'item_use.eat.eat', lang)
            if 'drink' in data_item and data_item['drink']:
                activ_text = t(f'item_use.eat.drink', lang)

            return_text = t('item_use.eat.great', lang, 
            item_name=_get_name(item.item_id, lang), 
            eat_stat=dino.stats['eat'], 
            dino_name=dino.name, activ=activ_text) + '\n'

            if repeat_text:
                return_text += repeat_text
            if buffs_text:
                return_text += buffs_text

            await DinoMood.add(dino.id, 'good_eat', 1, 900)
            await quest_process(userid, 'feed', items=[item.item_id] * count)
            from bot.modules.user.achievements import check_achievements
            await check_achievements(userid, "feed", item.item_id)
            return return_text, True
        else:
            loses_eat = randint(0, (data_item['act'] * count) // 2) * -1
            dino.stats['eat'] = Dino.edited_stats(dino.stats['eat'], loses_eat)
            await dino.update_data({'$set': {'stats.eat': dino.stats['eat']}})
            return_text = t('item_use.eat.bad', lang, item_name=_get_name(item.item_id, lang), loses_eat=loses_eat, dino_name=dino.name)
            await DinoMood.add(dino.id, 'bad_eat', -1, 1200)
            from bot.modules.user.achievements import check_achievements
            await check_achievements(userid, "feed", item.item_id)
            await check_achievements(userid, "feed", "disliked")
            return return_text, True


class AccessoryItem(Item):
    @classmethod
    async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.localization import t
        if not dino or isinstance(dino, bool) or not hasattr(dino, 'status'):
            return 'dino_required', None
        
        if (await dino.status) == item.type:
            return t('item_use.accessory.no_change', lang), False

        from bot.const import GAME_SETTINGS
        dino_accs_count = await Item.find(Item.owner.id == dino.id).count()
        if dino_accs_count >= GAME_SETTINGS.get('max_accessories', 5):
            return t('item_use.accessory.max_items', lang), False

        existing = await Item.find_one(Item.owner.id == dino.id, {"items_data.item_id": item.item_id})
        if existing:
            return t('item_use.accessory.already_have', lang), False

        # Equipping accessory
        res = await Item.add_accessory(userid, dino.id, item.items_data)
        if res:
            from bot.modules.user.achievements import check_achievements
            await check_achievements(userid, "equip_accessory")
            return t('item_use.accessory.change', lang), False
        return 'failed', False


class RecipeItem(Item):
    @classmethod
    async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.items.craft_recipe import craft_recipe
        await craft_recipe(userid, chatid, lang, item.items_data, count)
        return '', False

class CaseItem(Item):
    @classmethod
    async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.localization import t
        from bot.modules.items.item import get_data, AddItemToUser, get_name
        from bot.modules.images_save import send_SmartPhoto
        from bot.modules.markup import markups_menu
        from bot.modules.items.items_groups import get_group
        
        data_item = item.data
        drop = data_item['drop_items']
        shuffle(drop)
        drop_items = {}

        col_repit = random_dict(data_item['col_repit'])
        for _ in range(count):
            for _ in range(col_repit):
                drop_item = None
                while drop_item is None:
                    for iterable_data in drop:
                        if iterable_data['chance'][1] == iterable_data['chance'][0] or randint(1, iterable_data['chance'][1]) <= iterable_data['chance'][0]:
                            drop_item = iterable_data.copy()
                            if isinstance(drop_item['id'], dict):
                                drop_item['id'] = choice(get_group(drop_item['id']['group']))
                            elif isinstance(drop_item['id'], list):
                                drop_item['id'] = choice(drop_item['id'])
                            break

            drop_col = random_dict(drop_item['col'])
            if drop_item['id'] in drop_items:
                drop_items[drop_item['id']]['col'] += drop_col
            else:
                drop_items[drop_item['id']] = {"col": drop_col, "abilities": drop_item['abilities']}

        for drop_id, data in drop_items.items():
            await AddItemToUser(userid, drop_id, data['col'], data['abilities'])
            drop_item_data = get_data(drop_id)
            item_name = get_name(drop_id, lang)
            image = f"images/items/generated/{drop_id}.png" if 'image' in drop_item_data else "images/items/null.png"
            await send_SmartPhoto(userid, image, t('item_use.case.drop_item', lang, item_name=item_name, col=data['col']), 'Markdown', await markups_menu(userid, 'last_menu', lang))
        return '', True

class EggItem(Item):
    @classmethod
    async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.localization import t
        from bot.models.user import User
        from bot.models.dinosaur import DinoMood, Egg
        from bot.modules.images import create_eggs_image
        from bot.modules.markup import markups_menu
        from bot.modules.data_format import list_to_inline
        from bot.modules.items.item_tools import item_code
        from bot.exec import bot
        
        user = await User.find_one(User.userid == userid)
        if not user:
            return 'user_not_found', False
            
        dino_limit_col = await user.max_dino_col()
        dino_limit = dino_limit_col['standart']  

        if dino_limit['now'] < dino_limit['limit']:
            res_egg_choose = await Egg.find_one(Egg.owner_id == userid, Egg.stage == 'choosing', Egg.quality == item.data['inc_type'])
            if not res_egg_choose:
                egg_data = Egg(stage='choosing', owner_id=userid, quality=item.data['inc_type'])
                egg_data.choose_eggs()
            else:
                egg_data = res_egg_choose
                if egg_data.id_message:
                    try:
                        await bot.delete_message(userid, egg_data.id_message)
                    except Exception: pass

            image = await create_eggs_image(egg_data.eggs)
            code = await item_code(item_dict=item.items_data, userid=userid)
            btn = {t('item_use.egg.edit_buttons', lang): f'item egg_edit {code}'}
            buttons = {}
            for i in range(3): 
                buttons[f'🥚 {i+1}'] = f'item egg {code} {egg_data.eggs[i]}'
            buttons = list_to_inline([btn, buttons])

            mes = await bot.send_photo(userid, image, caption=t('item_use.egg.egg_answer', lang), parse_mode='Markdown', reply_markup=buttons)
            egg_data.id_message = mes.message_id
            egg_data.start_choosing = int(time.time())

            if not res_egg_choose: 
                await egg_data.insert()
            else:
                await egg_data.save()

            await bot.send_message(userid, t('item_use.egg.plug', lang), reply_markup=await markups_menu(userid, 'last_menu', lang))
            return '', False
        else:
            return t('item_use.egg.egg_limit', lang, limit=dino_limit['limit']), False

class SpecialItem(Item):
    @classmethod
    async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):

        from bot.models.user import User
        user_obj = None
        try:
            uid = int(userid)
            user_obj = await User.find_one(User.userid == uid)
            if not user_obj:
                user_obj = await User(userid=uid).insert()
        except Exception:
            try:
                user_obj = await User.find_one(User.id == ObjectId(userid))
            except Exception:
                pass
        if not user_obj:
            return False

        from bot.modules.localization import t
        from bot.models.user import User
        from bot.models.activity import Activity
        
        data_item = item.data
        if data_item['class'] == 'defrosting' and dino:
            status = await dino.check_status()
            if status != 'inactive':
                return t('item_use.special.defrost.notinc', lang), False
            else:
                await Activity.get_pymongo_collection().delete_many({
                    "activity_type": "inactive",
                    "$or": [
                        {"dino_id": dino.id},
                        {"dino_id": str(dino.id)},
                        {"dino.$id": dino.id},
                        {"dino.$id": str(dino.id)}
                    ]
                })
                return t('item_use.special.defrost.ok', lang), True

        elif data_item['class'] == 'freezing' and dino:
            status = await dino.check_status()
            if status == 'pass':
                end = 0 if data_item['time'] == 'forever' else data_item['time'] + int(time.time())
                from bot.models.activity import Activity
                act = Activity(
                    dino_id=dino.id,
                    activity_type='inactive',
                    start_time=int(time.time()),
                    end_time=end
                )
                await act.insert()
                return t('item_use.special.freez', lang), True
            else:
                return t('alredy_busy', lang), False

        elif data_item['class'] == 'premium':
            from bot.models.user import Subscription
            raw_time = data_item['premium_time']
            if isinstance(raw_time, str) and raw_time == 'inf':
                await Subscription.award_premium(userid, 'inf')
                time_str = '∞'
            else:
                total_seconds = raw_time * count
                await Subscription.award_premium(userid, total_seconds)
                days = total_seconds // 86400
                time_str = f'{days} дн.' if days else f'{total_seconds // 3600} ч.'
            return t('item_use.special.premium', lang, premium_time=time_str), True

        elif data_item['class'] == 'dino_slot':
            user_doc = await User.find_one(User.userid == userid)
            if user_doc:
                slots_to_add = data_item.get('abilities', {}).get('count', 1) * count
                user_doc.add_slots += slots_to_add
                await user_doc.save()
                return t('item_use.special.add_slot', lang), True
            else:
                return t('item_use.special.error_slot', lang), False

        elif data_item['class'] == 'reborn':
            from bot.models.dinosaur import DeadDino, Dino as DinoModel
            reborn_id = kwargs.get('reborn_data', None)
            if not reborn_id:
                return 'failed', False
            dct_dino = await DeadDino.find_one(DeadDino.id == ObjectId(reborn_id))
            if dct_dino:
                user_doc = await User.find_one(User.userid == userid)
                if user_doc:
                    dino_limit_col = await user_doc.max_dino_col()
                    dino_limit = dino_limit_col['standart']
                    if dino_limit['now'] < dino_limit['limit']:
                        res, alt_id = await DinoModel.insert_dino(userid, dct_dino.data_id, dct_dino.quality)
                        if res:
                            await res.update({'$set': {'name': dct_dino.name}})
                            if dct_dino.stats:
                                for stat_name, stat_val in dct_dino.stats.items():
                                    await res.update({'$set': {f'stats.{stat_name}': stat_val}})
                            await dct_dino.delete()
                            from bot.modules.user.achievements import check_achievements
                            await check_achievements(userid, "revive_dino")
                            return t('item_use.special.reborn.ok', lang, limit=dino_limit['limit']), True
                        else:
                            return 'failed', False
                    else:
                        return t('item_use.special.reborn.limit', lang, limit=dino_limit['limit']), False
                else:
                    return 'user_not_found', False
            else:
                return 'failed', False

        elif data_item['class'] == 'transport':
            from bot.models.dinosaur import Dino as DinoModel, DinoOwners
            abilities = item.abilities
            if abilities.get('data_id', 0) == 0:
                if dino:
                    await Activity.get_pymongo_collection().delete_many({
                        "$or": [
                            {"dino_id": dino.id},
                            {"dino_id": str(dino.id)},
                            {"dino_ids": dino.id},
                            {"dino_ids": str(dino.id)},
                            {"dino.$id": dino.id},
                            {"dino.$id": str(dino.id)}
                        ]
                    })
                    act = Activity(
                        dino=dino,
                        activity_type='inactive',
                        start_time=int(time.time()),
                        end_time=0
                    )
                    await act.insert()

                    user_doc = await User.find_one(User.userid == userid)
                    if user_doc:
                        if user_doc.settings.get('last_dino') == dino.id:
                            user_doc.settings['last_dino'] = None
                            await user_doc.save()

                    await DinoOwners.find(DinoOwners.dino.id == dino.id).delete()
                    await Item.add(userid, item.item_id, 1, {'data_id': dino.alt_id})
                    return t('transport.add_dino', lang), True
                else:
                    return t('transport.error', lang), False
            else:
                user_doc = await User.find_one(User.userid == userid)
                if user_doc:
                    max_dc = await user_doc.max_dino_col()
                    cuds = max_dc['standart']['now']
                    max_dc_st = max_dc['standart']['limit']

                    if cuds + 1 > max_dc_st:
                        return t('transport.max_dino', lang), False
                    else:
                        alt_id = abilities.get('data_id')
                        dino_dtc = await DinoModel.find_one(DinoModel.alt_id == alt_id)
                        if dino_dtc:
                            await DinoOwners.create_connection(dino_dtc.id, userid)
                            from bot.models.user import DinoCollection
                            await DinoCollection.add_to_collection(userid, dino_dtc.data_id)
                            from bot.modules.user.achievements import check_achievements
                            await check_achievements(userid, "dino_hatch")
                            await check_achievements(userid, "collection_add")
                            await Activity.get_pymongo_collection().delete_many({
                                "activity_type": "inactive",
                                "$or": [
                                    {"dino_id": dino_dtc.id},
                                    {"dino_id": str(dino_dtc.id)},
                                    {"dino.$id": dino_dtc.id},
                                    {"dino.$id": str(dino_dtc.id)}
                                ]
                            })
                            return t('transport.delete_dino', lang), True
                        else:
                            return t('transport.error', lang), False
                else:
                    return t('transport.error', lang), False
        return 'failed', False

def random_dict(data: dict) -> int:
    if data.get('type') == 'random':
        return randint(data['min'], data['max'])
    return data.get('act', 0)

class ItemCraft(PrivateModelMixin, Document):
    alt_code: str = ""
    userid: int = 0
    dino: Optional[Link[Dino]] = None
    time_end: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)

    class Settings:
        name = "item_craft"
        indexes = [
            IndexModel([("alt_code", TEXT)], unique=True, name="alt_code"),
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("dino", ASCENDING)], name="dino"),
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

    @classmethod
    async def create_task(cls, craft_id: ObjectId, end_time: int):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task("check_items", {"craft_id": str(craft_id)}, run_at=end_time, resource_id=f"craft:{craft_id}")

    @classmethod
    async def cancel_task(cls, craft_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"craft:{craft_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        import time
        current_time = int(time.time())
        crafts = await cls.find().to_list()
        for craft in crafts:
            res_id = f"craft:{craft.id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, craft.time_end)
                await cls.create_task(craft.id, run_at)

class Farm(PrivateModelMixin, Document):
    owner_id: int = 0
    land_id: int = 0
    plant_id: str = ""
    plant_time: int = 0
    watered: bool = False

    class Settings:
        name = "farm"
