from bson import ObjectId
from bot.config import conf
from bot.models.market import Preferential, Product
from bot.models.user import User
from bot.modules.market.market import delete_product
from bot.modules.task_queue import task_handler

@task_handler("market_delete")
async def market_delete_task(data: dict):
    product_id = data.get("product_id")
    if product_id:
        prod = await Product.find_one(Product.id == ObjectId(product_id))
        if prod:
            await delete_product(prod.id)

@task_handler("auction_end")
async def auction_end_task(data: dict):
    product_id = data.get("product_id")
    if product_id:
        prod = await Product.find_one(Product.id == ObjectId(product_id))
        if prod:
            users_data = list(prod.users)
            max_coins = 0
            winner = None
            for user in users_data:
                status = await User.find_one(User.userid == user.userid)
                if status and user.coins >= max_coins:
                    max_coins = user.coins
                    winner = prod.users.index(user)

            if winner is not None:
                prod.users[winner].status = 'win'
                await prod.save()

            await delete_product(prod.id)

@task_handler("preferential_delete")
async def preferential_delete_task(data: dict):
    preferential_id = data.get("preferential_id")
    if preferential_id:
        pref = await Preferential.find_one(Preferential.id == ObjectId(preferential_id))
        if pref:
            await pref.delete()

@task_handler("update_channel_message", rate_limit=5)
async def update_channel_message_task(data: dict):
    from bot.models.market import Product, Puhs, Seller
    from bot.modules.market.market import delete_product, product_ui
    from bot.modules.localization import t
    from bot.modules.data_format import list_to_inline
    from bot.exec import bot
    from bson import ObjectId

    product_id_str = data.get("product_id")
    owner_id = data.get("owner_id")
    sold_out = data.get("sold_out", False)

    if not product_id_str:
        return

    product_id = ObjectId(product_id_str)
    product = await Product.get(product_id)
    if not product:
        return

    res = await Puhs.find_one(Puhs.owner_id == owner_id)
    if res and product.message_id:
        channel = res.channel_id
        lang = res.lang

        seller = await Seller.find_one(Seller.owner_id == owner_id)
        behavior = getattr(seller, "stock_out_behavior", "zero") if seller else "zero"

        if sold_out and behavior == "delete":
            try:
                await bot.delete_message(channel, product.message_id)
            except Exception as e:
                from bot.modules.logs import log
                log(f"Failed to delete channel message: {e}", lvl=3, prefix="market")
        else:
            text, markup = await product_ui(lang, product.id, False, html=True)

            import re
            text = re.sub(r'!\[(.*?)\]\(tg://emoji\?id=(\d+)\)', r'<tg-emoji emoji-id="\2">\1</tg-emoji>', text)
            text = re.sub(r'\*([^*\n]+)\*', r'<b>\1</b>', text)
            text = re.sub(r'_([_\n]+)_', r'<i>\1</i>', text)

            if sold_out:
                markup = list_to_inline([])
            else:
                buttons = [
                    {
                        t('product_ui.buttons.view', lang): f"product_info info {product.alt_id}"
                    }
                ]
                markup = list_to_inline(buttons)

            try:
                await bot.edit_message_caption(chat_id=channel, message_id=product.message_id, caption=text, reply_markup=markup)
            except Exception:
                try:
                    await bot.edit_message_text(chat_id=channel, message_id=product.message_id, text=text, reply_markup=markup)
                except Exception as e:
                    from bot.modules.logs import log
                    log(f"Failed to update channel message: {e}", lvl=3, prefix="market")

    if sold_out:
        await delete_product(product.id)