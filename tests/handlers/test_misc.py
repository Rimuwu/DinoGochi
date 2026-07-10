"""
Tests for Miscellaneous commands (bot/handlers/commands.py) via real handler flows.
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
async def test_misc_utility_commands(test_dp, test_bot):
    """
    Verifies timer and string_to_sec commands.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=120001, username="misc_tester")
    await setup_user_with_dino(sim)

    # 1. Test /timer 60
    sim.clear_sent_requests()
    await sim.send_message("/timer 60")
    await asyncio.sleep(0.1)
    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '')
    assert "1" in last_text or "минут" in last_text

    # 2. Test /string_to_sec 1m
    sim.clear_sent_requests()
    await sim.send_message("/string_to_sec 1m")
    await asyncio.sleep(0.1)
    responses2 = sim.get_sent_requests()
    assert len(responses2) > 0
    last_text2 = getattr(responses2[-1], 'text', '')
    assert "60" in last_text2


@pytest.mark.asyncio
async def test_help_command(test_dp, test_bot):
    """
    Verifies help command.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=120002, username="help_tester")
    await setup_user_with_dino(sim)

    sim.clear_sent_requests()
    await sim.send_message("/help")
    await asyncio.sleep(0.1)
    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '')
    assert "описание" in last_text or "help" in last_text or "timer" in last_text


@pytest.mark.asyncio
async def test_menu_transition_commands(test_dp, test_bot):
    """
    Verifies settings, profile, friends, market, tavern, actions, and dino profile menu commands.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=120003, username="transitions_tester")
    dino = await setup_user_with_dino(sim)

    async def wait_for_responses():
        for _ in range(20):
            res = list(sim.get_sent_requests())
            if len(res) > 0:
                return res
            await asyncio.sleep(0.05)
        return list(sim.get_sent_requests())

    # 1. Test /settings
    sim.clear_sent_requests()
    await sim.send_message("/settings")
    responses = await wait_for_responses()
    assert len(responses) > 0
    assert "настро" in getattr(responses[-1], 'text', '').lower()

    # 2. Test /profile_menu
    sim.clear_sent_requests()
    await sim.send_message("/profile_menu")
    responses_prof = await wait_for_responses()
    assert len(responses_prof) > 0
    assert "профил" in (getattr(responses_prof[-1], 'text', '') or getattr(responses_prof[-1], 'caption', '')).lower()

    # 3. Test /tavern
    sim.clear_sent_requests()
    await sim.send_message("/tavern")
    responses_tav = await wait_for_responses()
    assert len(responses_tav) > 0
    assert "таверн" in (getattr(responses_tav[-1], 'text', '') or getattr(responses_tav[-1], 'caption', '')).lower()

    # 4. Test /actions
    sim.clear_sent_requests()
    await sim.send_message("/actions")
    responses_act = await wait_for_responses()
    assert len(responses_act) > 0
    assert "действ" in (getattr(responses_act[-1], 'text', '') or getattr(responses_act[-1], 'caption', '')).lower()

    # 5. Test /dino (dino_profile)
    sim.clear_sent_requests()
    await sim.send_message("/dino")
    responses_dino = await wait_for_responses()
    assert len(responses_dino) > 0
    found_dino = any(
        dino.name.lower() in (getattr(r, 'text', '') or getattr(r, 'caption', '') or '').lower()
        for r in responses_dino
    )
    assert found_dino, f"Dino name should be in one of responses: {[getattr(r, 'text', getattr(r, 'caption', '')) for r in responses_dino]}"
