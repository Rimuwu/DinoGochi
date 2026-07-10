"""
Tests for Blacksmith (bot/handlers/blacksmith.py) via real handler flows.
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
async def test_blacksmith_menu_and_info(test_dp, test_bot):
    """
    Verifies that /blacksmith command opens the menu, and info button displays the blacksmith info.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=70001, username="bs_menu_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message("/blacksmith")
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0, "Should reply to /blacksmith command"

    # Click Info button (represented by commands_name.blacksmith.info localization string)
    info_text = t('commands_name.blacksmith.info', lang)
    sim.clear_sent_requests()
    await sim.send_message(info_text)
    await asyncio.sleep(0.1)

    responses_info = sim.get_sent_requests()
    assert len(responses_info) > 0
    # The response text should contain blacksmith table prices
    last_resp = responses_info[-1]
    text = getattr(last_resp, 'text', '') or getattr(last_resp, 'caption', '')
    assert "⭐" in text or "%" in text, "Blacksmith info should display prices/chances table"


@pytest.mark.asyncio
async def test_blacksmith_no_items_select(test_dp, test_bot):
    """
    If user tries to upgrade but has no upgradable items, they should get a 'no items' message.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=70002, username="bs_no_items_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Clear inventory first
    await Item.find(Item.owner_id == sim.user_id).delete()

    sim.clear_sent_requests()
    upgrade_btn = t('commands_name.blacksmith.upgrade', lang)
    await sim.send_message(upgrade_btn)
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '')
    assert t('blacksmith.no_items', lang) in last_text, "Should notify user about no upgradable items"


@pytest.mark.asyncio
async def test_blacksmith_upgrade_flow_and_toggles(test_dp, test_bot):
    """
    Simulates the full upgrade flow:
    - User has 2x blade_regular (lvl 0)
    - Starts upgrade -> select item -> quantity screen -> choose rune -> confirm -> complete
    """
    sim = BotSimulator(test_dp, test_bot, user_id=70003, username="bs_flow_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Give user 2x weapon
    await Item.find(Item.owner_id == sim.user_id).delete()
    await Item.add(sim.user_id, "blade_regular", 2, {"lvl": 0})
    await Item.add(sim.user_id, "rune_lvl3", 1)  # add a rune

    # Give user enough coins
    user = await User.find_one(User.userid == sim.user_id)
    await user.add_coins(5000)

    db_item = await Item.find_one(Item.owner_id == sim.user_id, {"items_data.item_id": "blade_regular"})
    assert db_item is not None

    # Step 1: Open selection (simulating state handler call or directly trigger blacksmith_select_item)
    from bot.handlers.blacksmith import blacksmith_select_item
    sim.clear_sent_requests()
    transmitted_data = {'chatid': sim.user_id, 'lang': lang, 'userid': sim.user_id}
    await blacksmith_select_item(db_item.items_data, transmitted_data)
    await asyncio.sleep(0.1)

    responses = list(sim.get_sent_requests())
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '')
    assert t('blacksmith.choose_rune', lang) in last_text

    cb_msg = responses[-1]
    sim.clear_sent_requests()

    from aiogram.types import Chat, Message as TgMessage, CallbackQuery, User as TgUser
    chat = Chat(id=sim.user_id, type="private")
    dummy_message = TgMessage(
        message_id=12345,
        date=12345,
        chat=chat,
        text="dummy"
    )
    dummy_message._bot = sim.bot

    # Create callback query
    callback = CallbackQuery(
        id="cb_id",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Test"),
        chat_instance="chat_inst",
        data=f"bs_r:{db_item.id}:rune_lvl3:1",
        message=dummy_message
    )
    callback._bot = sim.bot

    from bot.handlers.blacksmith import bs_rune_select
    await bs_rune_select(callback)
    await asyncio.sleep(0.1)

    # Now it should show confirmation screen
    responses2 = list(sim.get_sent_requests())
    assert len(responses2) > 0
    last_text2 = getattr(responses2[-1], 'text', '')
    assert "улучшения" in last_text2 or "Подтверждение" in last_text2

    # Let's test the mark name checkbox toggle "bs_mark:{db_item.id}:{rune_item_id}:{quantity}:{new_mark}"
    from bot.handlers.blacksmith import bs_mark_toggle
    callback_mark = CallbackQuery(
        id="cb_id_mark",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Test"),
        chat_instance="chat_inst",
        data=f"bs_mark:{db_item.id}:rune_lvl3:1:1",
        message=dummy_message
    )
    callback_mark._bot = sim.bot
    await bs_mark_toggle(callback_mark)
    await asyncio.sleep(0.1)

    # Let's confirm the upgrade "bs_upg:{db_item.id}:{rune_id}:{qty}:{mark}"
    from bot.handlers.blacksmith import bs_upgrade_confirm
    sim.clear_sent_requests()
    callback_confirm = CallbackQuery(
        id="cb_id_confirm",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Test"),
        chat_instance="chat_inst",
        data=f"bs_upg:{db_item.id}:rune_lvl3:1:1",
        message=dummy_message
    )
    callback_confirm._bot = sim.bot

    # Stub random to guarantee success
    import random
    old_random = random.random
    random.random = lambda: 0.0  # force success (since final_chance will be > 0.0)

    try:
        await bs_upgrade_confirm(callback_confirm)
        await asyncio.sleep(0.1)
    finally:
        random.random = old_random

    # Verify result
    responses3 = sim.get_sent_requests()
    assert len(responses3) > 0
    last_text3 = getattr(responses3[-1], 'text', '')
    assert t('blacksmith.results', lang).split('{')[0] in last_text3 or "Результат" in last_text3

    # The 2x blade_regular (lvl 0) should be gone, and 1x blade_regular (lvl 1) should be in DB
    weapon_lvl1 = await Item.find_one(Item.owner_id == sim.user_id, {"items_data.item_id": "blade_regular", "items_data.abilities.lvl": 1})
    assert weapon_lvl1 is not None, "Upgrade should produce lvl 1 weapon"
    assert weapon_lvl1.count == 1
    # Check that author is NOT set for level 1 (requires target_lvl >= 2)
    assert weapon_lvl1.abilities.get('author') is None
