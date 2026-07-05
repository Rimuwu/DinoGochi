from typing import Optional, List, Dict, Any, Union
from beanie import Document
from pydantic import Field
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

class User(Document):
    userid: Optional[int] = None

    @property
    def _id(self) -> ObjectId:
        return self.id

    name: str = ""
    avatar: str = ""
    last_message_time: int = 0
    last_markup: str = "main_menu"
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        'notifications': True,
        'last_dino': None,
        'profile_view': 1,
        'inv_view': [2, 3],
        'my_name': '',
        'no_talk': False,
        'confidentiality': False,
        'inv_sort': 'name_asc'
    })
    notifications: Dict[str, Any] = Field(default_factory=dict)
    coins: int = 100
    super_coins: int = 0
    lvl: int = 0
    xp: int = 0
    add_slots: int = 0
    dungeon: Dict[str, Any] = Field(default_factory=dict)
    saved: Dict[str, Any] = Field(default_factory=lambda: {
        'backgrounds': []
    })

    class Settings:
        name = "users"
        keep_nulls = False
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid"),
            IndexModel([("coins", DESCENDING)], name="coins_desc"),
            IndexModel([("super_coins", DESCENDING)], name="super_coins_desc"),
            IndexModel([("lvl", DESCENDING), ("xp", DESCENDING)], name="lvl_xp_desc")
        ]

    async def create(self, userid: int):
        db_user = await User.find_one(User.userid == userid)
        if db_user:
            for field_name in self.model_fields:
                val = getattr(db_user, field_name)
                setattr(self, field_name, val)
            self.id = db_user.id
            if hasattr(db_user, '_pre_save_values'):
                self._pre_save_values = db_user._pre_save_values
            if hasattr(db_user, '_state'):
                self._state = db_user._state
        else:
            self.userid = userid
        return self

    async def get_dinos(self, all_dinos: bool = True) -> list:
        from bot.models.dinosaur import DinoOwners, Dino
        dino_list = []
        if all_dinos:
            res = await DinoOwners.find(DinoOwners.owner_id == self.userid).to_list()
        else:
            res = await DinoOwners.find(DinoOwners.owner_id == self.userid, DinoOwners.type == 'owner').to_list()
        for conn in res:
            try:
                db_id = ObjectId(conn.dino_id)
                d = await Dino.find_one(Dino.id == db_id)
            except Exception:
                d = None
            if not d:
                d = await Dino.find_one(Dino.alt_id == conn.dino_id)
            if d:
                dino_list.append(d)
        return dino_list

    @property
    async def get_col_dinos(self) -> int:
        from bot.models.dinosaur import DinoOwners
        return await DinoOwners.find(DinoOwners.owner_id == self.userid).count()

    @property
    async def get_eggs(self) -> list:
        from bot.models.dinosaur import Egg
        return await Egg.find(Egg.owner_id == self.userid, Egg.stage == 'incubation').to_list()

    async def get_inventory(self, exclude_ids: list = []):
        from bot.models.items import Item
        inv = await Item.find(Item.owner_id == self.userid).to_list()
        filtered_inv = []
        count = 0
        for item in inv:
            if item.items_data.get('item_id') not in exclude_ids:
                filtered_inv.append({
                    '_id': item.id,
                    'owner_id': item.owner_id,
                    'items_data': item.items_data,
                    'count': item.count
                })
                count += item.count
        return filtered_inv, count

    @property
    async def get_friends(self) -> dict:
        from bot.models.user import Friend
        friends_list = await Friend.find(Friend.userid == self.userid).to_list()
        friends_dict = {'friends': [f.friendid for f in friends_list], 'requests': []}
        return friends_dict

    @property
    async def premium(self) -> bool:
        import time
        sub = await Subscription.find_one(Subscription.userid == self.userid)
        if sub:
            if isinstance(sub.sub_end, str) and sub.sub_end == "inf":
                return True
            if isinstance(sub.sub_end, (int, float)) and sub.sub_end > time.time():
                return True
        return False

    @property
    async def lang(self) -> str:
        l = await Lang.find_one(Lang.userid == self.userid)
        return l.lang if l else "en"

    def view(self):
        print(f'userid: {self.userid}')
        print(f'DATA: {self.__dict__}')

    async def full_delete(self):
        from bot.models.items import Item, ItemCraft
        from bot.models.market import Product, Seller, Preferential, Puhs
        from bot.models.dinosaur import DeadDino, Egg, DinoOwners, Dino
        from bot.models.tavern import DailyAward, Quest, InsideShop, Tavern
        from bot.models.other import MessageLog, DeadUser, States
        from bot.models.group import GroupUser
        from bot.models.user import Referral, Lang, Ad, Subscription, DinoCollection, Friend

        await Item.find(Item.owner_id == self.userid).delete()
        await Product.find(Product.owner_id == self.userid).delete()
        await DeadDino.find(DeadDino.owner_id == self.userid).delete()
        await Egg.find(Egg.owner_id == self.userid).delete()
        await Seller.find(Seller.owner_id == self.userid).delete()
        await Puhs.find(Puhs.userid == self.userid).delete()
        await DailyAward.find(DailyAward.owner_id == self.userid).delete()
        await Quest.find(Quest.owner_id == self.userid).delete()
        await InsideShop.find(InsideShop.owner_id == self.userid).delete()
        await Preferential.find(Preferential.userid == self.userid).delete()

        await Referral.find(Referral.userid == self.userid).delete()
        await Lang.find(Lang.userid == self.userid).delete()
        await Ad.find(Ad.userid == self.userid).delete()
        await DeadUser.find(DeadUser.userid == self.userid).delete()
        await Subscription.find(Subscription.userid == self.userid).delete()
        from bot.modules.user.tavern_redis import remove_from_tavern
        try:
            await remove_from_tavern(self.userid)
        except Exception:
            pass
        await Tavern.find(Tavern.owner_id == self.userid).delete()
        await MessageLog.find(MessageLog.userid == self.userid).delete()
        await ItemCraft.find(ItemCraft.userid == self.userid).delete()

        await GroupUser.find(GroupUser.user_id == self.userid).delete()
        await DinoCollection.find(DinoCollection.user_id == self.userid).delete()

        dinos_conn = await DinoOwners.find(DinoOwners.owner_id == self.userid).to_list()
        for conn in dinos_conn:
            if conn.type == 'owner':
                alt_conn = await DinoOwners.find(DinoOwners.dino_id == conn.dino_id, DinoOwners.type == 'add_owner').to_list()
                if len(alt_conn) > 1:
                    await DinoOwners.find_one(DinoOwners.dino_id == conn.dino_id).update({"$set": {"type": "owner"}})
                else:
                    try:
                        dino_d = await Dino.find_one(Dino.id == ObjectId(conn.dino_id))
                    except Exception:
                        dino_d = None
                    if not dino_d:
                        dino_d = await Dino.find_one(Dino.alt_id == conn.dino_id)
                    if dino_d:
                        await dino_d.delete()
            await conn.delete()

        await Friend.find(Friend.userid == self.userid).delete()
        await Friend.find(Friend.friendid == self.userid).delete()

        from bot.modules.managment.tracking import update_all_user_track
        await update_all_user_track(self.userid, 'delete_account')

        await self.delete()

    async def get_last_dino(self):
        from bot.modules.user.user import last_dino
        return await last_dino(self)

    async def max_dino_col(self):
        from bot.modules.user.user import max_dino_col
        return await max_dino_col(self.lvl, self.userid, await self.premium, self.add_slots)

    async def get_avatar(self):
        from bot.modules.user.avatar import get_avatar
        return await get_avatar(self.userid)

    async def add_coins(self, amount: int):
        self.coins += amount
        await self.save()
        from bot.modules.logs import log
        log(f"Edit coins: user: {self.userid} col: {amount}", 1, "add_coins")

    async def remove_coins(self, amount: int) -> bool:
        if self.coins < amount:
            return False
        self.coins -= amount
        await self.save()
        from bot.modules.logs import log
        log(f"Edit coins: user: {self.userid} col: {-amount}", 1, "remove_coins")
        return True

    async def add_super_coins(self, amount: int):
        self.super_coins += amount
        await self.save()
        from bot.modules.logs import log
        log(f"Edit super_coins: user: {self.userid} col: {amount}", 1, "add_super_coins")

    async def remove_super_coins(self, amount: int) -> bool:
        if self.super_coins < amount:
            return False
        self.super_coins -= amount
        await self.save()
        from bot.modules.logs import log
        log(f"Edit super_coins: user: {self.userid} col: {-amount}", 1, "remove_super_coins")
        return True

    async def add_item(self, item_id: str, count: int = 1, abilities: dict | None = None):
        from bot.models.items import Item
        return await Item.add(self.userid, item_id, count, abilities)

    async def remove_item(self, item_id: str, count: int = 1, abilities: dict | None = None) -> bool:
        from bot.models.items import Item
        return await Item.remove(self.userid, item_id, count, abilities)

    @classmethod
    async def transfer_coins(cls, from_userid: int, to_userid: int, amount: int) -> bool:
        from bot.modules.overwriting.DataCalsses import Transaction
        async with Transaction():
            from_user = await cls.find_one(cls.userid == from_userid)
            to_user = await cls.find_one(cls.userid == to_userid)
            if from_user and to_user and await from_user.remove_coins(amount):
                await to_user.add_coins(amount)
                return True
        return False

    @classmethod
    async def transfer_super_coins(cls, from_userid: int, to_userid: int, amount: int) -> bool:
        from bot.modules.overwriting.DataCalsses import Transaction
        async with Transaction():
            from_user = await cls.find_one(cls.userid == from_userid)
            to_user = await cls.find_one(cls.userid == to_userid)
            if from_user and to_user and await from_user.remove_super_coins(amount):
                await to_user.add_super_coins(amount)
                return True
        return False

    async def set_last_markup(self, markup: str):
        self.last_markup = markup
        await self.save()

    async def set_avatar(self, avatar: str):
        self.avatar = avatar
        await self.save()

    async def set_name(self, name: str):
        self.name = name
        await self.save()

    async def set_lang(self, lang: str):
        from bot.models.user import Lang
        await Lang.set_user_lang(self.userid, lang)

    async def add_xp_lvl(self, xp: int, lvl: int):
        self.xp = xp
        self.lvl += lvl
        await self.save()

    async def inc_quests_ended(self):
        if not self.dungeon:
            self.dungeon = {}
        self.dungeon['quest_ended'] = self.dungeon.get('quest_ended', 0) + 1
        await self.save()

    async def add_background(self, background_id: int):
        if 'backgrounds' not in self.saved:
            self.saved['backgrounds'] = []
        if background_id not in self.saved['backgrounds']:
            self.saved['backgrounds'].append(background_id)
        await self.save()

class Lang(Document):
    userid: Optional[int] = None
    lang: str = "en"

    class Settings:
        name = "lang"
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid"),
            IndexModel([("lang", TEXT)], name="lang")
        ]

    @classmethod
    async def set_user_lang(cls, userid: int, lang: str):
        from bot.modules.localization import available_locales
        if lang not in available_locales:
            lang = 'en'
        
        user_lang = await cls.find_one(cls.userid == userid)
        if user_lang:
            user_lang.lang = lang
            await user_lang.save()
        else:
            user_lang = cls(userid=userid, lang=lang)
            await user_lang.insert()
        return user_lang

class Referral(Document):
    userid: Optional[int] = None
    code: str = ""
    type: str = ""  # 'general' or 'sub'

    class Settings:
        name = "referals"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("code", TEXT)], name="code")
        ]

    @classmethod
    async def get_referal_award(cls, userid: int):
        from bot.const import GAME_SETTINGS as gs
        from bot.modules.logs import log
        from bot.modules.items.item import AddItemToUser
        from bot.models.user import User

        coins = gs['referal']['coins']
        items = gs['referal']['items']

        user = await User.find_one(User.userid == userid)
        if user:
            user.coins += coins
            await user.save()

        log(f"Edit coins: user: {userid} col: {coins}", 1, "take_coins")
        for item in items: 
            await AddItemToUser(userid, item)

    @classmethod
    async def create_referal(cls, userid: int, code: str = ''):
        from bot.modules.data_format import random_code
        existing = await cls.find_one(cls.userid == userid, cls.type == 'general')
        if not existing:
            if not code: 
                while not code:
                    c = random_code(10)
                    if not await cls.find_one(cls.code == c): 
                        code = c

            data = cls(
                code=code,
                userid=userid,
                type='general'
            )
            await data.insert()
            return True, code
        return False, ''

    @classmethod
    async def get_code_owner(cls, code: str):
        return await cls.find_one(cls.code == code, cls.type == 'general')

    @classmethod
    async def get_user_code(cls, userid: int):
        return await cls.find_one(cls.userid == userid, cls.type == 'general')

    @classmethod
    async def get_user_sub(cls, userid: int):
        return await cls.find_one(cls.userid == userid, cls.type == 'sub')

    @classmethod
    async def connect_referal(cls, code: str, userid: int) -> bool:
        from bot.modules.user.friends import insert_friend_connect
        existing_sub = await cls.find_one(cls.userid == userid, cls.type == 'sub')
        if not existing_sub:
            code_creator = await cls.get_code_owner(code)
            if code_creator:
                if code_creator.userid != userid:
                    data = cls(
                        code=code,
                        userid=userid,
                        type='sub'
                    )
                    await data.insert()

                    await insert_friend_connect(userid, code_creator.userid, 'friends')
                    await cls.get_referal_award(userid)
                    return True
        return False

class Friend(Document):
    userid: Optional[int] = None
    friendid: Optional[int] = None
    type: str = "request"
    user_data: Dict[str, Any] = Field(default_factory=dict)
    friend_data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "friends"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("friendid", ASCENDING)], name="friendid")
        ]

class Subscription(Document):
    userid: Optional[int] = None
    sub_start: int = 0
    sub_end: Union[int, str] = 0

    class Settings:
        name = "subscriptions"
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid"),
            IndexModel([("sub_start", ASCENDING)], name="sub_start")
        ]

class Ad(Document):
    userid: Optional[int] = None
    last_ads: int = 0
    limit: Union[int, str] = 7200

    async def set_last_ads(self, timestamp: int):
        self.last_ads = timestamp
        await self.save()

    class Settings:
        name = "ads"
        indexes = [
            IndexModel(
                [("userid", ASCENDING)],
                unique=True,
                partialFilterExpression={"userid": {"$exists": True}},
                name="userid"
            ),
            IndexModel([("last_ads", ASCENDING)], name="last_ads")
        ]

class DinoCollection(Document):
    user_id: Optional[int] = None
    dino_id: str = ""
    added_time: int = 0

    class Settings:
        name = "dino_collection"

class Achievement(Document):
    userid: Optional[int] = None
    achievement_id: str = ""
    unlocked_time: int = 0

    class Settings:
        name = "achievements"
