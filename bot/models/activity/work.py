from typing import Dict, Any, Optional
from bson.objectid import ObjectId
import time
from bot.models.activity.base import Activity

class WorkActivity(Activity):
    send: int
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
        from bot.models.dinosaur import Dino
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
        
        existing = await cls.find_one(cls.dino_id == ObjectId(dino_baseid))
        if not existing:
            act = cls(
                dino_id=str(dino_baseid),
                activity_type='mine',
                start_time=int(time.time()),
                end_time=int(time.time()) + works_data['mine']['time'],
                send=owner_id,
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
                dino = await Dino().create(dino_baseid)
                if dino:
                    for key in get_group('backpacks'):
                        acc = await Item.check_accessory(dino, key, True, 10)
                        if acc:
                            act.max_items += acc.get_capacity()
                    for key in get_group('pickaxes'):
                        acc = await Item.check_accessory(dino, key, True, 15)
                        if acc:
                            act.item_per_hour += acc.get_effectiv()
            await act.insert()
            return True
        return False

    @classmethod
    async def start_bank(cls, dino_baseid: ObjectId, owner_id: int, action_type: str):
        from bot.modules.data_format import random_code
        from bot.models.dinosaur import Dino
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
        
        existing = await cls.find_one(cls.dino_id == ObjectId(dino_baseid))
        if not existing:
            act = cls(
                dino_id=str(dino_baseid),
                activity_type='bank',
                start_time=int(time.time()),
                end_time=int(time.time()) + works_data['bank']['time'],
                send=owner_id,
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
                dino = await Dino().create(dino_baseid)
                if dino:
                    for key in get_group('backpacks'):
                        acc = await Item.check_accessory(dino, key, True, 10)
                        if acc:
                            act.max_items += acc.get_capacity()
            await act.insert()
            return True
        return False

    @classmethod
    async def start_sawmill(cls, dino_baseid: ObjectId, owner_id: int, action_type: str):
        from bot.modules.data_format import random_code
        from bot.models.dinosaur import Dino
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
        
        existing = await cls.find_one(cls.dino_id == ObjectId(dino_baseid))
        if not existing:
            act = cls(
                dino_id=str(dino_baseid),
                activity_type='sawmill',
                start_time=int(time.time()),
                end_time=int(time.time()) + works_data['sawmill']['time'],
                send=owner_id,
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
                dino = await Dino().create(dino_baseid)
                if dino:
                    for key in get_group('backpacks'):
                        acc = await Item.check_accessory(dino, key, True, 10)
                        if acc:
                            act.max_items += acc.get_capacity()
                    for key in get_group('axes'):
                        acc = await Item.check_accessory(dino, key, True, 15)
                        if acc:
                            act.item_per_hour += acc.get_effectiv()
            await act.insert()
            return True
        return False

    @classmethod
    async def end_work(cls, dino_baseid: ObjectId):
        from bot.models.user import User
        from bot.modules.items.item import AddItemToUser, get_item_dict
        
        from beanie.operators import In

        res = await cls.find_one(
            cls.dino_id == ObjectId(dino_baseid),
            In(cls.activity_type, ['bank', 'mine', 'sawmill'])
        )
        if res:
            sended = res.send
            if res.coins is not None:
                user_obj = await User.find_one(User.userid == sended)
                if user_obj:
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
