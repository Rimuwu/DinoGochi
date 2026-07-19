"""
Tests for user features via handlers (BotSimulator).
Covers inventory filters/sort/search, item deletion/merchant selling,
desktop crafting, user profile/dino pagination, about menu commands,
collections and donation rating.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import asyncio
from tests.simulator import BotSimulator
from tests.handlers.test_general import register_and_incubate, boost_and_birth
from bot.models.user import User, Lang, Subscription, DinoCollection
from bot.models.dinosaur import Dino, DinoOwners, Egg
from bot.models.items import Item
from bot.models.activity import Activity
from bot.models.other import Donation
from bot.modules.localization import t, get_lang
from bot.modules.items.item import item_code, get_name, get_data
from aiogram.methods import SendMessage, SendPhoto, AnswerCallbackQuery, EditMessageText
from tests.handlers.test_items import setup_user_with_dino, add_item, open_inv_and_click, find_callback_in_markup, confirm_yes

def get_items_on_page(requests):
    """Helper to extract item buttons/names from reply_markup."""
    buttons = []
    for req in reversed(requests):
        markup = getattr(req, 'reply_markup', None)
        if markup:
            if hasattr(markup, 'inline_keyboard'):
                for row in markup.inline_keyboard:
                    for btn in row:
                        buttons.append(btn.text)
            if hasattr(markup, 'keyboard'):
                for row in markup.keyboard:
                    for btn in row:
                        buttons.append(btn.text)
    return buttons

def get_last_markup_buttons(sim):
    markup = sim.get_last_reply_markup()
    buttons = []
    if markup:
        if hasattr(markup, 'inline_keyboard'):
            for row in markup.inline_keyboard:
                for btn in row:
                    buttons.append(btn.text)
        if hasattr(markup, 'keyboard'):
            for row in markup.keyboard:
                for btn in row:
                    buttons.append(btn.text)
    return buttons

async def open_inv_and_click_smart(sim, lang: str, item_id: str):
    from bot.modules.get_state import get_state
    st = await get_state(sim.user_id, sim.user_id)
    await st.clear()

    await sim.send_message(t('commands_name.profile.inventory', lang))
    await asyncio.sleep(0.1)

    buttons = get_last_markup_buttons(sim)
    target_btn = None
    item_display_name = get_name(item_id, lang)
    clean_search = item_display_name.split(None, 1)[-1].lower() if " " in item_display_name else item_display_name.lower()
    for btn in buttons:
        if clean_search in btn.lower():
            target_btn = btn
            break

    if not target_btn:
        target_btn = item_display_name

    sim.clear_sent_requests()
    await sim.send_message(target_btn)
    await asyncio.sleep(0.2)
    return sim.get_sent_requests()

# ---------------------------------------------------------------------------
# 1. ITEM DELETE & MERCHANT FLOWS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_item_delete_flow(test_dp, test_bot):
    """Deleting an item from inventory via the 'delete' button."""
    sim = BotSimulator(test_dp, test_bot, user_id=31001, username="del_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    item_id = 'jar_honey'
    await add_item(sim.user_id, item_id, 1)

    requests = await open_inv_and_click_smart(sim, lang, item_id)

    del_cb = find_callback_in_markup(requests, 'item delete')
    all_replies = [getattr(r, 'text', getattr(r, 'caption', '')) for r in requests]
    assert del_cb is not None, f"Delete button not found. Replies: {all_replies}"

    # Click delete -> sends ConfirmStepData FSM
    await sim.click_callback(del_cb)
    # Confirm deletion
    await sim.send_message(confirm_yes(lang))
    # Choose count = 1
    await sim.send_message("1")
    await asyncio.sleep(0.2)

    # Verify item is deleted
    item_doc = await Item.find_one({'owner': sim.user_id, 'items_data.item_id': item_id})
    assert item_doc is None or item_doc.count == 0, "Item should be deleted"


@pytest.mark.asyncio
async def test_merchant_sell_flow(test_dp, test_bot):
    """Selling an item to the Merchant (Скупщик)."""
    sim = BotSimulator(test_dp, test_bot, user_id=31002, username="merchant_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    item_id = 'jar_honey'
    await add_item(sim.user_id, item_id, 10)

    requests = await open_inv_and_click_smart(sim, lang, item_id)

    buyer_cb = find_callback_in_markup(requests, 'buyer')
    all_replies = [getattr(r, 'text', getattr(r, 'caption', '')) for r in requests]
    assert buyer_cb is not None, f"Merchant button not found. Replies: {all_replies}"

    item_doc_before = await Item.find_one({'owner': sim.user_id, 'items_data.item_id': item_id})
    print("ITEM DOC BEFORE SELL:", item_doc_before)

    user_before = await User.find_one(User.userid == sim.user_id)
    coins_before = user_before.coins

    # Click buyer -> sends ChooseIntHandler
    await sim.click_callback(buyer_cb)
    # Sell count = 1 (meaning 1 pack of 6 items)
    await sim.send_message("1")
    await asyncio.sleep(0.2)
    


    user_after = await User.find_one(User.userid == sim.user_id)
    assert user_after.coins > coins_before, "Coins should increase after selling"

    item_doc = await Item.find_one({'owner': sim.user_id, 'items_data.item_id': item_id})
    assert item_doc is not None and item_doc.count == 4, "Item count should be reduced by 6 (10 -> 4)"


# ---------------------------------------------------------------------------
# 2. DESKTOP CRAFTING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_desktop_craft_flow(test_dp, test_bot):
    """Crafting an item using a recipe and materials in inventory."""
    sim = BotSimulator(test_dp, test_bot, user_id=31003, username="craft_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    recipe_id = 'torch_recipe'
    # Materials for torch_recipe: twigs_tree (4), blank_piece_paper (3)
    await add_item(sim.user_id, recipe_id, 1)
    await add_item(sim.user_id, 'twigs_tree', 4)
    await add_item(sim.user_id, 'blank_piece_paper', 3)

    requests = await open_inv_and_click_smart(sim, lang, recipe_id)

    use_cb = find_callback_in_markup(requests, 'item use')
    assert use_cb is not None

    # Use recipe -> starts craft FSM
    await sim.click_callback(use_cb)
    # Confirm craft
    await sim.send_message(confirm_yes(lang))
    # Select quantity = 1
    await sim.send_message("1")
    await asyncio.sleep(0.2)

    # Since torch_recipe has no time_craft, it crafts instantly
    torch_doc = await Item.find_one({'owner': sim.user_id, 'items_data.item_id': 'torch'})
    all_replies = [getattr(r, 'text', getattr(r, 'caption', '')) for r in sim.get_sent_requests()]
    assert torch_doc is not None and torch_doc.count == 1, f"Torch should be crafted. Replies: {all_replies}"

    # Materials should be consumed
    twigs = await Item.find_one({'owner': sim.user_id, 'items_data.item_id': 'twigs_tree'})
    paper = await Item.find_one({'owner': sim.user_id, 'items_data.item_id': 'blank_piece_paper'})
    assert twigs is None or twigs.count == 0
    assert paper is None or paper.count == 0


# ---------------------------------------------------------------------------
# 3. INVENTORY FUNCTIONALITY: SEARCH, SORT, FILTERS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inventory_search_sort_filters(test_dp, test_bot):
    """Testing search, filters by category, and sorting in inventory."""
    sim = BotSimulator(test_dp, test_bot, user_id=31004, username="inv_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Add diverse items
    await add_item(sim.user_id, 'jar_honey', 1)
    await add_item(sim.user_id, 'twigs_tree', 1)

    # Open inventory
    await sim.send_message(t('commands_name.profile.inventory', lang))
    
    # 1. Search
    search_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_menu search')
    all_replies = [getattr(r, 'text', getattr(r, 'caption', '')) for r in sim.get_sent_requests()]
    assert search_cb is not None, f"Search button not found. Replies: {all_replies}"
    await sim.click_callback(search_cb)
    # Send search query
    await sim.send_message("мёд")
    await asyncio.sleep(0.2)

    btns = get_last_markup_buttons(sim)
    print("SEARCH BUTTONS FOUND:", btns)
    assert any("honey" in btn.lower() or "мёд" in btn.lower() for btn in btns), "Honey should be visible"
    assert not any("twig" in btn.lower() or "вет" in btn.lower() for btn in btns), "Twigs should be filtered out"

    # Reset search
    clear_search_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_menu clear_search')
    if clear_search_cb:
        await sim.click_callback(clear_search_cb)
        await asyncio.sleep(0.1)

    # 2. Filters (Select 'eat' category)
    filters_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_menu filters')
    assert filters_cb is not None
    await sim.click_callback(filters_cb)
    await asyncio.sleep(0.2)
    
    eat_filter_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_filter toggle eat')
    assert eat_filter_cb is not None, "Eat filter button (toggle eat) not found in callbacks"
    await sim.click_callback(eat_filter_cb)
    
    close_filter_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_filter close')
    assert close_filter_cb is not None
    await sim.click_callback(close_filter_cb)
    await asyncio.sleep(0.2)

    # Only eat items should be shown
    btns_filtered = get_last_markup_buttons(sim)
    assert any("honey" in btn.lower() or "мёд" in btn.lower() for btn in btns_filtered)
    assert not any("twig" in btn.lower() or "вет" in btn.lower() for btn in btns_filtered)

    # 3. Sort
    sort_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_menu sort')
    assert sort_cb is not None
    await sim.click_callback(sort_cb)
    
    name_asc_cb = find_callback_in_markup(sim.get_sent_requests(), 'inventory_sort name_asc')
    assert name_asc_cb is not None
    await sim.click_callback(name_asc_cb)
    await asyncio.sleep(0.1)


# ---------------------------------------------------------------------------
# 4. USER PROFILE & DINO PAGINATION (4+ DINOS)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profile_and_dino_pagination(test_dp, test_bot):
    """User profile info and dino list pagination with 5 dinos."""
    sim = BotSimulator(test_dp, test_bot, user_id=31005, username="profile_tester")
    dino1 = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Setup 4 additional dinos (total 5)
    for i in range(4):
        dino_obj = Dino(
            data_id=12000 + i,
            alt_id=f"31005_alt{i}",
            name=f"ExtraDino{i}",
            quality="com"
        )
        await dino_obj.insert()
        conn = DinoOwners(
            dino=dino_obj,
            owner_id=sim.user_id,
            type="owner"
        )
        await conn.insert()

    # Open profile information
    await sim.send_message(t('commands_name.profile.information', lang))
    
    dino_list_cb = find_callback_in_markup(sim.get_sent_requests(), f'user_profile dino {sim.user_id} 0')
    assert dino_list_cb is not None, "Dino list button not found in profile"

    # Click dino list
    await sim.click_callback(dino_list_cb)
    await asyncio.sleep(0.2)

    # Verify pagination arrows are present
    next_page_cb = find_callback_in_markup(sim.get_sent_requests(), f'user_profile dino {sim.user_id} 1')
    assert next_page_cb is not None, "Pagination next page button should be present"

    # Click next page
    await sim.click_callback(next_page_cb)
    await asyncio.sleep(0.2)


# ---------------------------------------------------------------------------
# 5. ABOUT BOT MENU COMMANDS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_about_menu_commands(test_dp, test_bot):
    """Verifies all handlers in 'About Bot' menu."""
    sim = BotSimulator(test_dp, test_bot, user_id=31006, username="about_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Create dummy statistics to cover about_menu stats display
    from bot.models.other import Statistic
    from datetime import datetime
    stat_doc = Statistic(
        date=str(datetime.now().date()),
        users=10,
        dinosaurs=5,
        items=15,
        groups=2
    )
    await stat_doc.insert()

    # Entry: Open about menu
    await sim.send_message(t('commands_name.profile.about', lang))
    await asyncio.sleep(0.1)
    about_main_msg = sim.get_last_message_text()
    assert about_main_msg is not None

    # 1. Team/Developers
    await sim.send_message(t('commands_name.about.team', lang))
    await asyncio.sleep(0.1)
    team_msg = sim.get_last_message_text()
    assert team_msg is not None

    # 2. Links
    await sim.send_message(t('commands_name.about.links', lang))
    await asyncio.sleep(0.1)
    links_msg = sim.get_last_message_text()
    assert links_msg is not None

    # 3. FAQ / Guidebook
    await sim.send_message(t('commands_name.about.faq', lang))
    await asyncio.sleep(0.1)
    faq_msg = sim.get_last_message_text()
    assert faq_msg is not None

    # 4. Statistics / Graphs
    await sim.send_message(t('commands_name.about.grafs', lang))
    await asyncio.sleep(0.1)
    grafs_msg = sim.get_last_message_text()
    assert grafs_msg is not None or any(r.__class__.__name__ in ('SendPhoto', 'EditMessageCaption') for r in sim.get_sent_requests())


# ---------------------------------------------------------------------------
# 6. MY COLLECTION PAGINATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_my_collection_arrows(test_dp, test_bot):
    """Testing my collection page and pagination arrows."""
    sim = BotSimulator(test_dp, test_bot, user_id=31007, username="collection_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Insert items into user's collection
    c1 = DinoCollection(userid=sim.user_id, data_id=1, familie="Herbivorous", date=1783500000)
    c2 = DinoCollection(userid=sim.user_id, data_id=2, familie="Predators", date=1783501000)
    await c1.insert()
    await c2.insert()

    # Open collection
    await sim.send_message(t('commands_name.about.my_collection', lang))
    await asyncio.sleep(0.2)

    # Next page arrow callback (mycol_page:1)
    next_col_cb = find_callback_in_markup(sim.get_sent_requests(), 'mycol_page:1')
    assert next_col_cb is not None, "Collection next page button should be present"

    await sim.click_callback(next_col_cb)
    await asyncio.sleep(0.2)


# ---------------------------------------------------------------------------
# 7. DONATION & RATINGS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_donation_and_rating(test_dp, test_bot):
    """Tests donation submission and rating display (fixing the donation rating)."""
    sim = BotSimulator(test_dp, test_bot, user_id=31008, username="donation_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # 1. Insert donation data
    from bot.modules.donation import save_donation, give_reward
    import time
    code = await save_donation(
        userid=sim.user_id,
        user_first_name="DonatorTest",
        amount=1000,
        product="dino_premium_30",
        time_data=int(time.time()),
        col=1,
        donation_id="test_charge_123"
    )
    assert code is not None

    # Test non_repayable custom donation & duplicate donation_id protection
    code_dup = await save_donation(
        userid=sim.user_id,
        user_first_name="DonatorTest",
        amount=1000,
        product="dino_premium_30",
        time_data=int(time.time()),
        col=1,
        donation_id="test_charge_123"
    )
    assert code_dup == code

    non_rep_code = await save_donation(
        userid=sim.user_id,
        user_first_name="DonatorTest",
        amount=500,
        product="non_repayable",
        time_data=int(time.time()),
        col=1,
        donation_id="test_charge_124"
    )
    await give_reward(sim.user_id, "non_repayable", 1, non_rep_code)

    # Insert CryptoBot donation data (0.50 USDT = 50 cents = 50 Stars)
    from bot.models.other import Donation
    crypto_donat = Donation(
        code=f"crypto_{sim.user_id}",
        userid=sim.user_id,
        user_first_name="DonatorTest",
        amount=50,  # 50 cents (0.50 USDT) = 50 Stars
        product="dino_ultima",
        issued_reward=True,
        send_notification=True,
        time=int(time.time()),
        col=1,
        donation_id="test_crypto_1",
        status="done",
        provider="cryptobot"
    )
    await crypto_donat.insert()

    # Rebuild ratings cache in Redis
    from bot.tasks.data_reupdat import rating_check
    await rating_check()

    # 2. View ratings menu
    await sim.send_message(t('commands_name.profile.rating', lang))
    await asyncio.sleep(0.2)

    # Click donate rating
    donate_cb = find_callback_in_markup(sim.get_sent_requests(), 'donate_rating')
    assert donate_cb is not None
    await sim.click_callback(donate_cb)
    await asyncio.sleep(0.1)

    # Select all-time rating
    all_time_cb = find_callback_in_markup(sim.get_sent_requests(), 'donate_rating all')
    assert all_time_cb is not None
    await sim.click_callback(all_time_cb)
    await asyncio.sleep(0.2)

    # Verify rating output contains donor name or sum
    all_texts = [getattr(r, 'text', getattr(r, 'caption', '')) for r in sim.get_sent_requests()]
    assert any("Test" in (txt or '') for txt in all_texts), f"Donor name 'Test' should be shown in rating. Sent: {all_texts}"


@pytest.mark.asyncio
async def test_inventory_lazy_loading_perf(test_dp, test_bot):
    """Verifies inventory lazy loading performance and Redis state size with 100+ pages (300,000+ items)."""
    sim = BotSimulator(test_dp, test_bot, user_id=31099, username="perf_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Generate 1500 unique item definitions by varying item_id and endurance
    from bot.modules.items.item import ITEMS
    from bot.models.items import Item
    
    unique_items_to_add = []
    item_ids = list(ITEMS.keys())
    
    # Generate 1500 distinct items (different item_id or durability values)
    count_created = 0
    for item_id in item_ids:
        # Varying endurance from 1 to 5 to make them unique inventory entries
        for endurance in range(1, 6):
            if count_created >= 1500:
                break
            unique_items_to_add.append({
                "item_id": item_id,
                "abilities": {"endurance": endurance}
            })
            count_created += 1
        if count_created >= 1500:
            break

    # Bulk insert into MongoDB to speed up test execution
    db_items = []
    for ui in unique_items_to_add:
        db_items.append(Item(
            owner=sim.user_id,
            items_data={"item_id": ui["item_id"], "abilities": ui["abilities"]},
            count=200 # Total 300,000 items
        ))
    await Item.insert_many(db_items)

    import time
    start_time = time.time()

    # Open Inventory
    await sim.send_message(t('commands_name.profile.inventory', lang))
    await asyncio.sleep(0.3)

    load_duration = time.time() - start_time
    assert load_duration < 1.0, f"Inventory opened too slowly: {load_duration}s"

    # Verify FSM Redis state size and lazy rendering
    from bot.modules.get_state import get_state
    state = await get_state(sim.user_id, sim.user_id)
    state_data = await state.get_data()
    
    pages = state_data['pages']
    total_pages = len(pages)
    
    # 1500 items / 6 items per page = 250 pages
    assert total_pages == 250, f"Expected 250 pages, got {total_pages}"
    
    # Check that only current (0), next (1), and previous/last (249) are rendered
    assert pages[0] is not None, "Page 0 should be rendered"
    assert pages[1] is not None, "Page 1 should be rendered"
    assert pages[249] is not None, "Page 249 should be rendered"
    
    # Pages in the middle must be None (not loaded)
    assert pages[100] is None, "Page 100 should not be rendered yet (lazy load)"
    
    # Swipe to page 1
    from bot.const import GAME_SETTINGS
    await sim.send_message(GAME_SETTINGS['forward_button'])
    await asyncio.sleep(0.2)
    
    # Check page 2 is now rendered on swipe
    state_data = await state.get_data()
    pages_after = state_data['pages']
    assert pages_after[2] is not None, "Page 2 should be rendered now after swiping to page 1"


@pytest.mark.asyncio
async def test_profile_inventory_pagination(test_dp, test_bot):
    """Verifies profile inventory pagination and rarity sorting."""
    sim = BotSimulator(test_dp, test_bot, user_id=31007, username="inv_profile_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    from bot.modules.items.item_tools import AddItemToUser
    
    # Add 11 distinct items to force pagination (since page size is 10)
    items_to_add = [
        "twigs_tree", "clay", "leather_clothing", "iron_sword",
        "rope", "feather", "fish_oil", "torch", "tea", "salad", "soup"
    ]
    for item_id in items_to_add:
        await AddItemToUser(sim.user_id, item_id, 1)
    
    # Open profile information
    await sim.send_message(t('commands_name.profile.information', lang))
    await asyncio.sleep(0.2)
    
    # Check for inventory button in profile markup
    inv_cb = find_callback_in_markup(sim.get_sent_requests(), f'user_profile inventory {sim.user_id} 0')
    assert inv_cb is not None, "Inventory backpack button not found in profile markup"
    
    # Click inventory button
    await sim.click_callback(inv_cb)
    await asyncio.sleep(0.2)
    
    # Verify we can find next page button (page 1)
    next_page_cb = find_callback_in_markup(sim.get_sent_requests(), f'user_profile inventory {sim.user_id} 1')
    assert next_page_cb is not None, "Inventory profile pagination next button not found"
    
    # Click next page
    await sim.click_callback(next_page_cb)
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_shop_push_behavior_and_multi_item_image(test_dp, test_bot):
    """Verifies multi-item image generation, Redis caching, and shop push behavior toggle."""
    from bot.modules.images import create_multi_items_image, send_items_photo
    from bot.models.market import Product, Seller, Puhs
    from bot.redismanager import redis_get
    
    # 1. Verify multi-item image generator works
    items = [{"item_id": "twigs_tree", "count": 2}, {"item_id": "clay", "count": 1}]
    img_file = await create_multi_items_image(items)
    assert img_file is not None
    assert img_file.filename == "DinoGochi.JPEG"
    
    # 2. Verify Redis caching logic works
    chat_id = 999999
    mes1 = await send_items_photo(chat_id, items, "Test caption")
    assert mes1 is not None
    
    sorted_items = sorted(items[:10], key=lambda x: (x['item_id'], x.get('count', 1)))
    key_parts = [f"{i['item_id']}:{i.get('count', 1)}" for i in sorted_items]
    redis_key = f"file_id:multi_items:{'_'.join(key_parts)}"
    
    cached_file_id = await redis_get(redis_key)
    assert cached_file_id is not None, "Generated image file_id should be cached in Redis"
    
    mes2 = await send_items_photo(chat_id, items, "Test caption")
    assert mes2 is not None
    
    # 3. Verify shop menu channel configurations
    sim = BotSimulator(test_dp, test_bot, user_id=31008, username="shop_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")
    
    await Seller.create_shop(sim.user_id, "Test Shop Name", "Shop description")
    
    puhs = Puhs(owner_id=sim.user_id, channel_id=-1001234567, lang=lang)
    await puhs.insert()
    
    from bot.modules.market.market import seller_ui
    text, markup, image = await seller_ui(sim.user_id, lang, True)
    assert markup is not None
    
    push_cb = next((b.callback_data for row in markup.inline_keyboard for b in row if "push_channel" in b.callback_data), None)
    assert push_cb is not None, "Publishing Channel button should be present in shop menu"
    
    from bot.handlers.market import seller
    class MockCall:
        def __init__(self, data, message, from_user):
            self.data = data
            self.message = message
            self.from_user = from_user
            
    class MockMessage:
        def __init__(self):
            class Chat:
                def __init__(self):
                    self.id = 31008
            self.chat = Chat()
            self.message_id = 12345
            
    class MockUser:
        def __init__(self):
            self.id = 31008
            
    call = MockCall(f"seller push_channel {sim.user_id}", MockMessage(), MockUser())
    await seller(call)
    
    seller_doc = await Seller.find_one(Seller.owner_id == sim.user_id)
    assert getattr(seller_doc, "stock_out_behavior", "zero") == "zero"
    
    call_toggle = MockCall(f"seller toggle_behavior {sim.user_id}", MockMessage(), MockUser())
    await seller(call_toggle)
    
    seller_doc_after = await Seller.find_one(Seller.owner_id == sim.user_id)
    assert getattr(seller_doc_after, "stock_out_behavior", "zero") == "delete", "Stock behavior should toggle to delete"

