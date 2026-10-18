import os
import sys
import time
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import asyncio
from bson.objectid import ObjectId
from tests.simulator import BotSimulator
from tests.handlers.test_general import register_and_incubate, boost_and_birth
from bot.models.user import User
from bot.models.dinosaur import Dino
from bot.models.items import Item
from bot.models.activity import JourneyActivity
from bot.handlers.actions_live.journey import select_duration_and_start, JourneySetupStates
from bot.modules.get_state import get_state
from aiogram.types import CallbackQuery, Message


@pytest.mark.asyncio
async def test_journey_bag_removes_and_restores_weapon(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=45001, username="journey_dupe_test")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    user = await User.find_one(User.userid == sim.user_id)
    # Add a weapon with custom endurance
    await user.add_item("sword_iron", 1, {"endurance": 75})

    inv_before = await Item.find({"owner": sim.user_id, "items_data.item_id": "sword_iron"}).to_list()
    assert len(inv_before) == 1
    assert inv_before[0].abilities.get("endurance") == 75

    # Simulate bag selection state
    state = await get_state(sim.user_id, sim.user_id)
    await state.set_state(JourneySetupStates.selecting_duration)
    await state.update_data(
        selected_dino_ids=[str(dino.id)],
        location="forest",
        chosen_bag_items=[{
            "item_id": "sword_iron",
            "abilities": {"endurance": 75},
            "count": 1
        }],
        bag_selections={"sword_iron": 1}
    )

    cb_msg = Message(
        message_id=999,
        date=int(time.time()),
        chat=sim.chat,
        from_user=sim.tg_user,
        text="[Duration Message]"
    )
    cb = CallbackQuery(
        id="123",
        from_user=sim.tg_user,
        chat_instance="1",
        message=cb_msg,
        data="w_time:t30"
    ).as_(test_bot)

    await select_duration_and_start(cb, state)

    # Verify weapon is REMOVED from user's inventory while in journey!
    inv_during = await Item.find({"owner": sim.user_id, "items_data.item_id": "sword_iron"}).to_list()
    assert len(inv_during) == 0, "Weapon must be removed from inventory when journey starts!"

    # Verify journey is active with the weapon in bag
    journey = await JourneyActivity.find_one(JourneyActivity.userid == sim.user_id)
    assert journey is not None
    assert len(journey.bag) == 1
    assert journey.bag[0]["item_id"] == "sword_iron"
    assert journey.bag[0]["abilities"]["endurance"] == 75

    # End journey
    await JourneyActivity.end(journey.id)

    # Verify weapon is returned to user inventory without duplication (count = 1)
    inv_after = await Item.find({"owner": sim.user_id, "items_data.item_id": "sword_iron"}).to_list()
    assert len(inv_after) == 1, "User should have exactly 1 weapon returned!"
    assert inv_after[0].count == 1
    assert inv_after[0].abilities.get("endurance") == 75


@pytest.mark.asyncio
async def test_journey_concurrent_end_no_duplication(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=45002, username="concurrent_end_test")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    user = await User.find_one(User.userid == sim.user_id)
    await user.add_item("bow_hunting", 1, {"endurance": 50})

    # Start journey with bow_hunting in bag
    await Item.remove(sim.user_id, "bow_hunting", 1, {"endurance": 50})
    journey_res = await JourneyActivity.start(
        [dino.id],
        sim.user_id,
        duration=1800,
        location="forest",
        bag_items=[{
            "item_id": "bow_hunting",
            "abilities": {"endurance": 50},
            "count": 1
        }]
    )
    assert journey_res is True

    journey = await JourneyActivity.find_one(JourneyActivity.userid == sim.user_id)
    assert journey is not None

    # Call end concurrently twice
    await asyncio.gather(
        JourneyActivity.end(journey.id),
        JourneyActivity.end(journey.id)
    )

    # Check inventory: bow_hunting must only be awarded ONCE!
    inv = await Item.find({"owner": sim.user_id, "items_data.item_id": "bow_hunting"}).to_list()
    assert len(inv) == 1
    assert inv[0].count == 1
    assert inv[0].abilities.get("endurance") == 50


@pytest.mark.asyncio
async def test_arena_bag_item_deduction_and_cancel_refund(test_dp, test_bot):
    from bot.handlers.arena import arena_bag_callback, search_cancel_callback
    from bot.models.arena import ArenaQueueModel

    sim = BotSimulator(test_dp, test_bot, user_id=45003, username="arena_dupe_test")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    user = await User.find_one(User.userid == sim.user_id)
    await user.add_item("spear_piercing", 1, {"endurance": 60})

    # Call arena_bag_callback with mocked open arena
    return_data = {
        "bag_items": [{
            "item_id": "spear_piercing",
            "abilities": {"endurance": 60},
            "count": 1
        }]
    }
    trans_data = {
        "userid": sim.user_id,
        "chatid": sim.user_id,
        "lang": "ru",
        "selected_dino_ids": [str(dino.id)],
        "category": "solo"
    }

    with unittest.mock.patch("bot.tasks.arena_tasks.get_arena_status", return_value=(True, 3600)):
        await arena_bag_callback(return_data, trans_data)

    # Verify spear is removed from inventory while in arena queue
    inv_queue = await Item.find({"owner": sim.user_id, "items_data.item_id": "spear_piercing"}).to_list()
    assert len(inv_queue) == 0, "Spear must be removed from inventory when entered arena queue!"

    # Cancel search
    cancel_msg = Message(
        message_id=999,
        date=int(time.time()),
        chat=sim.chat,
        from_user=sim.tg_user,
        text="[Cancel Search]"
    )
    cb = CallbackQuery(
        id="124",
        from_user=sim.tg_user,
        chat_instance="1",
        message=cancel_msg,
        data="arena:search_cancel"
    ).as_(test_bot)

    await search_cancel_callback(cb)

    # Verify spear is refunded exactly once (count = 1)
    inv_refund = await Item.find({"owner": sim.user_id, "items_data.item_id": "spear_piercing"}).to_list()
    assert len(inv_refund) == 1, "User should have exactly 1 spear refunded!"
    assert inv_refund[0].count == 1
    assert inv_refund[0].abilities.get("endurance") == 60
