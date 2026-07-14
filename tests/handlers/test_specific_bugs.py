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
    assert "перегруж" in last_msg.lower() or "overload" in last_msg.lower()


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

        journey = await JourneyActivity.find_one(JourneyActivity.userid == sim.user_id)
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


@pytest.mark.asyncio
async def test_dead_check_ignoring_self(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40004, username="dead_checker_test")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    # Check dead_check without ignoring (should be False because we have a dino)
    is_dead = await Dino.dead_check(sim.user_id)
    assert is_dead is False

    # Check dead_check with ignoring the dino (should be True because it's our only dino)
    is_dead_ignored = await Dino.dead_check(sim.user_id, ignore_dino_id=dino.id)
    assert is_dead_ignored is True


@pytest.mark.asyncio
async def test_dino_dead_notification_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40005, username="notification_dead_tester")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    # Clear bot sent requests
    test_bot.sent_requests.clear()

    # Kill the dino (calling dead() method)
    await dino.dead()

    # The dino must be deleted
    deleted_dino = await Dino.find(Dino.id == dino.id).first_or_none()
    assert deleted_dino is None

    # Verify that not_independent_dead notification was sent because user level is 1 (<= dead_dialog_max_lvl)
    # The notification key 'not_independent_dead' should have been formatted and sent.
    # In Russian it is: "❤ К сожалению... ваш динозаврик *Torvosaurus*... умер...\n\n✉ | Вам электронное письмо от организации. Откройте его."
    # Let's inspect test_bot.sent_requests
    sent_msgs = [req.text for req in test_bot.sent_requests if hasattr(req, 'text')]
    assert any("письмо от организации" in msg or "email from the organization" in msg for msg in sent_msgs)


@pytest.mark.asyncio
async def test_cannot_feed_dino_on_journey(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40006, username="journey_feeder")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    user = await User.find_one(User.userid == sim.user_id)
    await user.add_item("pizza", 5)

    # 1. Put dino on a journey
    from bot.models.activity import JourneyActivity
    success = await JourneyActivity.start([dino.id], sim.user_id, duration=3600, location='forest')
    assert success is True

    # Dino status should now be 'journey'
    dino_status = await dino.status
    assert dino_status == 'journey'

    # 2. Try to feed pizza via use_item
    from bot.modules.items.item_tools import use_item
    from bot.models.items import Item
    
    # We pass delete=True, if it works it would reduce pizza count
    send_status, return_text = await use_item(sim.user_id, sim.user_id, "ru", {'item_id': 'pizza'}, count=1, dino=dino)
    assert send_status is True
    assert "путешествия" in return_text

    # Pizza count should still be 5 because feeding was blocked!
    user_pizza = await Item.find_one(Item.owner == user.userid, Item.items_data.item_id == "pizza")
    assert user_pizza is not None
    assert user_pizza.count == 5


@pytest.mark.asyncio
async def test_dino_kindergarten_task(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=40007, username="kindergarten_task_test")
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    from bot.models.activity import Kindergarten
    from bot.models.enums import DinoStatus
    from bot.tasks.data_reupdat import dino_kindergarten
    import time

    # Set dino status to kindergarten and insert expired Kindergarten entry
    await Dino.set_status(dino.id, DinoStatus.KINDERGARTEN)
    
    k_entry = Kindergarten(
        userid=sim.user_id,
        type="dino",
        start=int(time.time()) - 3600,
        end=int(time.time()) - 100, # expired
        dino=dino
    )
    await k_entry.insert()

    # Clear sent requests to check user notifications
    test_bot.sent_requests.clear()

    # Run background task, it should not raise KeyError and should complete successfully
    await dino_kindergarten()

    # Dino status should be updated back to PASS
    updated_dino = await Dino.find_one(Dino.id == dino.id)
    assert await updated_dino.status == DinoStatus.PASS

    # Kindergarten entry should be deleted
    k_check = await Kindergarten.find_one(Kindergarten.dino.id == dino.id)
    assert k_check is None

    # Notification should have been sent to user
    sent_msgs = [req.text for req in test_bot.sent_requests if hasattr(req, 'text')]
    assert any("садик" in msg.lower() or "kindergarten" in msg.lower() for msg in sent_msgs)


@pytest.mark.asyncio
async def test_create_product_items_items_no_trade_col_keyerror(test_dp, test_bot):
    from bot.modules.add_product.items_items import stock, stock_adapter
    from unittest import mock
    
    return_data = {
        'trade_items': [
            {'item_id': 'pizza', 'count': 3},
            {'item_id': 'apple', 'count': 5}
        ]
    }
    
    transmitted_data = {
        'chatid': 12345,
        'userid': 12345,
        'lang': 'ru',
        'option': 'items_items',
        'items': [{'item_id': 'amber', 'count': 1}],
        'col': [1]
    }

    # 1. Calling stock should extract counts and populate trade_col
    await stock(return_data, transmitted_data)

    assert 'trade_col' in transmitted_data
    assert transmitted_data['trade_col'] == [3, 5]
    # Counts should have been popped from items to match single-item selection logic
    assert transmitted_data['trade_items'][0].get('count') is None
    assert transmitted_data['trade_items'][1].get('count') is None

    # 2. Mock 'end' function and call stock_adapter to verify price list construction
    with mock.patch('bot.modules.add_product.items_items.end') as mock_end:
        await stock_adapter(in_stock=2, transmitted_data=transmitted_data)
        mock_end.assert_called_once()
        called_return_data, called_transmitted_data = mock_end.call_args[0]
        assert len(called_return_data['price']) == 8
        assert called_return_data['price'].count({'item_id': 'pizza'}) == 3
        assert called_return_data['price'].count({'item_id': 'apple'}) == 5
        assert called_return_data['in_stock'] == 2



