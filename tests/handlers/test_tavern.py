"""
Tests for Tavern handlers (bot/handlers/tavern.py) via real handler flows.
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
from bot.models.other import Event
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
async def test_events_list(test_dp, test_bot):
    """
    Verifies /events list.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=110001, username="events_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Clear events and insert one test event
    await Event.find_all().delete()
    test_event = Event(
        type="xp_boost",
        time_start=0,
        time_end=int(asyncio.get_event_loop().time() + 3600),
        data={"xp_boost": 0.5}
    )
    await test_event.insert()

    sim.clear_sent_requests()
    events_btn = t('commands_name.dino_tavern.events', lang)
    await sim.send_message(events_btn)
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '').lower()
    assert "xp_boost" in last_text or "опыт" in last_text or "увеличение" in last_text


@pytest.mark.asyncio
async def test_daily_award(test_dp, test_bot):
    """
    Verifies daily award display menu and reward claim callback.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=110002, username="daily_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # 1. View daily award info
    sim.clear_sent_requests()
    award_btn = t('commands_name.dino_tavern.daily_award', lang)
    await sim.send_message(award_btn)
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'caption', '') or getattr(responses[-1], 'text', '')
    assert "наград" in last_text or "daily_award" in last_text

    # 2. Trigger daily award callback
    from bot.handlers.tavern import daily_award
    from aiogram.types import CallbackQuery, User as TgUser, Message as TgMessage, Chat

    chat = Chat(id=sim.user_id, type="private")
    dummy_message = TgMessage(
        message_id=99999,
        date=12345,
        chat=chat,
        text="dummy"
    )
    dummy_message._bot = sim.bot

    callback = CallbackQuery(
        id="award_cb",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Tester"),
        chat_instance="inst",
        data="daily_award",
        message=dummy_message
    )
    callback._bot = sim.bot

    sim.clear_sent_requests()
    await daily_award(callback)
    await asyncio.sleep(0.1)

    # Award should be claimed or noted that it's already in base
    responses2 = sim.get_sent_requests()
    assert len(responses2) > 0
    last_text2 = getattr(responses2[-1], 'text', '')
    assert "base" in last_text2 or "Вы получили" in last_text2 or "наград" in last_text2 or "уже" in last_text2


@pytest.mark.asyncio
async def test_dino_edit_options(test_dp, test_bot):
    """
    Verifies tavern dino edit menus.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=110003, username="edit_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    edit_btn = t('commands_name.dino_tavern.edit', lang)
    await sim.send_message(edit_btn)
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'caption', '') or getattr(responses[-1], 'text', '')
    assert "Кузница" in last_text or "изменить" in last_text or "трансформация" in last_text or "Внешность" in last_text
