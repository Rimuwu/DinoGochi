import os

file_path = 'bot/models/items.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "from beanie import Document, PydanticObjectId",
    "from beanie import Document, PydanticObjectId, Link\nfrom bot.models.base_private import PrivateModelMixin\nfrom bot.models.user import User\nfrom bot.models.dinosaur import Dino"
)

# 2. Inherit classes
content = content.replace("class Item(Document):", "class Item(PrivateModelMixin, Document):")
content = content.replace("class ItemCraft(Document):", "class ItemCraft(PrivateModelMixin, Document):")
content = content.replace("class Farm(Document):", "class Farm(PrivateModelMixin, Document):")

# 3. Field and settings replacements
content = content.replace("owner_id: Optional[Union[int, str]] = None", "owner: Optional[Union[Link[User], Link[Dino]]] = None")
content = content.replace('IndexModel([("owner_id", ASCENDING)], name="owner_id")', 'IndexModel([("owner", ASCENDING)], name="owner")')

content = content.replace("userid: Optional[int] = None", "user: Optional[Link[User]] = None")
content = content.replace("dino_id: Optional[PydanticObjectId] = None", "dino: Optional[Link[Dino]] = None")
content = content.replace('IndexModel([("userid", ASCENDING)], name="userid")', 'IndexModel([("user", ASCENDING)], name="user")')
content = content.replace('IndexModel([("dino_id", ASCENDING)], name="dino_id")', 'IndexModel([("dino", ASCENDING)], name="dino")')

# For Farm
content = content.replace("owner_id: Optional[int] = None", "owner: Optional[Link[User]] = None")

# 4. Inject User resolution in methods
# Helper replacement for methods that take userid:
user_resolution = """
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
"""

# Let's perform precise replacements for method headers:
# Item.add
content = content.replace(
    "async def add(cls, userid: Union[int, str], item_id: str, count: int = 1, abilities: dict | None = None):",
    "async def add(cls, userid: Union[int, str], item_id: str, count: int = 1, abilities: dict | None = None):\n" + user_resolution
)

# Item.remove
content = content.replace(
    "async def remove(cls, userid: Union[int, str], item_id: str, count: int = 1, abilities: dict | None = None):",
    "async def remove(cls, userid: Union[int, str], item_id: str, count: int = 1, abilities: dict | None = None):\n" + user_resolution
)

# Item.check_item
content = content.replace(
    "async def check_item(cls, userid: Union[int, str], item_data: dict, count: int = 1) -> dict:",
    "async def check_item(cls, userid: Union[int, str], item_data: dict, count: int = 1) -> dict:\n" + user_resolution
)

# Item.check_count
content = content.replace(
    "async def check_count(cls, userid: Union[int, str], count: int, item_id: str, abilities: dict | None = None) -> bool:",
    "async def check_count(cls, userid: Union[int, str], count: int, item_id: str, abilities: dict | None = None) -> bool:\n" + user_resolution
)

# Item.check_and_return_dif
content = content.replace(
    "async def check_and_return_dif(cls, userid: Union[int, str], item_id: str, abilities: dict | None = None) -> int:",
    "async def check_and_return_dif(cls, userid: Union[int, str], item_id: str, abilities: dict | None = None) -> int:\n" + user_resolution
)

# Item.delete_abilities
content = content.replace(
    "async def delete_abilities(cls, item_data: dict, characteristic: str, unit: int, count: int, userid: Union[int, str]):",
    "async def delete_abilities(cls, item_data: dict, characteristic: str, unit: int, count: int, userid: Union[int, str]):\n" + user_resolution
)

# Item.downgrade
content = content.replace(
    "async def downgrade(cls, userid: Union[int, str], item: dict, characteristic: str, amount: int):",
    "async def downgrade(cls, userid: Union[int, str], item: dict, characteristic: str, amount: int):\n" + user_resolution
)

# Item.add_accessory
content = content.replace(
    "async def add_accessory(cls, userid: int, dino_id: ObjectId, item_data: dict) -> bool:",
    "async def add_accessory(cls, userid: int, dino_id: ObjectId, item_data: dict) -> bool:\n" + user_resolution
)

# Item.remove_accessory
content = content.replace(
    "async def remove_accessory(cls, userid: int, dino_id: ObjectId, item_id: str) -> bool:",
    "async def remove_accessory(cls, userid: int, dino_id: ObjectId, item_id: str) -> bool:\n" + user_resolution
)

# Item.use_item
content = content.replace(
    "async def use_item(self, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):",
    "async def use_item(self, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):\n" + user_resolution
)

# EatItem._use_item
content = content.replace(
    "async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):",
    "async def _use_item(cls, item: Item, userid: int, chatid: int, lang: str, count: int = 1, dino = None, **kwargs):\n" + user_resolution
)

# 5. DB query replaces
content = content.replace("cls.owner_id == userid", "cls.owner.id == user_obj.id")
content = content.replace("cls.owner_id == str(dino_id)", "cls.owner.id == dino_id")
content = content.replace("cls.owner_id == str(d_id)", "cls.owner.id == d_id")
content = content.replace("Item.owner_id == str(dino.id)", "Item.owner.id == dino.id")
content = content.replace("Egg.owner_id == userid", "Egg.owner.id == user_obj.id")
content = content.replace("owner_id=userid", "owner=user_obj")
content = content.replace("owner_id=str(dino_id)", "owner=dino_obj")
content = content.replace("item.owner_id = str(dino_id)", "item.owner = dino_obj")

# In Item.add_accessory, dino_obj resolution is needed:
dino_resolution = """        dino_obj = await Dino.find_one(Dino.id == dino_id)
        if not dino_obj:
            return False"""
content = content.replace("existing = await cls.find_one(cls.owner.id == dino_id, {\"items_data.item_id\": item_data['item_id']})",
                          dino_resolution + "\n        existing = await cls.find_one(cls.owner.id == dino_id, {\"items_data.item_id\": item_data['item_id']})")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Properly updated items.py")
