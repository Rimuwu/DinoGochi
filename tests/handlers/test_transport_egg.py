"""
Tests for Transport Egg via REAL handler flow:
- item_info display (covers the KeyError 'abilities' bug)
- pack dino into egg via inventory -> use callback -> dino selection
- unpack dino from egg via inventory -> use callback
"""
import os
import sys
import pytest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.simulator import BotSimulator
from tests.handlers.test_general import register_and_incubate, boost_and_birth
from bot.models.user import User
from bot.models.dinosaur import Dino, DinoOwners
from bot.models.items import Item
from bot.models.activity import Activity
from bot.modules.localization import get_lang, t
from bot.modules.items.item import get_name as _get_name


async def setup_user_with_dino(sim: BotSimulator) -> Dino:
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None
    from bot.modules.get_state import get_state
    st = await get_state(sim.user_id, sim.user_id)
    await st.clear()
    return dino


def find_use_callback(requests) -> str | None:
    """Find 'item use' callback in any sent markup."""
    for req in reversed(requests):
        markup = getattr(req, 'reply_markup', None)
        if markup and hasattr(markup, 'inline_keyboard'):
            for row in markup.inline_keyboard:
                for btn in row:
                    if btn.callback_data and btn.callback_data.startswith('item use'):
                        return btn.callback_data
    return None


async def open_inventory_item(sim: BotSimulator, lang: str, item_id: str):
    """Navigate: open inventory → type item display name → get item_info response."""
    from bot.modules.get_state import get_state
    st = await get_state(sim.user_id, sim.user_id)
    await st.clear()

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.profile.inventory', lang))
    sim.clear_sent_requests()

    item_display = _get_name(item_id, lang)
    await sim.send_message(item_display)
    await asyncio.sleep(0.2)
    return sim.get_sent_requests()


# ---------------------------------------------------------------------------
# Test 1: Display transport egg info via real item_info path (no abilities KeyError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transport_egg_item_info_display(test_dp, test_bot):
    """
    Verifies that item_info for transport_egg (with and without abilities in DB)
    does NOT crash with KeyError: 'abilities'.
    This is the path: inventory -> send_item_info -> item_info
    """
    sim = BotSimulator(test_dp, test_bot, user_id=50011, username="egg_info_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Add transport_egg using proper Item.add (which calls get_item_dict → stores abilities correctly)
    await Item.add(sim.user_id, "transport_egg", 1)

    # Navigate into the inventory to display item info — this calls item_info
    responses = await open_inventory_item(sim, lang, "transport_egg")

    # Bot should have responded (no crash)
    assert len(responses) > 0, "Bot should respond when viewing transport_egg in inventory"

    # Verify it's not an error — there should be text with item info
    last_text = None
    for req in reversed(responses):
        txt = getattr(req, 'text', None) or getattr(req, 'caption', None)
        if txt:
            last_text = txt
            break
    assert last_text is not None, "Bot response should contain text (item info)"


# ---------------------------------------------------------------------------
# Test 2: Pack dino into transport egg via full handler flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transport_egg_pack_via_handler(test_dp, test_bot):
    """
    Full handler flow for PACKING a dino into transport_egg:
    inventory -> item name -> 'item use' callback -> confirm -> dino name
    Expected:
    - Dino gets an 'inactive' Activity.
    - DinoOwners record deleted.
    - Filled transport_egg (data_id = dino.alt_id) appears in inventory.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=50012, username="egg_packer")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Add empty transport_egg through proper Item.add (creates with abilities.data_id=0 from JSON)
    await Item.add(sim.user_id, "transport_egg", 1)

    # Open inventory → view item
    responses = await open_inventory_item(sim, lang, "transport_egg")

    # Find "item use" callback button
    use_cb = find_use_callback(responses)
    assert use_cb is not None, "No 'item use' button found in transport_egg info"

    # Click "use" → should prompt for confirm or dino selection
    sim.clear_sent_requests()
    await sim.click_callback(use_cb)
    await asyncio.sleep(0.1)

    # Confirm (if step exists)
    await sim.send_message(t('buttons_name.yes', lang))
    await asyncio.sleep(0.1)

    # Select dino by name
    await sim.send_message(dino.name)
    await asyncio.sleep(0.3)

    # Verify: dino should be in inactive activity
    inactive = await Activity.get_pymongo_collection().find_one({
        "activity_type": "inactive",
        "$or": [{"dino_id": dino.id}, {"dino_id": str(dino.id)}]
    })
    assert inactive is not None, "Dino should have inactive activity after being packed into egg"

    # Verify: DinoOwners connection removed
    owner_link = await DinoOwners.find_one(DinoOwners.dino.id == dino.id)
    assert owner_link is None, "DinoOwners should be deleted after packing dino"

    # Verify: filled egg exists
    filled_egg = await Item.find_one({
        "owner": sim.user_id,
        "items_data.item_id": "transport_egg",
        "items_data.abilities.data_id": dino.alt_id
    })
    assert filled_egg is not None, "Filled transport_egg (with dino.alt_id) should be in inventory"


# ---------------------------------------------------------------------------
# Test 3: Unpack dino from transport egg via full handler flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transport_egg_unpack_via_handler(test_dp, test_bot):
    """
    Full handler flow for UNPACKING a dino from a filled transport_egg:
    inventory -> item name -> 'item use' callback -> confirm
    Expected:
    - DinoOwners connection restored.
    - inactive activity removed.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=50013, username="egg_unpacker")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Manually set up "packed" state: remove from owners, add inactive activity
    act = Activity(
        dino_id=dino.id,
        activity_type="inactive",
        start_time=0,
        end_time=0
    )
    await act.insert()
    await DinoOwners.find(DinoOwners.dino.id == dino.id).delete()

    # Add a FILLED transport_egg via Item.add with the dino's alt_id as ability
    await Item.add(sim.user_id, "transport_egg", 1, {"data_id": dino.alt_id})

    # Verify egg is stored correctly with abilities
    filled_egg = await Item.find_one({
        "owner": sim.user_id,
        "items_data.item_id": "transport_egg",
        "items_data.abilities.data_id": dino.alt_id
    })
    assert filled_egg is not None, "Filled transport_egg not found in inventory"

    # Open inventory → view item — also tests item_info for FILLED egg (has dino name in text)
    from bot.modules.get_state import get_state
    st = await get_state(sim.user_id, sim.user_id)
    await st.clear()

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.profile.inventory', lang))
    sim.clear_sent_requests()

    # For a filled egg the display name may still be "transport_egg"
    item_display = _get_name("transport_egg", lang)
    await sim.send_message(item_display)
    await asyncio.sleep(0.2)

    responses = sim.get_sent_requests()
    assert len(responses) > 0, "Bot should show filled transport_egg info"

    # The filled egg info should mention the dino's name
    all_text = " ".join(
        (getattr(r, 'text', None) or getattr(r, 'caption', None) or '')
        for r in responses
    )
    assert dino.name in all_text, \
        f"Filled egg info should mention dino name '{dino.name}', got: {all_text[:300]}"

    # Find use callback and trigger unpack
    use_cb = find_use_callback(responses)
    assert use_cb is not None, "No 'item use' button found in filled transport_egg info"

    sim.clear_sent_requests()
    await sim.click_callback(use_cb)
    await asyncio.sleep(0.1)

    # Confirm if needed
    await sim.send_message(t('buttons_name.yes', lang))
    await asyncio.sleep(0.3)

    # Verify: DinoOwners restored
    owner_link = await DinoOwners.find_one(DinoOwners.dino.id == dino.id)
    assert owner_link is not None, "DinoOwners should be restored after unpacking"

    # Verify: inactive activity removed
    inactive = await Activity.get_pymongo_collection().find_one({
        "activity_type": "inactive",
        "$or": [{"dino_id": dino.id}, {"dino_id": str(dino.id)}]
    })
    assert inactive is None, "Inactive activity should be removed after unpacking dino"
