from typing import Dict, Any, Optional
from bson.objectid import ObjectId
import time
from pymongo.errors import DuplicateKeyError
from bot.models.activity.base import Activity
from bot.models.dinosaur import Dino

class WorkActivity(Activity):
    userid: int = 0
    use_energy: bool = False
    last_check: int
    alt_code: str
    min_time: int
    max_time: int
    ahtung_lvl: int = 0
    coins: Optional[int] = None
    max_coins: Optional[int] = None
    items: Optional[Dict[str, Any]] = None
    max_items: Optional[int] = None
    item_per_hour: Optional[int] = None
    last_view: int = 0
    checks: int = 3

    @classmethod
    async def start_mine(cls, dino_baseid: ObjectId, owner_id: int, action_type: str):
        from bot.modules.data_format import random_code
        from bot.models.items import Item
        from bot.modules.items.item import get_data
        from bot.modules.items.items_groups import get_group
        
        works_data = {
            "mine": {
                "time": 3600 * 2,
                "max_coins": 7000,
                "max_items": 7
            }
        }
        
        dino_oid = ObjectId(dino_baseid)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False

            act = cls(
                dino=dino_obj,
                activity_type='mine',
                start_time=int(time.time()),
                end_time=int(time.time()) + works_data['mine']['time'],
                userid=owner_id,
                use_energy=False,
                last_check=int(time.time()),
                alt_code=random_code(),
                min_time=works_data['mine']['time'],
                max_time=works_data['mine']['time'],
                ahtung_lvl=0,
                last_view=0,
                checks=3
            )
            if action_type == 'coins':
                act.coins = 0
                act.max_coins = works_data['mine']['max_coins']
            elif action_type == 'ore':
                act.items = {}
                act.max_items = works_data['mine']['max_items']
                act.item_per_hour = 3
                dino = dino_obj
                if dino:
                    equipped_items = await Item.find(Item.owner.id == dino.id).to_list()
                    for acc in equipped_items:
                        cap = acc.get_capacity()
                        if cap > 0:
                            await Item.downgrade_accessory(dino.id, acc.items_data['item_id'], 10)
                            act.max_items += cap
                    for key in get_group('pickaxes'):
                        acc = await Item.check_accessory(dino, key, True, 15)
                        if acc:
                            act.item_per_hour += acc.get_effectiv()
            try:
                await act.insert()
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def start_bank(cls, dino_baseid: ObjectId, owner_id: int, action_type: str):
        from bot.modules.data_format import random_code
        from bot.models.items import Item
        from bot.modules.items.item import get_data
        from bot.modules.items.items_groups import get_group
        
        works_data = {
            "bank": {
                "time": 3600 * 4,
                "max_coins": 15000,
                "max_items": 6
            }
        }
        
        dino_oid = ObjectId(dino_baseid)
        existing = await Activity.find_one(
            Activity.dino.id == dino_oid,
            with_children=True
        )
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == dino_oid)
            if not dino_obj:
                return False

            act = cls(
                dino=dino_obj,
                activity_type='bank',
                start_time=int(time.time()),
                end_time=int(time.time()) + works_data['bank']['time'],
                userid=owner_id,
                use_energy=False,
                last_check=int(time.time()),
                alt_code=random_code(),
                min_time=works_data['bank']['time'],
                max_time=works_data['bank']['time'],
                ahtung_lvl=0,
                last_view=0,
                checks=3
            )
            if action_type == 'coins':
                act.coins = 0
                act.max_coins = works_data['bank']['max_coins']
            elif action_type == 'recipes':
                act.items = {}
                act.max_items = works_data['bank']['max_items']
                act.item_per_hour = 1
                dino = dino_obj
                if dino:
                    equipped_items = await Item.find(Item.owner.id == dino.id).to_list()
                    for acc in equipped_items:
                        cap = acc.get_capacity()
                        if cap > 0:
                            await Item.downgrade_accessory(dino.id, acc.items_data['item_id'], 10)
                            act.max_items += cap
            try:
                await act.insert()
            except DuplicateKeyError:
                return False
            return True
        return False

    @classmethod
    async def start_sawmill(cls, dino_baseid: ObjectId, owner_id: int, action_type: str):
        from bot.modules.data_format import random_code
        from bot.models.items import Item
        from bot.modules.items.item import get_data
        from bot.modules.items.items_groups import get_group
        
        works_data = {
            "sawmill": {
                "time": 3600 * 2,
                "max_coins": 7000,
                "max_items": 15
            }
        }
        
        existing = await Activity.find_one(Activity.dino.id == ObjectId(dino_baseid), with_children=True)
        if not existing:
            dino_obj = await Dino.find_one(Dino.id == ObjectId(dino_baseid))
            if not dino_obj:
                return False

            act = cls(
                dino=dino_obj,
                activity_type='sawmill',
                start_time=int(time.time()),
                end_time=int(time.time()) + works_data['sawmill']['time'],
                userid=owner_id,
                use_energy=False,
                last_check=int(time.time()),
                alt_code=random_code(),
                min_time=works_data['sawmill']['time'],
                max_time=works_data['sawmill']['time'],
                ahtung_lvl=0,
                last_view=0,
                checks=3
            )
            if action_type == 'coins':
                act.coins = 0
                act.max_coins = works_data['sawmill']['max_coins']
            elif action_type == 'wood':
                act.items = {}
                act.max_items = works_data['sawmill']['max_items']
                act.item_per_hour = 5
                dino = dino_obj
                if dino:
                    equipped_items = await Item.find(Item.owner.id == dino.id).to_list()
                    for acc in equipped_items:
                        cap = acc.get_capacity()
                        if cap > 0:
                            await Item.downgrade_accessory(dino.id, acc.items_data['item_id'], 10)
                            act.max_items += cap
                    for key in get_group('axes'):
                        acc = await Item.check_accessory(dino, key, True, 15)
                        if acc:
                            act.item_per_hour += acc.get_effectiv()
            await act.insert()
            return True
        return False

    @classmethod
    async def end_work(cls, dino_baseid: ObjectId):
        from bot.modules.items.item import AddItemToUser, get_item_dict
        from beanie.operators import In

        res = await cls.find_one(
            cls.dino.id == ObjectId(dino_baseid),
            In(cls.activity_type, ['bank', 'mine', 'sawmill'])
        )
        if res:
            sended = res.userid
            if sended:
                from bot.models.user import User
                user_obj = await User.find_one(User.userid == sended)
                if user_obj:
                    if res.coins is not None:
                        await user_obj.add_coins(res.coins)
                    elif res.items is not None:
                        for key, item in res.items.items():
                            data = get_item_dict(key)
                            item_id = data['item_id']
                            abilities = data.get('abilities', {})
                            await AddItemToUser(sended, item_id, item['count'], abilities)
            await res.delete()
            return True
        return False
