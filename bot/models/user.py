from typing import Tuple, TYPE_CHECKING
from typing import Optional, List, Dict, Any, Union
from bot.models.enums import ReferralType, FriendType
from beanie import Document
from pydantic import Field
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from bot.models.base_private import PrivateModelMixin

if TYPE_CHECKING:
    from bot.models.dinosaur import Dino

class User(PrivateModelMixin, Document):
    userid: Optional[int] = None
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
        'inv_sort': 'name_asc',
        'rare_emoji': True,
        'only_emoji': False
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

    @property
    def _id(self) -> ObjectId:
        return self.id

    class Settings:
        name = "users"
        keep_nulls = False
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid"),
            IndexModel([("coins", DESCENDING)], name="coins_desc"),
            IndexModel([("super_coins", DESCENDING)], name="super_coins_desc"),
            IndexModel([("lvl", DESCENDING), ("xp", DESCENDING)], name="lvl_xp_desc")
        ]

    async def create(self, userid: int) -> "User":
        db_user = await User.find_one(User.userid == userid)
        if db_user:
            self.__dict__.update(db_user.__dict__)
        else:
            self.userid = userid
        return self

    async def get_dinos(self, all_dinos: bool = True) -> list['Dino']:
        from bot.models.dinosaur import DinoOwners
        dino_list = []
        if all_dinos:
            res = await DinoOwners.find(DinoOwners.owner_id == self.userid).to_list()
        else:
            res = await DinoOwners.find(DinoOwners.owner_id == self.userid, 
                                        DinoOwners.type == 'owner').to_list()
        for conn in res:
            try:
                if conn.dino:
                    d = await conn.dino.fetch()
                    if d:
                        dino_list.append(d)
            except Exception:
                pass
        return dino_list

    async def get_dinos_and_owners(self) -> list[dict[str, Any]]:
        from bot.models.dinosaur import DinoOwners, Dino
        from bson import ObjectId
        data = []
        res = await DinoOwners.find(DinoOwners.owner_id == self.userid).to_list()
        for dino_obj in res:
            try:
                if dino_obj.dino:
                    dd = await dino_obj.dino.fetch()
                    if dd:
                        data.append({'dino': dd, 'owner_type': dino_obj.type})
            except Exception:
                pass
        return data

    @property
    async def get_col_dinos(self) -> int:
        from bot.models.dinosaur import DinoOwners
        return await DinoOwners.find(DinoOwners.owner_id == self.userid).count()

    @property
    async def get_eggs(self) -> list:
        from bot.models.dinosaur import Egg
        return await Egg.find(Egg.owner_id == self.userid, Egg.stage == 'incubation').to_list()

    async def get_inventory(self, exclude_ids: Optional[list[int | str]] = None
    ) -> Tuple[list[dict[str, Any]], int]:
        from bot.models.items import Item

        if not exclude_ids:
            exclude_ids = []

        if isinstance(self, int):
            user = await User.find_one(User.userid == self)
            if not user:
                return [], 0
            user_id = user.id
            userid_int = self
        else:
            user = self
            user_id = self.id
            userid_int = self.userid

        owners_list = [userid_int, str(userid_int), user_id, str(user_id)]
        inv = await Item.find({"owner": {"$in": owners_list}}).to_list()
        filtered_inv = []
        count = 0
        for item in inv:
            if item.items_data.get('item_id') not in exclude_ids:
                filtered_inv.append({
                    '_id': item.id,
                    'count': item.count,
                    'items_data': item.items_data
                })
                count += item.count
        return filtered_inv, count

    @classmethod
    async def have_account(cls, userid: int) -> bool:
        return await cls.find_one(cls.userid == userid) is not None

    async def get_inventory_from_i(self, items_l: list[dict] | None = None, limit = None, one_count = False) -> list:
        from bot.models.items import Item
        from bot.modules.items.item import get_item_dict
        from bot.modules.data_format import item_list

        if items_l is None:
            items_l = []

        if isinstance(self, int):
            userid_int = self
        else:
            userid_int = self.userid

        if one_count:
            id_list = []

        find_i = []
        for item in items_l:
            item_id: str = item['item_id']
            abilities: dict = item.get('abilities', {})

            if abilities:
                fi = await Item.find({
                    "owner": userid_int,
                    "items_data.item_id": item_id,
                    "items_data.abilities": abilities
                }).limit(limit).to_list()
            else:
                fi = await Item.find({
                    "owner": userid_int,
                    "items_data.item_id": item_id
                }).limit(limit).to_list()

            pre_l = [{'item': i.items_data, 'count': i.count} for i in fi]
            if one_count:
                for i in pre_l:
                    if i['item']['item_id'] not in id_list:
                        id_list.append(i['item']['item_id'])
                        item_dict = get_item_dict(i['item']['item_id'])
                        total_count = sum(j['count'] for j in pre_l if j['item']['item_id'] == i['item']['item_id'])
                        find_i.append({
                            "item": item_dict,
                            "count": total_count
                        })
            else:
                find_i += pre_l

        return item_list(find_i)

    async def get_user_name(self_or_userid: Union["User", int, float]) -> str:
        if isinstance(self_or_userid, (int, float, str)):
            return await User.get_user_name_by_id(int(self_or_userid))

        self = self_or_userid
        if self.name and self.name != '' and self.name != 'noname':
            return self.name
        else:
            from bot.exec import bot
            try:
                chat_user = await bot.get_chat_member(self.userid, self.userid)
                if chat_user:
                    name = chat_user.user.first_name
                    await self.set_name(name)
                    return name
            except Exception:
                pass
        return 'NoName_NoUser'

    @classmethod
    async def get_user_name_by_id(cls, userid: int) -> str:
        user = await cls.find_one(cls.userid == int(userid))
        if user:
            return await user.get_user_name()
        return 'NoName_NoUser'

    async def max_dino_col(self) -> dict:
        from bot.const import GAME_SETTINGS as GS
        col = {
            'standart': {
                'now': 0, 'limit': 0
            },
            'additional': {
                'now': 0, 'limit': 1
            }
        }

        dino_lim_cfg = GS.get('dino_limit', {"premium_bonus": 1, "lvl_step": 20, "lvl_cap_step": 100})
        is_premium = await self.premium
        if is_premium:
            col['standart']['limit'] += dino_lim_cfg.get('premium_bonus', 1)
        col['standart']['limit'] += ((self.lvl // dino_lim_cfg.get('lvl_step', 20) + 1) - self.lvl // dino_lim_cfg.get('lvl_cap_step', 100))
        col['standart']['limit'] += self.add_slots

        from bot.models.dinosaur import DinoOwners, Egg
        dinos = await DinoOwners.find(DinoOwners.owner_id == self.userid).to_list()
        for dino in dinos:
            if dino.type == 'owner':
                col['standart']['now'] += 1
            else:
                col['additional']['now'] += 1

        eggs = await Egg.find(Egg.owner_id == self.userid, Egg.stage == 'incubation').to_list()
        for _ in eggs:
            col['standart']['now'] += 1

        return col

    async def get_last_dino(self) -> Optional["Dino"]:
        from bot.models.dinosaur import Dino, DinoOwners
        from bson import ObjectId

        last_dino_id = self.settings.get('last_dino')
        if last_dino_id:
            try:
                dino_data = await Dino.find_one(Dino.id == ObjectId(last_dino_id))
            except Exception:
                dino_data = None
            if not dino_data:
                dino_data = await Dino.find_one(Dino.alt_id == str(last_dino_id))
            if dino_data:
                owner_conn = await DinoOwners.find_one(DinoOwners.dino.id == dino_data.id, DinoOwners.owner_id == self.userid)
                if owner_conn:
                    return dino_data

        dino_list = await self.get_dinos()
        if dino_list:
            first_dino = dino_list[0]
            self.settings['last_dino'] = first_dino.id
            await self.save()
            return first_dino
        else:
            self.settings['last_dino'] = None
            await self.save()
            return None

    @classmethod
    async def insert_user(cls, userid: int, lang: str, name: str = '', avatar: str = '') -> "User":
        from bot.modules.logs import log
        from bot.modules.data_format import escape_markdown
        from bot.modules.user.advert import create_ads_data
        from bot.models.user import Lang

        user = await cls.find_one(cls.userid == userid)
        if not user:
            log(prefix='InsertUser', message=f'User: {userid}', lvl=0)
            user = cls(userid=userid)
            if name != '':
                user.name = escape_markdown(name)
                if user.name == '':
                    user.name = 'noname'
            if avatar != '':
                user.avatar = avatar
            await user.insert()
            await Lang.set_user_lang(userid, lang)
            await create_ads_data(userid, 1800)

            # Grant starter items from GAME_SETTINGS
            from bot.const import GAME_SETTINGS
            from bot.models.items import Item
            starter = GAME_SETTINGS.get('starter_items', [])
            for s_item in starter:
                item_id = s_item.get('item_id')
                count = s_item.get('count', 1)
                abilities = s_item.get('abilities', {})
                if item_id:
                    await Item.add(userid, item_id, count, abilities)
        return user

    async def get_dead_dinos(self) -> list:
        from bot.models.dinosaur import DeadDino
        return await DeadDino.find(DeadDino.owner_id == self.userid).to_list()

    async def get_items_count(self) -> int:
        from bot.models.items import Item
        return await Item.find(Item.owner.id == self.id).count()

    @property
    async def get_friends(self) -> dict:
        friends_list = await Friend.find(Friend.userid == self.userid).to_list()
        friends = [f.friendid for f in friends_list if f.friendid]
        return {'friends': friends, 'requests': []}

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

    def view(self) -> None:
        print(f'userid: {self.userid}')
        print(f'DATA: {self.__dict__}')

    async def full_delete(self) -> None:
        from bot.models.items import Item, ItemCraft
        from bot.models.market import Product, Seller, Preferential, Puhs
        from bot.models.dinosaur import DeadDino, Egg, DinoOwners, Dino
        from bot.models.tavern import DailyAward, Quest, InsideShop
        from bot.models.other import MessageLog, DeadUser
        from bot.models.group import GroupUser
        from bot.models.user import Referral, Lang, Ad, Subscription, DinoCollection, Friend

        await Item.find(Item.owner.id == self.id).delete()
        await Product.find(Product.owner_id == self.userid).delete()
        await DeadDino.find(DeadDino.owner_id == self.userid).delete()
        await Egg.find(Egg.owner_id == self.userid).delete()
        await Seller.find(Seller.owner_id == self.userid).delete()
        await Puhs.find(Puhs.owner_id == self.userid).delete()
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
        await MessageLog.find(MessageLog.userid == self.userid).delete()
        await ItemCraft.find(ItemCraft.userid == self.userid).delete()

        await GroupUser.find(GroupUser.userid == self.userid).delete()
        await DinoCollection.find(DinoCollection.userid == self.userid).delete()

        dinos_conn = await DinoOwners.find(DinoOwners.owner_id == self.userid).to_list()
        for conn in dinos_conn:
            dino_id = conn.dino.ref.id if hasattr(conn.dino, 'ref') else conn.dino.id
            if conn.type == 'owner':
                alt_conn = await DinoOwners.find(DinoOwners.dino.id == dino_id, DinoOwners.type == 'add_owner').to_list()
                if len(alt_conn) > 1:
                    await DinoOwners.find_one(DinoOwners.dino.id == dino_id).update({"$set": {"type": "owner"}})
                else:
                    try:
                        dino_d = await Dino.find_one(Dino.id == dino_id)
                    except Exception:
                        dino_d = None
                    if dino_d:
                        await dino_d.delete()
            await conn.delete()

        await Friend.find(Friend.userid == self.userid).delete()
        await Friend.find(Friend.friendid == self.userid).delete()

        from bot.modules.managment.tracking import update_all_user_track
        await update_all_user_track(self.userid, 'delete_account')

        await self.delete()



    async def get_avatar(self):
        from bot.modules.user.avatar import get_avatar
        return await get_avatar(self.userid)

    async def add_coins(self, amount: int) -> None:
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

    async def add_super_coins(self, amount: int) -> None:
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

    async def add_item(self, item_id: str, count: int = 1, abilities: dict | None = None) -> bool:
        from bot.models.items import Item
        return await Item.add(self.userid, item_id, count, abilities)

    async def remove_item(self, item_id: str, count: int = 1, abilities: dict | None = None) -> bool:
        from bot.models.items import Item
        return await Item.remove(self.userid, item_id, count, abilities)

    @classmethod
    async def transfer_coins(cls, from_userid: int, to_userid: int, amount: int) -> bool:
        from bot.modules.overwriting.DataCalsses import Transaction
        async with Transaction():
            u_from = await cls.find_one(cls.userid == from_userid)
            u_to = await cls.find_one(cls.userid == to_userid)
            if u_from and u_to and u_from.coins >= amount:
                await u_from.remove_coins(amount)
                await u_to.add_coins(amount)
                return True
        return False

    @classmethod
    async def transfer_super_coins(cls, from_userid: int, to_userid: int, amount: int) -> bool:
        from bot.modules.overwriting.DataCalsses import Transaction
        async with Transaction():
            u_from = await cls.find_one(cls.userid == from_userid)
            u_to = await cls.find_one(cls.userid == to_userid)
            if u_from and u_to and u_from.super_coins >= amount:
                await u_from.update({'$inc': {'super_coins': -amount}})
                await u_to.update({'$inc': {'super_coins': amount}})
                return True
        return False

    async def set_last_markup(self, markup: str) -> None:
        self.last_markup = markup
        await self.save()

    async def set_avatar(self, avatar: str) -> None:
        self.avatar = avatar
        await self.save()

    async def set_name(self, name: str) -> None:
        self.name = name
        await self.save()

    async def set_lang(self, lang: str) -> None:
        await Lang.set_user_lang(self.userid, lang)

    async def add_xp_lvl(self, xp_to_add: int) -> None:
        from bot.modules.user.user import xpboost_percent, max_lvl_xp
        from bot.modules.localization import get_data, get_lang
        from bot.modules.notifications import user_notification
        from bot.modules.localization import t
        from bot.const import GAME_SETTINGS as GS
        import time

        # Calculate boosted xp
        boosted_xp = int(xp_to_add * await xpboost_percent(self.userid))
        
        # Calculate level ups
        lvl_gain = 0
        current_xp = self.xp + boosted_xp

        lang_str = await self.lang

        lvl_messages = get_data('notifications.lvl_up', lang_str)

        while current_xp > 0:
            max_xp = max_lvl_xp(self.lvl + lvl_gain)
            if max_xp <= current_xp:
                current_xp -= max_xp
                lvl_gain += 1

                new_lvl = self.lvl + lvl_gain

                # Level up award processing
                lvl_awards = GS.get('lvl_award', {})
                str_lvl = str(new_lvl)
                rewards_text = None
                if str_lvl in lvl_awards:
                    award = lvl_awards[str_lvl]
                    coins = award.get('coins', 0)
                    super_coins = award.get('super_coins', 0)
                    items = award.get('items', [])

                    if coins > 0:
                        await self.add_coins(coins)
                    if super_coins > 0:
                        await self.add_super_coins(super_coins)

                    reward_lines = []
                    if coins > 0:
                        reward_lines.append(f"+{coins} {{custom_emoji:coins}}")
                    if super_coins > 0:
                        reward_lines.append(f"+{super_coins} {{custom_emoji:super_coin}}")

                    if items:
                        from bot.modules.items.item import AddItemToUser, get_name
                        for it in items:
                            it_id = it.get('item_id') or it.get('itemid')
                            count = it.get('count', 1)
                            abilities = it.get('abilities', {})
                            if it_id:
                                await AddItemToUser(self.userid, it_id, count, abilities)
                                it_name = get_name(it_id, lang_str, abilities)
                                reward_lines.append(f"{it_name} x{count}")

                    if reward_lines:
                        rewards_text = ", ".join(reward_lines)

                add_way = str(new_lvl) if str(new_lvl) in lvl_messages else 'standart'
                kwargs = {
                    'user_name': self.name,
                    'lvl': new_lvl,
                    'add_way': add_way
                }
                if rewards_text:
                    kwargs['rewards'] = rewards_text

                await user_notification(self.userid, 'lvl_up', lang_str, **kwargs)
            else:
                break

        old_lvl = self.lvl
        self.xp = current_xp
        self.lvl += lvl_gain
        await self.save()

        if lvl_gain > 0:
            from bot.modules.user.achievements import check_achievements
            await check_achievements(self.userid, "lvl_up", self.lvl)


        # Referral reward check for invitee: give items and notify inviter
        referal_items = await Referral.check_and_award_invited(self.userid, self.lvl, lang_str)
        if referal_items and lvl_gain > 0:
            # Include referal item info in the level-up notification
            items_text = ', '.join(referal_items)
            await user_notification(self.userid, 'referal_items_reward', lang_str,
                                    items=items_text)

    async def inc_quests_ended(self) -> None:
        if 'quests_ended' not in self.settings:
            self.settings['quests_ended'] = 0
        self.settings['quests_ended'] += 1
        await self.save()
        from bot.modules.user.achievements import check_achievements
        await check_achievements(self.userid, "quest_completed")


    async def add_background(self, background_id: int) -> None:
        if 'backgrounds' not in self.saved:
            self.saved['backgrounds'] = []
        if background_id not in self.saved['backgrounds']:
            self.saved['backgrounds'].append(background_id)
            await self.save()
            from bot.modules.user.achievements import check_achievements
            await check_achievements(self.userid, "background_bought")

    async def update_last_dino(self, dino_id: ObjectId):
        self.settings['last_dino'] = dino_id
        await self.save()

class Lang(PrivateModelMixin, Document):
    userid: int = 0
    lang: str = "en"

    class Settings:
        name = "lang"
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid"),
            IndexModel([("lang", TEXT)], name="lang")
        ]

    @classmethod
    async def set_user_lang(cls, userid: int, lang: str) -> "Lang":
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

        try:
            from bot.redismanager import get_redis
            redis = get_redis()
            await redis.set(f"user:lang:{userid}", lang)
        except Exception:
            pass

        return user_lang

class Referral(PrivateModelMixin, Document):
    userid: int = 0
    code: str = ""
    type: ReferralType = ReferralType.GENERAL

    # For GENERAL type (inviter): which level rewards were already claimed
    lvl_rewards_claimed: List[int] = Field(default_factory=list)
    # For GENERAL type (inviter): mark as old — cannot claim lvl 1 and 5
    is_old: bool = False

    # For SUB type (invitee): which level rewards were already given
    invited_lvl_rewards_given: List[int] = Field(default_factory=list)
    # For SUB type (invitee): cached level of the invitee (for display in "My referrals")
    referral_lvl: int = 0

    def update_referral_lvl(self, lvl: int) -> bool:
        """Update referral level. Returns True if changed."""
        if self.referral_lvl != lvl:
            self.referral_lvl = lvl
            return True
        return False

    def add_invited_lvl_reward_given(self, lvl: int) -> bool:
        """Add invited lvl reward if not already given. Returns True if changed."""
        if lvl not in self.invited_lvl_rewards_given:
            self.invited_lvl_rewards_given.append(lvl)
            return True
        return False

    def add_lvl_reward_claimed(self, lvl: int) -> bool:
        """Add lvl reward claimed by general/inviter. Returns True if changed."""
        if lvl not in self.lvl_rewards_claimed:
            self.lvl_rewards_claimed.append(lvl)
            return True
        return False

    class Settings:
        name = "referals"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("code", TEXT)], name="code")
        ]

    @classmethod
    async def create_referal(cls, userid: int, code: str = '') -> Tuple[bool, str]:
        """Create a GENERAL referral code for the user."""
        from bot.modules.data_format import random_code
        existing = await cls.find_one(cls.userid == userid, cls.type == ReferralType.GENERAL)
        if not existing:
            if not code:
                while not code:
                    c = random_code(10)
                    if not await cls.find_one(cls.code == c):
                        code = c

            data = cls(
                code=code,
                userid=userid,
                type=ReferralType.GENERAL
            )
            await data.insert()
            return True, code
        return False, ''

    @classmethod
    async def get_code_owner(cls, code: str) -> Optional["Referral"]:
        return await cls.find_one(cls.code == code, cls.type == ReferralType.GENERAL)

    @classmethod
    async def get_user_code(cls, userid: int) -> Optional["Referral"]:
        return await cls.find_one(cls.userid == userid, cls.type == ReferralType.GENERAL)

    @classmethod
    async def get_user_sub(cls, userid: int) -> Optional["Referral"]:
        return await cls.find_one(cls.userid == userid, cls.type == ReferralType.SUB)

    @classmethod
    async def connect_referal(cls, code: str, userid: int) -> bool:
        """Connect user to referral code (new users only via deep link).
        No automatic reward — invitee gets lvl 1 items separately on account creation.
        """
        from bot.modules.user.friends import insert_friend_connect
        existing_sub = await cls.find_one(cls.userid == userid, cls.type == ReferralType.SUB)
        if not existing_sub:
            code_creator = await cls.get_code_owner(code)
            if code_creator and code_creator.userid:
                creator_userid = code_creator.userid
                if creator_userid != userid:
                    data = cls(
                        code=code,
                        userid=userid,
                        type=ReferralType.SUB
                    )
                    await data.insert()

                    await insert_friend_connect(userid, creator_userid, 'friends')
                    from bot.modules.user.achievements import check_achievements
                    await check_achievements(creator_userid, "invite")
                    return True
        return False

    @classmethod
    async def award_invited_lvl1_items(cls, userid: int, lang: str) -> None:
        """Give level-1 items to newly registered invited user. Called on account creation."""
        from bot.const import GAME_SETTINGS as gs
        from bot.modules.items.item import AddItemToUser

        lvl_cfg = gs['referal']['levels'].get('1', {})
        items = lvl_cfg.get('invited_items', [])
        for item_id in items:
            await AddItemToUser(userid, item_id)

        # Mark lvl 1 as given in the SUB document
        sub = await cls.find_one(cls.userid == userid, cls.type == ReferralType.SUB)
        if sub and 1 not in sub.invited_lvl_rewards_given:
            sub.invited_lvl_rewards_given.append(1)
            await sub.save()

    @classmethod
    async def check_and_award_invited(cls, userid: int, new_lvl: int, lang: str) -> List[str]:
        """Check if invitee reached a reward level and give them items.
        Returns list of item names given (for inclusion in lvl_up notification).
        """
        from bot.const import GAME_SETTINGS as gs
        from bot.modules.items.item import AddItemToUser, get_name

        REWARD_LEVELS = [5, 15, 30, 50]  # lvl 1 handled on account creation
        given_items_names = []

        sub = await cls.find_one(cls.userid == userid, cls.type == ReferralType.SUB)
        if not sub:
            return []

        changed = False
        for lvl in REWARD_LEVELS:
            if new_lvl >= lvl and lvl not in sub.invited_lvl_rewards_given:
                lvl_cfg = gs['referal']['levels'].get(str(lvl), {})
                items = lvl_cfg.get('invited_items', [])
                for item_id in items:
                    await AddItemToUser(userid, item_id)
                    given_items_names.append(get_name(item_id, lang))
                sub.invited_lvl_rewards_given.append(lvl)
                changed = True

                # Notify inviter that a new level reward is available to claim
                inviter_code = await cls.get_code_owner(sub.code)
                if inviter_code and inviter_code.userid:
                    from bot.modules.notifications import user_notification
                    from bot.modules.localization import get_lang
                    inviter_lang = await get_lang(inviter_code.userid)
                    await user_notification(
                        inviter_code.userid, 'referal_invitee_lvlup', inviter_lang,
                        invitee_lvl=lvl, reward_lvl=lvl
                    )

        # Always keep cached level up to date
        if new_lvl > sub.referral_lvl:
            sub.referral_lvl = new_lvl
            changed = True

        if changed:
            await sub.save()

        return given_items_names

    @classmethod
    async def get_pending_inviter_rewards(cls, inviter_userid: int) -> List[dict]:
        """Return list of unclaimed reward levels for the inviter.
        Each entry: { 'lvl': int, 'coins': int, 'sc': int, 'count': int }
        """
        from bot.const import GAME_SETTINGS as gs
        REWARD_LEVELS = [1, 5, 15, 30, 50]

        inviter_doc = await cls.find_one(cls.userid == inviter_userid, cls.type == ReferralType.GENERAL)
        if not inviter_doc:
            return []

        code = inviter_doc.code
        subs = await cls.find(cls.code == code, cls.type == ReferralType.SUB).to_list()

        pending = []
        for lvl in REWARD_LEVELS:
            if lvl in inviter_doc.lvl_rewards_claimed:
                continue
            lvl_cfg = gs['referal']['levels'].get(str(lvl), {})
            # Count how many subs reached this level
            count = sum(
                1 for sub in subs
                if sub.referral_lvl >= lvl or lvl in sub.invited_lvl_rewards_given
            )
            if count > 0:
                pending.append({
                    'lvl': lvl,
                    'coins': lvl_cfg.get('inviter_coins', 0),
                    'sc': lvl_cfg.get('inviter_sc', 0),
                    'count': count
                })
        return pending

    @classmethod
    async def has_pending_rewards(cls, inviter_userid: int) -> bool:
        """Quick check if inviter has any unclaimed rewards."""
        pending = await cls.get_pending_inviter_rewards(inviter_userid)
        return len(pending) > 0

    @classmethod
    async def claim_inviter_reward(cls, inviter_userid: int, lvl: int) -> bool:
        """Claim a specific level reward for the inviter. Returns True if successful."""
        from bot.const import GAME_SETTINGS as gs
        from bot.models.user import User

        inviter_doc = await cls.find_one(cls.userid == inviter_userid, cls.type == ReferralType.GENERAL)
        if not inviter_doc:
            return False

        if lvl in inviter_doc.lvl_rewards_claimed:
            return False

        # Check that at least one sub reached this level
        code = inviter_doc.code
        subs = await cls.find(cls.code == code, cls.type == ReferralType.SUB).to_list()
        eligible = any(
            sub.referral_lvl >= lvl or lvl in sub.invited_lvl_rewards_given
            for sub in subs
        )
        if not eligible:
            return False

        lvl_cfg = gs['referal']['levels'].get(str(lvl), {})
        coins = lvl_cfg.get('inviter_coins', 0)
        sc = lvl_cfg.get('inviter_sc', 0)

        user = await User.find_one(User.userid == inviter_userid)
        if user:
            if coins > 0:
                await user.add_coins(coins)
            if sc > 0:
                await user.add_super_coins(sc)

        inviter_doc.lvl_rewards_claimed.append(lvl)
        await inviter_doc.save()
        return True


class Friend(PrivateModelMixin, Document):
    userid: int = 0
    friendid: int = 0
    type: FriendType = FriendType.REQUEST
    user_data: Dict[str, Any] = Field(default_factory=dict)
    friend_data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "friends"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("friendid", ASCENDING)], name="friendid")
        ]

class Subscription(PrivateModelMixin, Document):
    userid: int = 0
    sub_start: int = 0
    sub_end: Union[int, str] = 0
    end_notif: bool = False

    class Settings:
        name = "subscriptions"
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid"),
            IndexModel([("sub_start", ASCENDING)], name="sub_start")
        ]

    @classmethod
    async def award_premium(cls, userid: int, end_time: Union[int, str]) -> None:
        import time
        sub = await cls.find_one(cls.userid == userid)
        if sub:
            if isinstance(sub.sub_end, str) and sub.sub_end == "inf":
                pass
            elif isinstance(end_time, str):
                sub.sub_end = end_time
                await sub.save()
            elif isinstance(end_time, int):
                if isinstance(sub.sub_end, (int, float)):
                    sub.sub_end += end_time
                else:
                    sub.sub_end = int(time.time()) + end_time
                await sub.save()
        else:
            if isinstance(end_time, int):
                end_time = int(time.time()) + end_time 
            sub = cls(
                userid=userid,
                sub_start=int(time.time()),
                sub_end=end_time
            )
            await sub.insert()

class Ad(PrivateModelMixin, Document):
    userid: int = 0
    last_ads: int = 0
    limit: Union[int, str] = 7200

    async def set_last_ads(self, timestamp: int) -> None:
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

class DinoCollection(PrivateModelMixin, Document):
    userid: int = 0
    data_id: int = 0
    familie: str = ""
    date: int = 0

    class Settings:
        name = "dino_collection"

    @classmethod
    async def add_to_collection(cls, userid: int, data_id: int) -> Optional[dict]:
        import time
        existing = await cls.find_one(cls.userid == userid, cls.data_id == int(data_id))
        if existing:
            return None

        from bot.const import DINOS
        dino_data = DINOS['elements'][str(data_id)]
        
        entry = cls(
            userid=userid,
            data_id=int(data_id),
            familie=dino_data['name'],
            date=int(time.time())
        )
        await entry.insert()
        return {
            "user_id": userid,
            "data_id": int(data_id),
            "familie": dino_data['name'],
            "date": entry.date
        }

    @classmethod
    async def get_collection(cls, userid: int) -> list["DinoCollection"]:
        return await cls.find(cls.userid == userid).to_list()

    @classmethod
    async def get_count_families(cls, userid: int) -> int:
        collection = await cls.get_collection(userid)
        families = {entry.familie for entry in collection}
        return len(families)

class Achievement(PrivateModelMixin, Document):
    userid: int = 0
    achievement_id: str = ""
    unlocked_time: int = 0
    progress: Any = None
    stack: int = 0
    data: Any = None

    class Settings:
        name = "achievements"

