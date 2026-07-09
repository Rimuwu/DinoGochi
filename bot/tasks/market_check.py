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