import os
import sys
import pytest
import asyncio
import time
from bson.objectid import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.simulator import BotSimulator
from bot.models.user import User
from bot.models.dinosaur import Dino, Egg
from bot.modules.localization import t, get_lang
from tests.handlers.test_general import register_and_incubate, boost_and_birth

from bot.models.activity import GameActivity, JourneyActivity
from bot.models.activity.training import TrainingActivity
from bot.modules.task_queue import is_task_scheduled
import bot.config

@pytest.mark.asyncio
async def test_game_activity_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40001, username="gamer_dino")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # Enable active tasks for scheduling checks
    old_active = bot.config.conf.active_tasks
    bot.config.conf.active_tasks = True

    try:
        # Start the game
        success = await GameActivity.start(dino.id, duration=1800, percent=1.0)
        assert success is True

        # 1. Verify tasks are scheduled at startup / check verify_tasks works
        await GameActivity.verify_tasks()
        res_id = f"game:{dino.id}"
        assert await is_task_scheduled(res_id) is True

        # 2. Check game progress ticks
        await Dino.mutate_stat(dino, 'game', -dino.stats['game'] + 50)
        
        from bot.tasks.game_check import game_process
        initial_game_stat = 50
        increased = False
        for _ in range(10):
            await game_process()
            d = await Dino.find_one(Dino.id == dino.id)
            if d.stats['game'] > initial_game_stat:
                increased = True
                break
        assert increased is True, "Dino game stat did not increase after game_process ticks"

        # 3. Check Game ends correctly and cancels task
        from bot.tasks.game_check import game_end_task
        await game_end_task({"dino_id": str(dino.id)})

        # Verify GameActivity is removed
        act = await GameActivity.find_one(GameActivity.dino.id == dino.id)
        assert act is None

        # Verify task is canceled
        assert await is_task_scheduled(res_id) is False
    finally:
        bot.config.conf.active_tasks = old_active


@pytest.mark.asyncio
async def test_training_overload_notifications(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40002, username="overloader")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # 1. Start Training (Gym)
    act_data = await TrainingActivity.start(
        dino.id,
        activity="gym",
        up="power",
        sec="dexterity",
        up_unit=[0.1, 0.2],
        sec_unit=[0.01, 0.02],
        sended=sim.user_id
    )
    assert act_data is not None

    # Retrieve Training activity from DB via Beanie
    skill_activ = await TrainingActivity.find_one(TrainingActivity.dino.id == dino.id)
    assert skill_activ is not None

    max_time = skill_activ.max_time
    
    # 2. Simulate overload >= 20%
    # We want dif_percent = 25.
    overload_start_time = int(time.time()) - (max_time + 25 * (max_time // 100))

    # Update in DB
    from bot.models.activity import Activity
    from bot.modules.overwriting.DataCalsses import LazyCollection
    long_activity = LazyCollection(Activity)

    await long_activity.update_one({'_id': skill_activ.id}, {
        '$set': {
            'start_time': overload_start_time,
            'last_check': int(time.time()) - 601
        }
    })

    # Clear sent messages
    sim.clear_sent_requests()

    # Call skills_work task
    from bot.tasks.skills import skills_work
    await skills_work()

    # 3. Verify warning notification was sent
    updated_act = await TrainingActivity.find_one(TrainingActivity.dino.id == dino.id)
    assert updated_act.ahtung_lvl == 1

    # Check that warning message was sent
    last_msg = sim.get_last_message_text()
    assert last_msg is not None
    assert "перегруз" in last_msg.lower() or "overload" in last_msg.lower()


@pytest.mark.asyncio
async def test_journey_choice_timeout_and_logs(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40003, username="journey_choices")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    lang = await get_lang(sim.user_id, "ru")

    # Enable active tasks for scheduling checks
    old_active = bot.config.conf.active_tasks
    bot.config.conf.active_tasks = True

    try:
        # Start a journey
        success = await JourneyActivity.start([dino.id], sim.user_id, duration=3600, location='forest')
        assert success is True

        journey = await JourneyActivity.find_one(JourneyActivity.sended == sim.user_id)
        assert journey is not None

        # Insert a custom choice event
        ev = {
            "tick_index": 1,
            "trigger_time": int(time.time()) - 10,
            "status": "pending",
            "type": "choice",
            "event_data": {
                "key": "riddle_chest",  # a valid choice event key from journey_choices
                "options_count": 2,
                "outcomes": [
                    {
                        "success": {"coins": 50, "dino_edit": {"heal": 10}},
                        "fail": {"heal": -10}
                    },
                    {
                        "success": {"heal": 10},
                        "fail": {"heal": -5}
                    }
                ]
            }
        }
        journey.pregenerated_events = [ev]
        await journey.save()

        # Clear sent messages
        sim.clear_sent_requests()

        # Trigger tick
        await JourneyActivity.process_journey_ticks(journey, int(time.time()))

        # Reload journey
        journey = await JourneyActivity.find_one(JourneyActivity.id == journey.id)
        active_ev = journey.pregenerated_events[0]
        
        # 1. Assert status is waiting_choice
        assert active_ev["status"] == "waiting_choice"

        # 2. Assert timeout is exactly 15 minutes (900 seconds) from trigger/activation time
        assert active_ev["timeout"] >= int(time.time()) + 890
        assert active_ev["timeout"] <= int(time.time()) + 910

        # 3. Resolve choice manually (Option 0)
        await JourneyActivity.resolve_choice_event(journey, active_ev, option_idx=0)

        # Reload journey to inspect logs/details
        journey = await JourneyActivity.find_one(JourneyActivity.id == journey.id)
        resolved_ev = journey.pregenerated_events[0]

        # Assert status is completed
        assert resolved_ev["status"] == "completed"

        # Verify outcome effect is in logs
        log_msg = await JourneyActivity.generate_event_message(resolved_ev, lang, journey.id)
        assert log_msg is not None
        assert "выбор" in log_msg.lower() or "choice" in log_msg.lower()
    finally:
        bot.config.conf.active_tasks = old_active
