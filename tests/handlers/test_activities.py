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

    # Try stopping work through message
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.skills_actions.stop_work', lang))
    
    # Verify confirmation text and button is sent
    last_msg = sim.get_last_message_text()
    assert t('all_skills.stoping.text', lang) in last_msg

    # Click callback "stop_work"
    sim.clear_sent_requests()
    await sim.click_callback("stop_work")
    await asyncio.sleep(0.3)

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

    # Test checking progress command
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.extraction_actions.progress', lang))
    last_msg = sim.get_last_message_text()
    # Check that progress bar exists in response
    assert "⌛" in last_msg or "[" in last_msg

    # Trigger progress callback check button (e.g. progress_work check {dino.alt_id})
    sim.clear_sent_requests()
    await sim.click_callback(f"progress_work check {dino.alt_id}")
    await asyncio.sleep(0.3)

    # Test stop work command
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.extraction_actions.stop_work', lang))
    await asyncio.sleep(0.3)

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


@pytest.mark.asyncio
async def test_journey_filters_and_panel(test_dp, test_bot):
    from bot.models.activity import JourneyActivity
    from aiogram.methods import SendMessage, SendPhoto

    sim = BotSimulator(test_dp, test_bot, user_id=30005, username="journeyer")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    user = await User.find_one(User.userid == sim.user_id)
    await user.update_last_dino(dino.id)

    lang = await get_lang(sim.user_id, "ru")
    journey_cmd = t("commands_name.actions.journey", lang)

    # 1. Initially idle: verify dispatch panel is displayed
    sim.clear_sent_requests()
    await sim.send_message(journey_cmd)

    requests = sim.get_sent_requests()
    idle_msg = next((r for r in reversed(requests) if isinstance(r, SendMessage)), None)
    assert idle_msg is not None
    assert idle_msg.reply_markup is not None

    # Check that it contains "j_send" and "j_hist:1" callback buttons
    buttons = []
    for row in idle_msg.reply_markup.inline_keyboard:
        for btn in row:
            buttons.append(btn.callback_data)
    assert "j_send" in buttons
    assert "j_hist:1" in buttons

    # 2. Start a journey manually
    success = await JourneyActivity.start([dino.id], sim.user_id, duration=1800, location='forest')
    assert success is True

    # 3. Verify active journey menu: should only show events and buttons related to this journey
    sim.clear_sent_requests()
    await sim.send_message(journey_cmd)

    requests = sim.get_sent_requests()
    active_photo = next((r for r in reversed(requests) if isinstance(r, SendPhoto)), None)
    assert active_photo is not None
    assert active_photo.reply_markup is not None

    active_buttons = []
    for row in active_photo.reply_markup.inline_keyboard:
        for btn in row:
            active_buttons.append(btn.callback_data)

    # Should contain j_stop and j_active_log
    has_stop = any("j_stop" in b for b in active_buttons)
    has_log = any("j_active_log" in b for b in active_buttons)
    assert has_stop is True
    assert has_log is True

    # Should NOT contain j_send or j_hist because dino is already in a journey
    assert "j_send" not in active_buttons
    assert "j_hist:1" not in active_buttons

    # 4. Trigger active_menu_callback (j_active_menu) and verify it keeps restriction
    sim.clear_sent_requests()
    await sim.click_callback("j_active_menu")

    requests = sim.get_sent_requests()
    # It edited the message
    # Let's inspect the last message or requests
    # Clear and clean up the journey
    journey = await JourneyActivity.find_one(JourneyActivity.sended == sim.user_id)
    assert journey is not None
    await JourneyActivity.end(journey.id)

    # 5. After ending journey, check that it goes back to idle dispatch panel
    sim.clear_sent_requests()
    await sim.send_message(journey_cmd)

    requests = sim.get_sent_requests()
    idle_msg_after = next((r for r in reversed(requests) if isinstance(r, SendMessage)), None)
    assert idle_msg_after is not None
    assert idle_msg_after.reply_markup is not None

    buttons_after = []
    for row in idle_msg_after.reply_markup.inline_keyboard:
        for btn in row:
            buttons_after.append(btn.callback_data)
    assert "j_send" in buttons_after
    assert "j_hist:1" in buttons_after


@pytest.mark.asyncio
async def test_collecting_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=30080, username="collector")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # Start collecting
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.actions.collecting', lang))
    await asyncio.sleep(0.1)

    # Choose "🌿 Поля"
    way_btn = t('collecting.buttons.collecting', lang)
    sim.clear_sent_requests()
    await sim.send_message(way_btn)
    await asyncio.sleep(0.1)

    # Enter count
    sim.clear_sent_requests()
    await sim.send_message("10")
    await asyncio.sleep(0.2)

    # Verify collecting started
    from bot.models.activity import CollectingActivity
    act = await CollectingActivity.find_one(CollectingActivity.dino.id == dino.id)
    assert act is not None

    # Stop collecting via callback stop
    sim.clear_sent_requests()
    await sim.click_callback(f"collecting stop {dino.alt_id}")
    await asyncio.sleep(0.3)

    # Verify activity was stopped
    act_after = await CollectingActivity.find_one(CollectingActivity.dino.id == dino.id)
    assert act_after is None

    # Verify that the end_collecting notification was sent
    sent_requests = sim.get_sent_requests()
    has_end_msg = any(r.__class__.__name__ == 'SendMessage' and "закончил сбор пищи" in r.text for r in sent_requests)
    assert has_end_msg is True, "Should receive end_collecting notification even if no items gathered"


@pytest.mark.asyncio
async def test_dino_set_status_signatures(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=30090, username="statustester")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    from bot.models.dinosaur import Dino, DinoStatus
    from bot.models.activity import SleepActivity

    # Start sleep activity
    await SleepActivity.start(dino.id, 'short')
    db_dino = await Dino.find_one(Dino.id == dino.id)
    assert await db_dino.status == DinoStatus.SLEEP

    # Test classmethod style call to end sleep: Dino.set_status(dino_id, DinoStatus.PASS)
    await Dino.set_status(dino.id, DinoStatus.PASS)
    db_dino = await Dino.find_one(Dino.id == dino.id)
    assert await db_dino.status == DinoStatus.PASS

    # Start sleep activity again
    await SleepActivity.start(dino.id, 'short')
    db_dino = await Dino.find_one(Dino.id == dino.id)
    assert await db_dino.status == DinoStatus.SLEEP

    # Test instance style call to end sleep: dino.set_status(DinoStatus.PASS)
    await db_dino.set_status(DinoStatus.PASS)
    db_dino_after = await Dino.find_one(Dino.id == dino.id)
    assert await db_dino_after.status == DinoStatus.PASS



