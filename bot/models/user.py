from typing import Optional, List, Dict, Any, Union
from beanie import Document
from pydantic import Field
from bson.objectid import ObjectId

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
        'confidentiality': False
    })
    notifications: Dict[str, Any] = Field(default_factory=dict)
    coins: int = 100
    super_coins: int = 0
    lvl: int = 0
    xp: int = 0
    add_slots: int = 0
    saved: Dict[str, Any] = Field(default_factory=lambda: {
        'backgrounds': []
    })

    class Settings:
        name = "users"
        keep_nulls = False

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

class Lang(Document):
    userid: Optional[int] = None
    lang: str = "en"

    class Settings:
        name = "lang"

class Referral(Document):
    userid: Optional[int] = None
    code: str = ""
    type: str = ""  # 'general' or 'sub'

    class Settings:
        name = "referals"

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

        log(f"Edit coins: user: {userid} col: {coins}", 0, "take_coins")
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

    class Settings:
        name = "friends"

class Subscription(Document):
    userid: Optional[int] = None
    sub_start: int = 0
    sub_end: Union[int, str] = 0

    class Settings:
        name = "subscriptions"

class Ad(Document):
    userid: Optional[int] = None
    last_ads: int = 0

    class Settings:
        name = "ads"

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
