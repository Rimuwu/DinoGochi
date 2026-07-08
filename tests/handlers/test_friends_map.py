import os
import sys
import pytest
import asyncio
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.simulator import BotSimulator
from tests.handlers.test_general import register_and_incubate, boost_and_birth
from bot.models.user import User, Lang, Friend, Referral
from bot.models.dinosaur import Dino, DinoOwners
from bot.models.items import Item
from bot.models.market import Product, Seller
from bot.modules.localization import t, get_lang, get_data
from bot.modules.markup import confirm_markup

# Helper: setup two users
async def setup_two_users(test_dp, test_bot):
    sim1 = BotSimulator(test_dp, test_bot, user_id=88001, username="user_one")
    # Remove existing if any
    await User.find(User.userid == 88001).delete()
    await User.find(User.userid == 88002).delete()
    await Friend.find({'userid': 88001}).delete()
    await Friend.find({'friendid': 88001}).delete()
    await Friend.find({'userid': 88002}).delete()
    await Friend.find({'friendid': 88002}).delete()
    
    # Manually register user1 in DB to speed up
    u1 = User(userid=88001, name="User One", coins=5000, super_coins=100, lvl=5)
    await u1.insert()
    l1 = Lang(userid=88001, lang="ru")
    await l1.insert()

    sim2 = BotSimulator(test_dp, test_bot, user_id=88002, username="user_two")
    u2 = User(userid=88002, name="User Two", coins=2000, super_coins=50, lvl=5)
    await u2.insert()
    l2 = Lang(userid=88002, lang="ru")
    await l2.insert()

    return sim1, sim2

@pytest.mark.asyncio
async def test_friends_add_delete_and_transfer_coins(test_dp, test_bot):
    """Verifies adding a friend, sending coins and super-coins, and deleting a friend."""
    sim1, sim2 = await setup_two_users(test_dp, test_bot)
    lang = "ru"

    # 1. User 1 requests to add User 2 via User ID
    await sim1.send_message(t('commands_name.friends.add_friend', lang))
    # Select ID type adding method from inline button
    # Add friend via ID inline callback: "add_friend id"
    await sim1.send_message(t('buttons_name.cancel', lang)) # First cancel any state
    from bot.modules.get_state import get_state
    await (await get_state(sim1.user_id, sim1.user_id)).clear()

    # Directly trigger callback as clicking the button
    await sim1.click_callback("add_friend id")
    await asyncio.sleep(0.1)

    # Send User 2 ID
    await sim1.send_message(str(sim2.user_id))
    await asyncio.sleep(0.2)

    # Verify request created in DB
    conn = await Friend.find_one(Friend.userid == sim1.user_id, Friend.friendid == sim2.user_id, Friend.type == "request")
    assert conn is not None, "Friend request should be created in DB"

    # 2. User 2 accepts the friend request
    await sim2.send_message(t('commands_name.friends.requests', lang))
    await asyncio.sleep(0.2)

    # ChoosePagesStateHandler uses ordinary reply keyboard messages, so we send the button text "✅ 1"
    await sim2.send_message("✅ 1")
    await asyncio.sleep(0.2)

    # Verify type became friends
    conn_after = await Friend.find_one(Friend.userid == sim1.user_id, Friend.friendid == sim2.user_id)
    assert conn_after is not None and conn_after.type == "friends", "Request should be accepted as friends"

    # 3. User 1 transfers 1000 ordinary coins to User 2
    # Trigger take_money call from callback (which is actually coin transfer)
    await sim1.click_callback(f"take_money {sim2.user_id}")
    await asyncio.sleep(0.1)

    # Send transfer count: 1000
    await sim1.send_message("1000")
    await asyncio.sleep(0.2)

    # Verify coin balances
    u1 = await User.find_one(User.userid == sim1.user_id)
    u2 = await User.find_one(User.userid == sim2.user_id)
    assert u1.coins == 4000
    assert u2.coins == 3000

    # 4. User 1 transfers 50 super coins to User 2
    await sim1.click_callback(f"take_coins {sim2.user_id}")
    await asyncio.sleep(0.1)

    # Send transfer count: 50
    await sim1.send_message("50")
    await asyncio.sleep(0.2)

    # Verify super coin balances
    u1 = await User.find_one(User.userid == sim1.user_id)
    u2 = await User.find_one(User.userid == sim2.user_id)
    assert u1.super_coins == 50
    assert u2.super_coins == 100

    # 5. Remove friend
    await sim1.send_message(t('commands_name.friends.remove_friend', lang))
    await asyncio.sleep(0.1)
    
    # Choose friend to delete by sending their name
    state_s1 = await get_state(sim1.user_id, sim1.user_id)
    state_data1 = await state_s1.get_data()
    options_del = state_data1.get('options', {})
    friend_name = next((k for k, v in options_del.items() if v == sim2.user_id), None)
    assert friend_name is not None, "Delete target name should be in options"

    await sim1.send_message(friend_name)
    await asyncio.sleep(0.1)
    
    # Confirm deletion
    await sim1.send_message(t('buttons_name.yes', lang))
    await asyncio.sleep(0.2)

    # Verify friend removed from DB
    friendship = await Friend.find_one(Friend.userid == sim1.user_id, Friend.friendid == sim2.user_id)
    assert friendship is None, "Friend connection should be deleted from DB"

@pytest.mark.asyncio
async def test_referral_code_generation(test_dp, test_bot):
    """Verifies generating referral code and custom code creation."""
    sim = BotSimulator(test_dp, test_bot, user_id=88003, username="ref_tester")
    await User.find(User.userid == 88003).delete()
    await Referral.find(Referral.userid == 88003).delete()
    
    u = User(userid=88003, name="Ref Tester", coins=6000)
    await u.insert()
    l = Lang(userid=88003, lang="ru")
    await l.insert()
    lang = await get_lang(sim.user_id, "ru")

    # Request code generation page
    await sim.send_message(t('commands_name.referal.code', lang))
    await asyncio.sleep(0.1)

    # Click generate custom code callback
    await sim.click_callback("generate_referal custom")
    await asyncio.sleep(0.1)

    # Input custom code name
    custom_code = "COOLREFCODE"
    await sim.send_message(custom_code)
    await asyncio.sleep(0.2)

    # Verify referral record exists
    ref = await Referral.find_one(Referral.userid == sim.user_id, Referral.code == custom_code)
    assert ref is not None, "Referral custom code should be created in DB"

    # Verify coins were deducted
    u_after = await User.find_one(User.userid == sim.user_id)
    from bot.const import GAME_SETTINGS as GS
    assert u_after.coins == 6000 - GS['referal']['custom_price']

@pytest.mark.asyncio
async def test_map_navigation_and_submenus(test_dp, test_bot):
    """Verifies Map navigation, Taverna events, Blacksmith item upgrades, and Market Seller/Products."""
    sim = BotSimulator(test_dp, test_bot, user_id=88004, username="map_tester")
    await User.find(User.userid == 88004).delete()
    await Seller.find(Seller.owner_id == 88004).delete()
    
    u = User(userid=88004, name="Map Tester", coins=10000, lvl=5)
    await u.insert()
    l = Lang(userid=88004, lang="ru")
    await l.insert()
    lang = await get_lang(sim.user_id, "ru")

    # 1. Map command
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.map-bt', lang))
    await asyncio.sleep(0.1)

    # 2. Tavern Events
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.dino_tavern.events', lang))
    await asyncio.sleep(0.2)
    text = sim.get_last_message_text()
    assert text is not None and "события" in text.lower()

    # 3. Tavern Daily Award (bonus)
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.dino_tavern.daily_award', lang))
    await asyncio.sleep(0.2)
    text = sim.get_last_message_text()
    assert text is not None

    # 4. Tavern Mutation/Edit (transformation)
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.dino_tavern.edit', lang))
    await asyncio.sleep(0.2)
    text = sim.get_last_message_text()
    assert text is not None

    # 5. Tavern Quests
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.dino_tavern.quests', lang))
    await asyncio.sleep(0.2)
    text = sim.get_last_message_text()
    assert text is not None

    # 6. Tavern Hoarder (baraholschik)
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.dino_tavern.hoarder', lang))
    await asyncio.sleep(0.2)
    text = sim.get_last_message_text()
    assert text is not None

    # 7. Blacksmith Menu
    sim.clear_sent_requests()
    await sim.send_message("/blacksmith")
    await asyncio.sleep(0.2)
    text = sim.get_last_message_text()
    assert text is not None and "кузн" in text.lower()

    # 8. Market Seller Account registration
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.market', lang))
    await asyncio.sleep(0.2)

    # Open registration
    await sim.send_message(t('commands_name.seller_profile.create_market', lang))
    await asyncio.sleep(0.1)

    # Step 1: Input name
    await sim.send_message("My Cool Shop")
    await asyncio.sleep(0.1)

    # Step 2: Input description
    await sim.send_message("Best dinos and stuff")
    await asyncio.sleep(0.2)

    # Verify seller created
    seller = await Seller.find_one(Seller.owner_id == sim.user_id)
    assert seller is not None, "Seller account should be registered"
    assert seller.name == "My Cool Shop"

    # Add items to user map_tester so they can list products and test ChooseMultiInventory search/sort/filter
    await Item.find({'$or': [{'owner': sim.user_id}, {'owner': str(sim.user_id)}], 'items_data.item_id': {'$exists': True}}).delete()
    # Add regular cookie (interactive, sellable)
    await Item.add(sim.user_id, "cookie", 5)
    # Add freezing_1moth (special, cant_sell: true)
    await Item.add(sim.user_id, "freezing_1moth", 1)
    # Let's open Sell Product menu to list an item (option items_coins: 🍕 ➞ 🪙)
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.seller_profile.add_product', lang))
    await asyncio.sleep(0.2)
    
    # Choose items_coins option ("🍕 ➞ 🪙")
    await sim.send_message("🍕 ➞ 🪙")
    await asyncio.sleep(0.2)
    
    # Verify that ChooseMultiInventory state is active
    from bot.modules.get_state import get_state
    state = await get_state(sim.user_id, sim.user_id)
    st_data = await state.get_data()
    virtual_pages = st_data.get('virtual_pages', [])
    assert len(virtual_pages) > 0
    
    # Check that freezing_1moth is NOT in virtual_pages (cant_sell was successfully ignored)
    all_names = [name for page in virtual_pages for name, _, _ in page]
    assert not any("freezing" in n.lower() for n in all_names), "Freezing items must be filtered out by cant_sell rule"

    # Test sorting
    await sim.click_callback("multinv:sort")
    await asyncio.sleep(0.1)
    st_data = await state.get_data()
    assert st_data.get('inv_sort') == 'name_desc'

    # Test search query trigger
    await sim.click_callback("multinv:search")
    await asyncio.sleep(0.1)
    # Send search text
    await sim.send_message("cookie")
    await asyncio.sleep(0.2)
    
    st_data = await state.get_data()
    assert st_data.get('search_query') == 'cookie'
