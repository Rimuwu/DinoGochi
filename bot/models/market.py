from typing import List, Dict, Any, Union, Optional
from beanie import Document, Link as BeanieLink, PydanticObjectId
from pydantic import BaseModel, Field
import time
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User
from bot.modules.overwriting.DataCalsses import Transaction

class AuctionBid(BaseModel):
    userid: int
    name: str = ""
    lang: str = ""
    coins: int = 0
    status: str = "member"

class Product(PrivateModelMixin, Document):
    add_time: int = 0
    type: str = ""  # 'items_coins', 'coins_items', 'items_items', 'auction'
    owner_id: int = 0
    alt_id: str = ""
    items: List[Dict[str, Any]] = Field(default_factory=list)
    items_id: List[str] = Field(default_factory=list)
    price: Union[int, List[Dict[str, Any]]] = 0
    in_stock: int = 1
    bought: int = 0
    end: Optional[int] = None
    min_add: Optional[int] = None
    users: List[AuctionBid] = Field(default_factory=list)
    message_id: Optional[int] = None

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
        await cls.create_task(product.id, product.add_time, product.end if product_type == 'auction' else None)

        try:
            from bot.redismanager import redis_del
            await redis_del('market:active_item_ids')
        except Exception:
            pass

        from bot.modules.market.market import send_view_product
        try:
            await send_view_product(product.id, owner_id)
        except Exception as e:
            from bot.modules.logs import log
            log(f"send_view_product error: {e}", lvl=3, prefix="market")
            err_msg = str(e).lower()
            if "need administrator rights" in err_msg or "member" in err_msg or "chat not found" in err_msg or "not member" in err_msg:
                try:
                    from bot.modules.localization import get_lang, t
                    from bot.exec import bot
                    lang = await get_lang(owner_id)
                    text = t("push.no_admin_rights", lang)
                    await bot.send_message(owner_id, text)
                except Exception as send_err:
                    log(f"Failed to send missing rights warning to user {owner_id}: {send_err}", lvl=3, prefix="market")

        return product.id

    @classmethod
    async def delete_product(cls, baseid=None, alt_id=None):
        if baseid:
            product = await cls.get(baseid)
        else:
            product = await cls.find_one(cls.alt_id == alt_id)

        if product:
            # Calculate remained BEFORE any mutation of product.in_stock
            remained = product.in_stock - product.bought

            # Update the channel message before deleting the product from DB
            if product.message_id:
                from bot.models.market import Puhs
                from bot.exec import bot
                res = await Puhs.find_one(Puhs.owner_id == product.owner_id)
                if res:
                    channel = res.channel_id
                    lang = res.lang
                    
                    from bot.models.market import Seller
                    seller = await Seller.find_one(Seller.owner_id == product.owner_id)
                    behavior = getattr(seller, "stock_out_behavior", "zero") if seller else "zero"

                    if behavior == "delete":
                        try:
                            await bot.delete_message(channel, product.message_id)
                        except Exception:
                            pass
                    else:
                        product.in_stock = product.bought
                        await product.save()
                        
                        from bot.modules.market.market import product_ui
                        from bot.modules.data_format import list_to_inline
                        from bot.exec import bot
                        import re
                        
                        text, _ = await product_ui(lang, product.id, False, html=True)
                        text = re.sub(r'!\[(.*?)\]\(tg://emoji\?id=(\d+)\)', r'<tg-emoji emoji-id="\2">\1</tg-emoji>', text)
                        text = re.sub(r'\*([^*\n]+)\*', r'<b>\1</b>', text)
                        text = re.sub(r'_([_\n]+)_', r'<i>\1</i>', text)
                        
                        markup = list_to_inline([])
                        
                        try:
                            await bot.edit_message_caption(chat_id=channel, message_id=product.message_id, caption=text, reply_markup=markup)
                        except Exception:
                            try:
                                await bot.edit_message_text(chat_id=channel, message_id=product.message_id, text=text, reply_markup=markup)
                            except Exception:
                                pass

            async with Transaction():
                await product.delete()
                await cls.cancel_task(product.id)
                from bot.models.market import Preferential
                pref = await Preferential.find_one(Preferential.product.id == product.id)
                if pref:
                    await pref.delete()
                    await Preferential.cancel_task(pref.id)

            try:
                from bot.redismanager import redis_del
                await redis_del('market:active_item_ids')
            except Exception:
                pass

            p = product
            ptype = p.type
            owner = p.owner_id or None

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
                    if remained and owner:
                        await AddItemToUser(owner, item['item_id'], remained * col, abil)

            elif ptype == 'coins_items':
                coins = p.price * remained
                if coins and owner:
                    owner_user_obj = await User.find_one(User.userid == owner)
                    if owner_user_obj:
                        await owner_user_obj.add_coins(coins)

            elif ptype == 'auction':
                winner = None
                for user in list(p.users):
                    if user.status == 'win': 
                        winner = user
                    else:
                        user_obj = await User.find_one(User.userid == user.userid)
                        if user_obj:
                            await user_obj.add_coins(user.coins)
                        id_list = [i['item_id'] for i in list(p.items)]
                        c_items = counts_items(id_list, user.lang)
                        text = t('auction.delete_auction', user.lang, items=c_items)
                        try: 
                            await bot.send_message(user.userid, text)
                        except: 
                            pass

                if winner:
                    col_items = item_list(p.items)
                    total_qty = sum(item.get('count', 1) for item in col_items) * remained
                    for item in col_items:
                        col = item['count']
                        abil = item.get('abilities', {})
                        if remained:
                            await AddItemToUser(winner.userid, item['item_id'], remained * col, abil)

                            # Log sale to Redis
                            try:
                                from bot.redismanager import get_redis
                                import json
                                redis = get_redis()
                                sold_qty = remained * col
                                item_price = (winner.coins * (sold_qty / total_qty)) if total_qty > 0 else 0.0
                                await redis.rpush("global_market_sales_today", json.dumps({
                                    "item_id": item['item_id'],
                                    "count": sold_qty,
                                    "price": item_price
                                }))
                            except Exception as e:
                                from bot.modules.logs import log
                                log(f"Failed to log auction sale to redis: {e}", lvl=3)

                    two_percent = (p.price // 100) * 2
                    if owner:
                        owner_user_obj = await User.find_one(User.userid == owner)
                        if owner_user_obj:
                            await owner_user_obj.add_coins(winner.coins - two_percent)

                    id_list = [i['item_id'] for i in list(p.items)]
                    c_items = counts_items(id_list, winner.lang)
                    text = t('auction.win', winner.lang, items=c_items)
                    try: 
                        await bot.send_message(winner.userid, text)
                    except: 
                        pass
                else:
                    col_items = item_list(p.items)
                    for item in col_items:
                        col = item['count']
                        abil = item.get('abilities', {})
                        if remained and owner:
                            await AddItemToUser(owner, item['item_id'], remained * col, abil)

            if owner:
                from bot.modules.localization import get_lang
                owner_lang = await get_lang(owner)
                from bot.modules.market.market import preview_product
                preview = preview_product(p.items, p.price, p.type, owner_lang, html=True)
                await user_notification(owner, 'product_delete', owner_lang, preview=preview)
            return True
        return False

    @classmethod
    async def create_task(cls, product_id: ObjectId, add_time: int, end_time: Optional[int] = None):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task(
            "market_delete", {"product_id": str(product_id)}, 
            run_at=add_time + 86400 * 31, 
            resource_id=f"market_del:{product_id}"
        )
        if end_time is not None:
            await enqueue_task(
                "auction_end", {"product_id": str(product_id)}, 
                run_at=end_time, 
                resource_id=f"auction_end:{product_id}"
            )

    @classmethod
    async def cancel_task(cls, product_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"market_del:{product_id}")
        await cancel_task_by_resource(f"auction_end:{product_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        import time
        current_time = int(time.time())
        products = await cls.find().to_list()
        for prod in products:
            res_id = f"market_del:{prod.id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, prod.add_time + 86400 * 31)
                from bot.modules.task_queue import enqueue_task
                await enqueue_task("market_delete", {"product_id": str(prod.id)}, run_at=run_at, resource_id=res_id)
                
            if prod.type == 'auction' and prod.end:
                res_auc_id = f"auction_end:{prod.id}"
                if not await is_task_scheduled(res_auc_id):
                    run_at = max(current_time, prod.end)
                    from bot.modules.task_queue import enqueue_task
                    await enqueue_task("auction_end", {"product_id": str(prod.id)}, run_at=run_at, resource_id=res_auc_id)

    @classmethod
    async def buy_product(cls, pro_id: ObjectId, col: int, userid: int, name: str, lang: str = ''):
        from bot.modules.items.item import AddItemToUser, CheckCountItemFromUser, RemoveItemFromUser, transfer_item
        from bot.models.user import User
        from bot.modules.data_format import item_list

        product = await cls.get(pro_id)
        if product:
            p_tp = product.type
            owner = product.owner_id or None
            owner_user = None
            if owner:
                owner_user = await User.find_one(User.userid == owner)

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
                            total_qty = sum(item.get('count', 1) for item in col_items) * col
                            for item in col_items:
                                itme_col = item['count']
                                item_id = item['item_id']
                                abil = item.get('abilities', {})
                                await user_obj.add_item(item_id, itme_col * col, abil)

                                # Log sale to Redis
                                try:
                                    from bot.redismanager import get_redis
                                    import json
                                    redis = get_redis()
                                    sold_qty = itme_col * col
                                    item_price = (col_price * (sold_qty / total_qty)) if total_qty > 0 else 0.0
                                    await redis.rpush("global_market_sales_today", json.dumps({
                                        "item_id": item_id,
                                        "count": sold_qty,
                                        "price": item_price
                                    }))
                                except Exception as e:
                                    from bot.modules.logs import log
                                    log(f"Failed to log market sale to redis: {e}", lvl=3)

                            if owner_user:
                                await owner_user.add_coins(col_price - two_percent)
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
                            total_qty = sum(item.get('count', 1) for item in col_items) * col
                            for item in col_items:
                                itme_col = item['count']
                                item_id = item['item_id']
                                abil = item.get('abilities', {})
                                await transfer_item(userid, owner, item_id, itme_col * col, abil)

                                # Log sale to Redis
                                try:
                                    from bot.redismanager import get_redis
                                    import json
                                    redis = get_redis()
                                    sold_qty = itme_col * col
                                    item_price = (col_price * (sold_qty / total_qty)) if total_qty > 0 else 0.0
                                    await redis.rpush("global_market_sales_today", json.dumps({
                                        "item_id": item_id,
                                        "count": sold_qty,
                                        "price": item_price
                                    }))
                                except Exception as e:
                                    from bot.modules.logs import log
                                    log(f"Failed to log market sale to redis: {e}", lvl=3)

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

        seller = await Seller.find_one(Seller.owner_id == self.owner_id)
        if seller:
            seller.earned += earned
            seller.conducted += col
            await seller.save()

        self.bought += col
        await self.save()

        from bot.modules.user.achievements import check_achievements
        if self.owner_id:
            # Update market stats counters
            from bot.models.user import User
            seller_user = await User.find_one(User.userid == self.owner_id)
            if seller_user:
                if 'market_sell_count' not in seller_user.settings:
                    seller_user.settings['market_sell_count'] = 0
                if 'market_sell_total' not in seller_user.settings:
                    seller_user.settings['market_sell_total'] = 0
                seller_user.settings['market_sell_count'] += col
                seller_user.settings['market_sell_total'] += earned
                await seller_user.save()
            await check_achievements(self.owner_id, "sell_item")
        if owner:
            await check_achievements(owner, "buy_item")


        from bot.modules.task_queue import enqueue_task
        await enqueue_task("update_channel_message", {
            "product_id": str(self.id),
            "owner_id": self.owner_id,
            "sold_out": self.bought >= self.in_stock
        }, run_at=time.time() + 1.0)

        if owner:
            owner_lang = await get_lang(owner)
            preview = preview_product(self.items, self.price, self.type, owner_lang, html=True)

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
            data = AuctionBid(
                userid=userid,
                name=name,
                lang=lang,
                coins=coins,
                status='member'
            )
            for i in list(self.users):
                if i.userid == userid: 
                    user_obj = await User.find_one(User.userid == userid)
                    if user_obj:
                        await user_obj.add_coins(i.coins)
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

            from bot.modules.task_queue import enqueue_task
            import time
            await enqueue_task("update_channel_message", {
                "product_id": str(self.id),
                "owner_id": self.owner_id,
                "sold_out": self.bought >= self.in_stock
            }, run_at=time.time() + 1.0)

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
                
                from bot.modules.task_queue import enqueue_task
                await enqueue_task("update_channel_message", {
                    "product_id": str(product.id),
                    "owner_id": product.owner_id,
                    "sold_out": product.bought >= product.in_stock
                }, run_at=time.time() + 1.0)
                
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

                    from bot.modules.task_queue import enqueue_task
                    await enqueue_task("update_channel_message", {
                        "product_id": str(product.id),
                        "owner_id": product.owner_id,
                        "sold_out": product.bought >= product.in_stock
                    }, run_at=time.time() + 1.0)

                    return True, 'product_info.stock'

            elif product.type == 'coins_items':
                from bot.models.user import User
                async with Transaction():
                    user_obj = await User.find_one(User.userid == userid)
                    res = user_obj and await user_obj.remove_coins(product.price * in_stock)
                    if res:
                        product.in_stock += in_stock
                        await product.save()

                        from bot.modules.task_queue import enqueue_task
                        await enqueue_task("update_channel_message", {
                            "product_id": str(product.id),
                            "owner_id": product.owner_id,
                            "sold_out": product.bought >= product.in_stock
                        }, run_at=time.time() + 1.0)

                        return True, 'product_info.stock'
                return False, 'product_info.not_coins'
        return False, 'product_info.error'

    @classmethod
    async def delete_all_for_user(cls, userid: int):
        products_del = await cls.find(cls.owner_id == userid).to_list()
        for i in products_del:
            await cls.delete_product(i.id)


class Seller(PrivateModelMixin, Document):
    owner_id: int = 0
    name: str = ""
    description: str = ""
    earned: int = 0
    conducted: int = 0
    custom_image: str = ""
    stock_out_behavior: str = Field(default="zero")

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
                from bot.modules.user.achievements import check_achievements
                await check_achievements(owner_id, "create_market_shop")
                return True
        return False

    async def get_ui(self, my_market: bool, lang: str, name: str = ''):
        from bot.modules.localization import get_data, t
        from bot.models.market import Product
        from bot.modules.user.premium import premium
        from bot.modules.data_format import list_to_inline, escape_markdown
        from bot.modules.images import async_open
        from bot.exec import bot

        text, markup, img = '', None, None
        data = get_data('market_ui', lang)
        products_col = await Product.find(Product.owner_id == self.owner_id).count()
        owner_id = self.owner_id

        if my_market:
            owner = data['me_owner']
        else: 
            if not name:
                owner = await User.get_user_name(owner_id)
            else:
                owner = name

        status = ''
        if self.earned <= 1000: 
            status = 'needy'
        elif self.earned <= 10000: 
            status = 'stable'
        else: 
            status = 'rich'

        description = escape_markdown(self.description)

        text += f'{data["had"]} <b>{self.name}</b>\n<i>{description}</i>\n\n{data["owner"]} {owner}\n' \
                f'{data["earned"]} {self.earned} {data[status]}\n{data["conducted"]} {self.conducted}\n' \
                f'{data["products"]} {products_col}'

        if my_market: 
            text += f'\n\n{data["my_option"]}'

        bt_data = {}
        d_but = data['buttons']
        if not my_market:
            if products_col:
                bt_data[d_but['market_products']] = f"seller all {owner_id}"
            else: 
                bt_data[d_but['no_products']] = f" "
            markup = list_to_inline([bt_data])
        else:
            bt_data.update(
                {
                d_but['edit_text']: f'seller edit_text {owner_id}',
                d_but['edit_name']: f'seller edit_name {owner_id}',
                d_but['edit_image']: f'seller edit_image {owner_id}',
                }
            )

            row2 = {
                d_but.get('publishing_channel', '📢 Канал публикации'): f'seller push_channel {owner_id}'
            }
            if products_col >= 2:
                row2[d_but['cancel_all']] = f'seller cancel_all {owner_id}'

            markup = list_to_inline([bt_data, row2])
        img = await async_open(f'images/remain/market/{status}.png', True)

        if self.custom_image and owner_id and await premium(owner_id):
            try:
                if await bot.get_file(self.custom_image):
                    img = self.custom_image
            except Exception: 
                pass

        return text, markup, img

    async def update_earned(self, earned: int, conducted: int) -> None:
        self.earned += earned
        self.conducted += conducted
        await self.save()

    async def update_info(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        await self.save()

    async def set_custom_image(self, custom_image: str) -> None:
        self.custom_image = custom_image
        await self.save()


class Preferential(PrivateModelMixin, Document):
    userid: int = 0
    end: int = 0
    product: Optional[BeanieLink[Product]] = None

    class Settings:
        name = "preferential"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("end", ASCENDING)], name="end"),
            IndexModel([("product", ASCENDING)], unique=True, sparse=True, name="product")
        ]

    async def set_end(self, end: int) -> None:
        self.end = end
        await self.save()
        await self.create_task(self.id, end)

    @classmethod
    async def create_task(cls, preferential_id: ObjectId, end_time: int):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task("preferential_delete", {"preferential_id": str(preferential_id)}, run_at=end_time, resource_id=f"pref_del:{preferential_id}")

    @classmethod
    async def cancel_task(cls, preferential_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"pref_del:{preferential_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        import time
        current_time = int(time.time())
        preferentials = await cls.find().to_list()
        for pref in preferentials:
            res_id = f"pref_del:{pref.id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, pref.end)
                await cls.create_task(pref.id, run_at)


class Puhs(PrivateModelMixin, Document):
    owner_id: int = 0
    channel_id: Optional[int] = None
    lang: str = "en"

    class Settings:
        name = "puhs"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], name="owner_id")
        ]

    async def set_channel_id(self, channel_id: int) -> None:
        self.channel_id = channel_id
        await self.save()

    async def set_lang(self, lang: str) -> None:
        self.lang = lang
        await self.save()
