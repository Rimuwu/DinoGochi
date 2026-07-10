"""
Tests for Market (bot/handlers/market.py) via real handler flows.
"""
import os
import sys
import pytest
import asyncio
from bson.objectid import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.simulator import BotSimulator
from tests.handlers.test_general import register_and_incubate, boost_and_birth
from bot.models.user import User
from bot.models.dinosaur import Dino
from bot.models.items import Item
from bot.models.market import Product, Seller
from bot.modules.localization import get_lang, t


async def setup_user_with_dino(sim: BotSimulator) -> Dino:
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None
    from bot.modules.get_state import get_state
    st = await get_state(sim.user_id, sim.user_id)
    await st.clear()
    return dino


@pytest.mark.asyncio
async def test_market_create_and_my_market(test_dp, test_bot):
    """
    Tests creating a market profile (Seller) and viewing the market profile.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=80001, username="market_creator")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Seller requires user level >= 2
    user = await User.find_one(User.userid == sim.user_id)
    user.lvl = 2
    await user.save()

    # Clear existing seller if any
    await Seller.find(Seller.owner_id == sim.user_id).delete()

    sim.clear_sent_requests()
    create_btn = t('commands_name.seller_profile.create_market', lang)
    await sim.send_message(create_btn)
    await asyncio.sleep(0.1)

    # Bot should trigger ChooseStepHandler for name & description.
    # ChooseStepHandler waits for string input.
    responses = sim.get_sent_requests()
    assert len(responses) > 0

    # Provide market name
    sim.clear_sent_requests()
    await sim.send_message("My Super Store")
    await asyncio.sleep(0.1)

    # Provide description
    sim.clear_sent_requests()
    await sim.send_message("We sell dino accessories!")
    await asyncio.sleep(0.1)

    responses_final = sim.get_sent_requests()
    assert len(responses_final) > 0
    last_text = getattr(responses_final[-1], 'text', '')
    assert t('market_create.create', lang).split('{')[0] in last_text or "создан" in last_text

    # Verify Seller exists in DB
    seller = await Seller.find_one(Seller.owner_id == sim.user_id)
    assert seller is not None
    assert seller.name == "My Super Store"

    # View my market profile
    sim.clear_sent_requests()
    my_btn = t('commands_name.seller_profile.my_market', lang)
    await sim.send_message(my_btn)
    await asyncio.sleep(0.1)

    responses_view = sim.get_sent_requests()
    assert len(responses_view) > 0
    caption = getattr(responses_view[-1], 'caption', '') or getattr(responses_view[-1], 'text', '')
    assert "My Super Store" in caption


@pytest.mark.asyncio
async def test_market_add_and_delete_product(test_dp, test_bot):
    """
    Tests adding a product and then deleting it.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=80002, username="product_manager")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Ensure seller profile exists
    await Seller.find(Seller.owner_id == sim.user_id).delete()
    seller = Seller(owner_id=sim.user_id, name="Store 80002", description="Desc")
    await seller.insert()

    # Clear products
    await Product.find(Product.owner_id == sim.user_id).delete()

    # Give user a weapon item to sell
    await Item.find(Item.owner_id == sim.user_id).delete()
    await Item.add(sim.user_id, "blade_regular", 1)
    db_item = await Item.find_one(Item.owner_id == sim.user_id)
    assert db_item is not None

    # Manually insert product into DB to avoid complex multi-stage item selection states
    from bot.modules.market.market import add_product
    product_id = await add_product(
        sim.user_id, "items_coins", [db_item.items_data], 1000
    )

    product = await Product.find_one(Product.id == product_id)
    assert product is not None
    alt_id = product.alt_id

    # View my products
    sim.clear_sent_requests()
    my_products_btn = t('commands_name.seller_profile.my_products', lang)
    await sim.send_message(my_products_btn)
    await asyncio.sleep(0.1)

    responses = list(sim.get_sent_requests())
    assert len(responses) > 0
    found_search = any(t('products.search', lang) in (getattr(r, 'text', '') or '') for r in responses)
    assert found_search, "Products search header message should be sent"

    # Simulate deleting the product using the callback product_info delete <alt_id>
    from bot.handlers.market import product_info
    from aiogram.types import CallbackQuery, User as TgUser, Message as TgMessage
    from aiogram.types import Chat

    # Create dummy message
    chat = Chat(id=sim.user_id, type="private")
    dummy_message = TgMessage(
        message_id=99999,
        date=12345,
        chat=chat,
        text="dummy"
    )
    dummy_message._bot = sim.bot

    callback = CallbackQuery(
        id="delete_cb",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Manager"),
        chat_instance="inst",
        data=f"product_info delete {alt_id}",
        message=dummy_message
    )
    callback._bot = sim.bot

    await product_info(callback)
    await asyncio.sleep(0.1)

    # Product should be deleted
    product_after = await Product.find_one(Product.id == product_id)
    assert product_after is None, "Product should be deleted from DB"


@pytest.mark.asyncio
async def test_market_buy_product(test_dp, test_bot):
    """
    Tests buying a product from another seller.
    """
    # 1. Setup seller user (90001)
    seller_sim = BotSimulator(test_dp, test_bot, user_id=90001, username="seller_user")
    await setup_user_with_dino(seller_sim)

    # Give seller a weapon
    await Item.find(Item.owner_id == 90001).delete()
    await Item.add(90001, "blade_regular", 1)
    db_item = await Item.find_one(Item.owner_id == 90001)

    # Create product for seller
    from bot.modules.market.market import add_product
    product_id = await add_product(
        90001, "items_coins", [db_item.items_data], 500
    )
    product = await Product.find_one(Product.id == product_id)
    assert product is not None
    alt_id = product.alt_id

    # 2. Setup buyer user (90002) with enough coins
    buyer_sim = BotSimulator(test_dp, test_bot, user_id=90002, username="buyer_user")
    await setup_user_with_dino(buyer_sim)
    buyer_user = await User.find_one(User.userid == 90002)
    buyer_user.coins = 2000
    await buyer_user.save()

    lang = await get_lang(90002, "ru")

    # Clear buyer inventory to easily check what they receive
    await Item.find(Item.owner_id == 90002).delete()

    from bot.modules.market.market_chose import end_buy
    transmitted_data = {
        'id': product_id,
        'name': "Buyer",
        'messageid': 99999,
        'chatid': 90002,
        'userid': 90002,
        'lang': lang
    }

    buyer_sim.clear_sent_requests()
    await end_buy(1, transmitted_data)
    await asyncio.sleep(0.1)

    # Product should be deleted (purchased)
    product_after = await Product.find_one(Product.id == product_id)
    assert product_after is None, "Purchased product should be removed from market"

    # Buyer coins should be deducted
    buyer_after = await User.find_one(User.userid == 90002)
    assert buyer_after.coins == 1500

    # Buyer should have the item in their inventory
    buyer_item = await Item.find_one(Item.owner_id == 90002, {"items_data.item_id": "blade_regular"})
    assert buyer_item is not None
    assert buyer_item.count == 1
