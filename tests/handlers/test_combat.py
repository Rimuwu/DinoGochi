"""
Tests for Combat (bot/handlers/combat.py) via real handler flows.
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
async def test_combat_commands(test_dp, test_bot):
    """
    Verifies /test_combat and /test_mob_combat commands.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=100001, username="combat_tester")
    await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    # Command 1: /test_combat 1
    sim.clear_sent_requests()
    await sim.send_message("/test_combat 1")
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '') or getattr(responses[-1], 'caption', '')
    assert "Автобой завершен" in last_text or "winner" in last_text or "Ничья" in last_text

    # Command 2: /test_mob_combat 1 1
    sim.clear_sent_requests()
    await sim.send_message("/test_mob_combat 1 1")
    await asyncio.sleep(0.1)

    responses_mob = sim.get_sent_requests()
    assert len(responses_mob) > 0
    last_text_mob = getattr(responses_mob[-1], 'text', '') or getattr(responses_mob[-1], 'caption', '')
    assert "завершен" in last_text_mob or "winner" in last_text_mob


@pytest.mark.asyncio
async def test_combat_log_view_and_delete(test_dp, test_bot):
    """
    Verifies combat log viewing, navigation and deletion callbacks.
    """
    sim = BotSimulator(test_dp, test_bot, user_id=100002, username="combat_log_tester")
    dino = await setup_user_with_dino(sim)
    lang = await get_lang(sim.user_id, "ru")

    from bot.redismanager import redis_set
    from bot.handlers.combat import combat_log_view_call, delete_combat_log

    # 1. Create a dummy combat log entry in Redis
    battle_id = "combat_test_battle_123"
    redis_key = f"combat_log:{battle_id}"
    dummy_log = {
        "winner": "X",
        "reason_key": "combat_log.reasons.all_enemies_dead",
        "starting_data": {
            "X": [{"name": "MyDino", "max_hp": 100, "hp": 100, "role": "carry"}],
            "Y": [{"name": "EnemyDino", "max_hp": 80, "hp": 0, "role": "carry"}]
        },
        "rounds": {
            1: ["MyDino hits EnemyDino for 80 damage!"]
        },
        "loot": ["bone_sword"]
    }
    await redis_set(redis_key, dummy_log, ex=3600)

    # 2. Trigger combat_log_view callback query
    from aiogram.types import Chat, Message as TgMessage, CallbackQuery, User as TgUser
    chat = Chat(id=sim.user_id, type="private")
    dummy_message = TgMessage(
        message_id=99999,
        date=12345,
        chat=chat,
        text="dummy"
    )
    dummy_message._bot = sim.bot

    callback_view = CallbackQuery(
        id="view_cb",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Tester"),
        chat_instance="inst",
        data=f"combat_log_view {redis_key} 0 {dino.id}",
        message=dummy_message
    )
    callback_view._bot = sim.bot

    sim.clear_sent_requests()
    await combat_log_view_call(callback_view)
    await asyncio.sleep(0.1)

    responses = sim.get_sent_requests()
    assert len(responses) > 0
    last_text = getattr(responses[-1], 'text', '') or getattr(responses[-1], 'caption', '')
    assert "MyDino" in last_text

    # 3. Trigger delete_combat_log callback query
    callback_del = CallbackQuery(
        id="delete_cb",
        from_user=TgUser(id=sim.user_id, is_bot=False, first_name="Tester"),
        chat_instance="inst",
        data=f"cld {battle_id} {dino.id}",
        message=dummy_message
    )
    callback_del._bot = sim.bot

    sim.clear_sent_requests()
    await delete_combat_log(callback_del)
    await asyncio.sleep(0.1)

    # Verify callback returned success answer
    # (Checking redis key is deleted is secondary, but checking callback executed without crash is key)
    from bot.redismanager import redis_get
    redis_val = await redis_get(redis_key)
    assert redis_val is None, "Log should be deleted from Redis"
