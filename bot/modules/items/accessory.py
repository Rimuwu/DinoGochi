from typing import Optional, List
from bson import ObjectId
from bot.models.items import Item
from bot.models.dinosaur import Dino

async def Item.find_accessory(dino: Dino, acc_type: Optional[str] = None) -> list[list]:
    # We return list of lists [(item_dict, index)] for backwards compatibility
    items = await Item.Item.find_accessory(dino.id, acc_type)
    return [[i.items_data, idx] for idx, i in enumerate(items)]

async def Item.downgrade_accessory(dino: Dino, item_id: str, max_unit: int = 2) -> bool:
    return await Item.Item.downgrade_accessory(dino.id, item_id, max_unit)

async def Item.downgrade_type_accessory(dino: Dino, acc_type: str, max_unit: int = 2) -> bool:
    return await Item.Item.downgrade_type_accessory(dino.id, acc_type, max_unit)

async def Item.check_accessory(dino: Dino, item_id: str, downgrade: bool = False, max_down: int = 2) -> bool:
    return await Item.Item.check_accessory(dino.id, item_id, downgrade, max_down)

async def Item.weapon_damage(dino: Dino, downgrade: bool = False) -> int:
    return await Item.Item.weapon_damage(dino.id, downgrade)

async def Item.armor_protection(dino: Dino, downgrade: bool = False) -> int:
    return await Item.Item.armor_protection(dino.id, downgrade)

async def Item.add_accessory(dino: Dino, item_data: dict) -> bool:
    # Get user owner id from some context or pass it? Wait, item is owned by user, let's find user from DinoOwners
    owner = await dino.Dino.get_owner_by_id()
    if owner:
        return await Item.add_accessory(owner.owner_id, dino.id, item_data)
    return False

async def Item.remove_accessory(dino_id: ObjectId, item_id: str) -> bool:
    # Get user owner id
    from bot.models.dinosaur import DinoOwners
    owner = await DinoOwners.find_one(DinoOwners.dino_id == str(dino_id), DinoOwners.type == 'owner')
    if owner:
        return await Item.Item.remove_accessory(owner.owner_id, dino_id, item_id)
    return False