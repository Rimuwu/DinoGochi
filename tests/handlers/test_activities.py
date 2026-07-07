import os
import sys
# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import asyncio
from bson.objectid import ObjectId
from tests.simulator import BotSimulator
from bot.models.user import User
from bot.models.dinosaur import Dino, Egg
from bot.modules.localization import t, get_lang
from tests.handlers.test_general import register_and_incubate, boost_and_birth

@pytest.mark.asyncio
async def test_active_dino_change(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=20001, username="dino_changer")
    egg = await register_and_incubate(sim)
    dino1 = await boost_and_birth(sim, egg)
    assert dino1 is not None

    # Insert a second dinosaur manually in database
    from bot.models.dinosaur import DinoOwners
    dino2 = Dino(
        data_id=11888,
        name="SecondDino",
        alt_id="20001_secondDino",
        quality="com",
        stats={'heal': 100, 'eat': 80, 'game': 80, 'mood': 80, 'energy': 80, 'power': 1.0, 'dexterity': 1.0, 'intelligence': 1.0, 'charisma': 1.0}
    )
    await dino2.insert()
    await DinoOwners.create_connection(dino2.id, sim.user_id)

    lang = await get_lang(sim.user_id, "ru")
    
    # Verify current last_dino is dino1
    user = await User.find_one(User.userid == sim.user_id)
    active_dino = await user.get_last_dino()
    assert active_dino.id == dino1.id

    # Switch active dinosaur using callback
    sim.clear_sent_requests()
    await sim.click_callback(f"activ_dino {dino2.alt_id}")
    
    # Check that successful change text is in message
    last_msg = sim.get_last_message_text()
    assert t('edit_dino_button.susseful', lang, name=dino2.name) in last_msg
    
    # Reload user and check updated active dino
    user = await User.find_one(User.userid == sim.user_id)
    active_dino = await user.get_last_dino()
    assert active_dino.id == dino2.id


@pytest.mark.asyncio
async def test_speed_actions_and_busy(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=20002, username="speedy")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # Perform speed actions 10 times to test random branch paths
    for _ in range(10):
        # We clean database keys and KDActivity in clean_db so we manually delete KD here to run in loop
        from bot.models.activity import KDActivity
        await KDActivity.find(KDActivity.dino.id == dino.id).delete()

        sim.clear_sent_requests()
        await sim.send_message(t('commands_name.speed_actions.pet', lang))
        
        sim.clear_sent_requests()
        await sim.send_message(t('commands_name.speed_actions.talk', lang))

        # Check mood/stats update or that text was sent
        last_msg = sim.get_last_message_text()
        assert last_msg is not None

    # Test occupation: if dinosaur becomes busy (e.g., in sleep), speed actions should fail
    from bot.models.activity import SleepActivity
    await SleepActivity.start(dino.id, 'long')

    # Try pet when busy
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.speed_actions.pet', lang))
    last_msg = sim.get_last_message_text()
    assert t('alredy_busy', lang) in last_msg or "занят" in last_msg.lower()

    # Clean up activity
    await SleepActivity.end(dino.id)


@pytest.mark.asyncio
async def test_training_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=20003, username="trainer")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # Start Gym Training
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.skills_actions.gym', lang))
    
    # Retrieve send_message for choosing energy/booster
    requests = sim.get_sent_requests()
    assert len(requests) > 0
    # Click use energy option (e.g. callback "use_energy gym")
    sim.clear_sent_requests()
    await sim.click_callback("use_energy gym")
    
    # Verify training has started
    from bot.models.activity.training import TrainingActivity
    act = await TrainingActivity.find_one(TrainingActivity.dino.id == dino.id)
    assert act is not None
    assert act.activity_type == "gym"

    # Verify already busy when attempting pool
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.skills_actions.swimming_pool', lang))
    last_msg = sim.get_last_message_text()
    assert t('alredy_busy', lang) in last_msg

    # End training directly
    await TrainingActivity.end(dino.id)

    # Verify training completed and dino is free
    act = await TrainingActivity.find_one(TrainingActivity.dino.id == dino.id)
    assert act is None


@pytest.mark.asyncio
async def test_works_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=20004, username="worker")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # Send to mine work
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.extraction_actions.mine', lang))
    
    # Choose coins option from reply menu
    sim.clear_sent_requests()
    await sim.send_message(t('works.buttons.coins', lang))

    # Verify work started
    from bot.models.activity.work import WorkActivity
    act = await WorkActivity.find_one(WorkActivity.dino.id == dino.id)
    assert act is not None

    # Verify already busy when attempting saw mill
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.extraction_actions.sawmill', lang))
    last_msg = sim.get_last_message_text()
    assert t('alredy_busy', lang) in last_msg

    # End work directly
    await WorkActivity.end_work(dino.id)

    # Verify work finished
    act = await WorkActivity.find_one(WorkActivity.dino.id == dino.id)
    assert act is None


@pytest.mark.asyncio
async def test_life_actions_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=20005, username="lifestyler")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")
    user = await User.find_one(User.userid == sim.user_id)

    # 1. Feed Dino
    # Give some items first
    await user.add_item("pizza", 5)
    
    # Trigger feeding menu (commands_name.actions.feed)
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.actions.feed', lang))
    
    # We should have pizza in keyboard, click it
    # Callback is usually like "inventory food pizza" or similar
    # Let's find food item callback
    requests = sim.get_sent_requests()
    callback_data = None
    for r in requests:
        if hasattr(r, "reply_markup") and r.reply_markup and hasattr(r.reply_markup, 'inline_keyboard'):
            for row in r.reply_markup.inline_keyboard:
                for btn in row:
                    if "food" in btn.callback_data or "pizza" in btn.callback_data:
                        callback_data = btn.callback_data
                        break
    
    if callback_data:
        sim.clear_sent_requests()
        await sim.click_callback(callback_data)

    from bot.models.activity import SleepActivity
    res_sleep = await SleepActivity.start(dino.id, 'short')
    assert res_sleep is True, f"Failed to start sleep activity: {res_sleep}"

    print("DEBUG: SleepActivity.dino.id =", SleepActivity.dino.id)
    print("DEBUG: type =", type(SleepActivity.dino.id))
    print("DEBUG: is_link =", getattr(getattr(SleepActivity.dino.id, '_field_resolution', None), 'is_link', None))
    act = await SleepActivity.find_one(SleepActivity.dino.id == dino.id)
    assert act is not None

    # Tick sleep task
    from bot.tasks.sleep import short_check, check_notification as check_sleep_notification
    await short_check()
    
    # End sleep directly
    await SleepActivity.end(dino.id)

    # Sleep finished
    act = await SleepActivity.find_one(SleepActivity.dino.id == dino.id)
    assert act is None
