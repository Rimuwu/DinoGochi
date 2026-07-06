from typing import List, Dict, Any, Union, Optional
from beanie import Document
from pydantic import Field
import time
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT

class Product(Document):
    add_time: int = 0
    type: str = ""  # 'items_coins', 'coins_items', 'items_items', 'auction'
    owner_id: Optional[int] = None
    alt_id: str = ""
    items: List[Dict[str, Any]] = Field(default_factory=list)
    items_id: List[str] = Field(default_factory=list)
    price: Union[int, List[Dict[str, Any]]] = 0
    in_stock: int = 1
    bought: int = 0
    end: Optional[int] = None
    min_add: Optional[int] = None
    users: List[Dict[str, Any]] = Field(default_factory=list)

    class Settings:
        name = "products"
        indexes = [
            IndexModel([("alt_id", TEXT)], unique=True, name="alt_id"),
            IndexModel([("add_time", ASCENDING)], name="add_time"),
            IndexModel([("owner_id", ASCENDING)], name="owner_id")
        ]

    @classmethod
    async def generation_code(cls, owner_id: int) -> str:
        from bot.modules.data_format import random_code
        code = f'{owner_id}_{random_code(8)}'
        if await cls.find_one(cls.alt_id == code):
            code = await cls.generation_code(owner_id)
        return code

    @classmethod
    async def add(cls, owner_id: int, product_type: str, items: list, price, in_stock: int = 1, add_arg: dict | None = None):
        if add_arg is None: add_arg = {}
        assert product_type in ['items_coins', 'coins_items', 'items_items', 'auction'], f'Type ({product_type}) mismatch'

        items_id = []
        if product_type == 'items_items':
            for i in price:
                items_id.append(i['item_id'])
        for i in items:
            items_id.append(i['item_id'])

        alt_id = await cls.generation_code(owner_id)
        product = cls(
            add_time=int(time.time()),
            type=product_type,
            owner_id=owner_id,
            alt_id=alt_id,
            items=items,
            items_id=items_id,
            price=price,
            in_stock=in_stock,
            bought=0
        )

        if product_type == 'auction':
            product.end = add_arg['end'] + int(time.time())
            product.min_add = add_arg['min_add']
            product.users = []

        await product.insert()
        
        from bot.modules.market.market import send_view_product
        try:
            await send_view_product(product.id, owner_id)
        except Exception as e:
            from bot.modules.logs import log
            log(f"send_view_product error: {e}", lvl=3, prefix="market")

        return product.id

    @classmethod
    async def delete_product(cls, baseid=None, alt_id=None):
        

        if baseid:
            product = await cls.get(baseid)
        else:
            product = await cls.find_one(cls.alt_id == alt_id)

        if product:
            from bot.modules.overwriting.DataCalsses import Transaction
            async with Transaction():
                await product.delete()
                from bot.models.market import Preferential
                await Preferential.find(Preferential.product_id == str(product.id)).delete()

            p = product
            ptype = p.type
            remained = p.in_stock - p.bought
            owner = p.owner_id

            from bot.modules.data_format import item_list
            from bot.modules.items.item import AddItemToUser, counts_items
            from bot.models.user import User
            from bot.modules.localization import t
            from bot.exec import bot
            from bot.modules.notifications import user_notification

            if ptype in ['items_coins', 'items_items']:
                col_items = item_list(p.items)
                for item in col_items:
                    col = item['count']
                    abil = item.get('abilities', {})
                    if remained:
                        await AddItemToUser(owner, item['item_id'], remained * col, abil)

            elif ptype == 'coins_items':
                coins = p.price * remained
                if coins:
                    user_obj = await User.find_one(User.userid == owner)
                    if user_obj:
                        await user_obj.add_coins(coins)

            elif ptype == 'auction':
                winner = None
                for user in list(p.users):
                    if user['status'] == 'win': winner = user
                    else:
                        user_obj = await User.find_one(User.userid == user['userid'])
                        if user_obj:
                            await user_obj.add_coins(user['coins'])
                        id_list = [i['item_id'] for i in list(p.items)]
                        c_items = counts_items(id_list, user['lang'])
                        text = t('auction.delete_auction', user['lang'], items=c_items)
                        try: await bot.send_message(user['userid'], text)
                        except: pass

                if winner:
                    col_items = item_list(p.items)
                    for item in col_items:
                        col = item['count']
                        abil = item.get('abilities', {})
                        if remained:
                            await AddItemToUser(winner['userid'], item['item_id'], remained * col, abil)

                    two_percent = (p.price // 100) * 2
                    user_obj = await User.find_one(User.userid == owner)
                    if user_obj:
                        await user_obj.add_coins(winner['coins'] - two_percent)

                    id_list = [i['item_id'] for i in list(p.items)]
                    c_items = counts_items(id_list, winner['lang'])
                    text = t('auction.win', winner['lang'], items=c_items)
                    try: await bot.send_message(winner['userid'], text)
                    except: pass
                else:
                    col_items = item_list(p.items)
                    for item in col_items:
                        col = item['count']
                        abil = item.get('abilities', {})
                        if remained:
                            await AddItemToUser(owner, item['item_id'], remained * col, abil)

            from bot.modules.localization import get_lang
            owner_lang = await get_lang(owner)
            from bot.modules.market.market import preview_product
            preview = preview_product(p.items, p.price, p.type, owner_lang)
            await user_notification(owner, 'product_delete', owner_lang, preview=preview)
            return True
        return False

    @classmethod
    async def buy_product(cls, pro_id: ObjectId, col: int, userid: int, name: str, lang: str = ''):
        from bot.modules.items.item import AddItemToUser, CheckCountItemFromUser, RemoveItemFromUser, transfer_item
        from bot.models.user import User
        from bot.modules.data_format import item_list

        product = await cls.get(pro_id)
        if product:
            p_tp = product.type
            owner = product.owner_id

            if col > product.in_stock - product.bought and product.type != 'auction':
                return False, 'erro_max_col'
            else:
                from bot.modules.overwriting.DataCalsses import Transaction
                async with Transaction():
                    if p_tp == 'items_coins':
                        col_price = col * product.price
                        two_percent = (col_price // 100) * 2

                        user_obj = await User.find_one(User.userid == userid)
                        status = user_obj and await user_obj.remove_coins(col_price)
                        if status:
                            await product.upd_data(p_tp, col, owner, pro_id, name)
                            col_items = item_list(product.items)
                            for item in col_items:
                                itme_col = item['count']
                                item_id = item['item_id']
                                abil = item.get('abilities', {})
                                await user_obj.add_item(item_id, itme_col * col, abil)

                            owner_obj = await User.find_one(User.userid == owner)
                            if owner_obj:
                                await owner_obj.add_coins(col_price - two_percent)
                        else:
                            return False, 'error_no_coins'

                    elif p_tp == 'coins_items':
                        items_status, n = [], 0
                        col_price = col * product.price

                        col_items = item_list(product.items)
                        for item in col_items:
                            item_id = item['item_id']
                            count = item['count']
                            abil = item.get('abilities', {})
                            status = await CheckCountItemFromUser(userid, count * col, item_id, abil)
                            items_status.append(status)
                            n += 1

                        if not all(items_status):
                            return False, 'error_no_items'
                        else:
                            await product.upd_data(p_tp, col, owner, pro_id, name)
                            col_items = item_list(product.items)
                            for item in col_items:
                                itme_col = item['count']
                                item_id = item['item_id']
                                abil = item.get('abilities', {})
                                await transfer_item(userid, owner, item_id, itme_col * col, abil)

                            user_obj = await User.find_one(User.userid == userid)
                            if user_obj:
                                await user_obj.add_coins(col_price)

                    elif p_tp == 'items_items':
                        items_status, n = [], 0
                        col_items = item_list(product.price)
                        for item in col_items:
                            item_id = item['item_id']
                            count = item['count']
                            abil = item.get('abilities', {})
                            status = await CheckCountItemFromUser(userid, count * col, item_id, abil)
                            items_status.append(status)
                            n += 1

                        if not all(items_status):
                            return False, 'error_no_items'
                        else:
                            await product.upd_data(p_tp, col, owner, pro_id, name)
                            col_items = item_list(product.price)
                            for item in col_items:
                                itme_col = item['count']
                                item_id = item['item_id']
                                abil = item.get('abilities', {})
                                await transfer_item(userid, owner, item_id, itme_col * col, abil)

                            col_items = item_list(product.items)
                            for item in col_items:
                                itme_col = item['count']
                                item_id = item['item_id']
                                abil = item.get('abilities', {})
                                user_obj = await User.find_one(User.userid == userid)
                                await user_obj.add_item(item_id, itme_col * col, abil)

                    elif p_tp == 'auction':
                        from bot.models.user import User
                        user_obj = await User.find_one(User.userid == userid)
                        status = user_obj and await user_obj.remove_coins(col)
                        if status:
                            await product.new_participant(pro_id, userid, col, name, lang)
                        else:
                            return False, 'error_no_coins'

                if p_tp != 'auction':
                    return True, 'ok'
                else:
                    return True, 'participant'

        return False, 'error_no_product'

    async def upd_data(self, p_tp: str, col: int, owner: int, pro_id: ObjectId, name: str):
        from bot.models.market import Seller
        from bot.modules.user.user import get_lang
        from bot.modules.notifications import user_notification
        from bot.modules.market.market import preview_product

        earned = 0
        if p_tp not in ['coins_items', 'items_items']:
            earned = col * self.price

        seller = await Seller.find_one(Seller.owner_id == owner)
        if seller:
            seller.earned += earned
            seller.conducted += col
            await seller.save()

        self.bought += col
        await self.save()

        if self.bought >= self.in_stock:
            await Product.delete_product(pro_id)

        owner_lang = await get_lang(owner)
        preview = preview_product(self.items, self.price, self.type, owner_lang)

        if self.type == 'items_items':
            await user_notification(owner, 'items_items_buy', owner_lang,
                                preview=preview, col=col, name=name, alt_id=self.alt_id)
        else:
            await user_notification(owner, 'product_buy', owner_lang,
                                preview=preview, col=col, price=col * self.price, name=name, alt_id=self.alt_id)

    async def new_participant(self, baseid: ObjectId, userid: int, coins: int, name: str, lang: str):
        from bot.models.user import User

        ind = None
        if self.type == 'auction':
            data = {
                'userid': userid,
                'name': name,
                'lang': lang,
                'coins': coins,
                'status': 'member'
            }
            for i in list(self.users):
                if i['userid'] == userid: 
                    user_obj = await User.find_one(User.userid == userid)
                    if user_obj:
                        await user_obj.add_coins(i['coins'])
                    ind = self.users.index(i)
                    break

            if ind is None:
                self.users.append(data)
                self.price = coins
                await self.save()
            else:
                self.price = coins
                self.users[ind] = data
                await self.save()
            return True
        return False

    @classmethod
    async def edit_price(cls, product_alt_id: str, new_price: int, userid: int) -> tuple[bool, str]:
        from bot.models.user import User
        product = await cls.find_one(cls.alt_id == product_alt_id)
        if product:
            res = True
            if product.type == 'coins_items':
                stock = product.in_stock
                price = (product.price * stock) - (new_price * stock)
                user_obj = await User.find_one(User.userid == userid)
                if not user_obj:
                    res = False
                else:
                    if price >= 0:
                        await user_obj.add_coins(price)
                        res = True
                    else:
                        res = await user_obj.remove_coins(-price)

            if res:
                product.price = new_price
                await product.save()
                return True, 'product_info.update_price'
            else: 
                return False, 'product_info.not_coins'
        return False, 'product_info.error'

    @classmethod
    async def add_stock(cls, product_alt_id: str, in_stock: int, userid: int) -> tuple[bool, str]:
        from bot.modules.items.item import CheckCountItemFromUser, RemoveItemFromUser
        product = await cls.find_one(cls.alt_id == product_alt_id)

        if product:
            from bot.modules.overwriting.DataCalsses import Transaction
            if product.type in ['items_coins', 'items_items']:
                items = list(product.items)
                items_status = []

                for item in items:
                    item_id = item['item_id']
                    count = item['count']
                    abil = item.get('abilities', {})
                    status = await CheckCountItemFromUser(userid, in_stock * count, item_id, abil)
                    items_status.append(status)

                if not all(items_status):
                    return False, 'product_info.no_items'
                else:
                    async with Transaction():
                        for item in items:
                            item_id = item['item_id']
                            count = item['count']
                            abil = item.get('abilities', {})
                            await RemoveItemFromUser(userid, item_id, in_stock * count, abil)

                        product.in_stock += in_stock
                        await product.save()
                    return True, 'product_info.stock'

            elif product.type == 'coins_items':
                from bot.models.user import User
                async with Transaction():
                    user_obj = await User.find_one(User.userid == userid)
                    res = user_obj and await user_obj.remove_coins(product.price * in_stock)
                    if res:
                        product.in_stock += in_stock
                        await product.save()
                        return True, 'product_info.stock'
                return False, 'product_info.not_coins'
        return False, 'product_info.error'

    @classmethod
    async def delete_all_for_user(cls, userid: int):
        products_del = await cls.find(cls.owner_id == userid).to_list()
        for i in products_del:
            await cls.delete_product(i.id)

class Seller(Document):
    owner_id: Optional[int] = None
    name: str = ""
    description: str = ""
    earned: int = 0
    conducted: int = 0
    custom_image: str = ""

    class Settings:
        name = "sellers"
        indexes = [
            IndexModel([("name", TEXT)], name="name"),
            IndexModel([("owner_id", ASCENDING)], name="owner_id")
        ]

    @classmethod
    async def create_shop(cls, owner_id: int, name: str, description: str) -> bool:
        existing = await cls.find_one(cls.owner_id == owner_id)
        if not existing:
            existing_name = await cls.find_one(cls.name == name)
            if not existing_name:
                new_shop = cls(
                     owner_id=owner_id,
                     name=name,
                     description=description,
                     earned=0,
                     conducted=0,
                     custom_image=""
                )
                await new_shop.insert()
                return True
        return False

    async def get_ui(self, my_market: bool, lang: str, name: str = ''):
        from bot.modules.localization import get_data, t
        from bot.models.market import Product
        from bot.modules.user.user import user_name, premium
        from bot.modules.data_format import list_to_inline, escape_markdown
        from bot.modules.images import async_open
        from bot.exec import bot

        text, markup, img = '', None, None
        data = get_data('market_ui', lang)
        products_col = await Product.find(Product.owner_id == self.owner_id).count()

        if my_market:
            owner = data['me_owner']
        else: 
            if not name:
                owner = await user_name(self.owner_id)
            else:
                owner = name

        status = ''
        if self.earned <= 1000: status = 'needy'
        elif self.earned <= 10000: status = 'stable'
        else: status = 'rich'

        description = escape_markdown(self.description)

        text += f'{data["had"]} *{self.name}*\n_{description}_\n\n{data["owner"]} {owner}\n' \
                f'{data["earned"]} {self.earned} {data[status]}\n{data["conducted"]} {self.conducted}\n' \
                f'{data["products"]} {products_col}'

        if my_market: text += f'\n\n{data["my_option"]}'

        bt_data = {}
        d_but = data['buttons']
        if not my_market:
            if products_col:
                bt_data[d_but['market_products']] = f"seller all {self.owner_id}"
            else: bt_data[d_but['no_products']] = f" "
        else:
            bt_data.update(
                {
                d_but['edit_text']: f'seller edit_text {self.owner_id}',
                d_but['edit_name']: f'seller edit_name {self.owner_id}',
                d_but['edit_image']: f'seller edit_image {self.owner_id}',
                }
            )

            if products_col >= 2:
                bt_data[d_but['cancel_all']] = f'seller cancel_all {self.owner_id}'

        markup = list_to_inline([bt_data])
        img = await async_open(f'images/remain/market/{status}.png', True)

        if self.custom_image and await premium(self.owner_id):
            try:
                if await bot.get_file(self.custom_image):
                    img = self.custom_image
            except Exception: pass

        return text, markup, img

class Preferential(Document):
    userid: Optional[int] = None
    end: int = 0
    product_id: str = ""

    class Settings:
        name = "preferential"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("end", ASCENDING)], name="end"),
            IndexModel([("product_id", ASCENDING)], unique=True, name="product_id")
        ]

class Puhs(Document):
    owner_id: Optional[int] = None
    channel_id: Optional[int] = None
    lang: str = "en"

    class Settings:
        name = "puhs"
