import os
import sys
# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from tests.simulator import BotSimulator
from bot.models.user import User, Lang
from bot.models.dinosaur import Egg, Dino, DinoOwners
from aiogram.methods import SendMessage, SendPhoto, AnswerCallbackQuery, EditMessageMedia
from bot.modules.localization import t, get_lang

# --- Helper Methods for Stage Reusability ---

async def register_and_incubate(sim: BotSimulator) -> Egg:
    """Helper method to run start-game flow up to egg incubation."""
    # Step 1: Send /start
    sim.clear_sent_requests()
    await sim.send_message("/start")

    # Step 2: Click "🍡 Начать играть"
    sim.clear_sent_requests()
    lang = await get_lang(sim.user_id, "ru")
    start_game_cmd = t("commands_name.start_game", lang)
    await sim.send_message(start_game_cmd)

    # Retrieve the latest SendPhoto request to extract egg selection inline data
    requests = sim.get_sent_requests()
    photo_request = next((r for r in reversed(requests) if isinstance(r, SendPhoto)), None)
    assert photo_request is not None, "Egg selection photo request was not sent"
    
    reply_markup = photo_request.reply_markup
    assert reply_markup is not None
    egg_callback_data = reply_markup.inline_keyboard[0][0].callback_data
    assert egg_callback_data.startswith("start_egg")

    # Step 3: Choose egg
    sim.clear_sent_requests()
    await sim.click_callback(egg_callback_data)

    # Return the incubated egg from database
    db_egg = await Egg.find_one(Egg.owner_id == sim.user_id)
    assert db_egg is not None, "Egg not found in database"
    assert db_egg.stage == "incubation"
    return db_egg


async def boost_and_birth(sim: BotSimulator, egg: Egg) -> Dino:
    """Helper method to run free egg incubation boost and birth of the dinosaur."""
    # Click the "⚡ Ускорить вылупление" button
    sim.clear_sent_requests()
    await sim.click_callback(f"free_egg_boost {egg.id}")

    # Verify egg is deleted from database
    deleted_egg = await Egg.find_one(Egg.owner_id == sim.user_id)
    assert deleted_egg is None, "Egg was not deleted from database after boost"

    # Verify a new dinosaur is born and linked to the owner in the database
    owner_conn = await DinoOwners.find_one(DinoOwners.owner_id == sim.user_id)
    assert owner_conn is not None, "Dino owner connection was not created in database"

    dino = await Dino.find_one(Dino.id == owner_conn.dino.ref.id)
    assert dino is not None, "Dinosaur record not found in database"
    return dino


# --- Integration Tests ---

@pytest.mark.asyncio
async def test_start_game_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=12345, username="tester_bob")
    
    # Run helper to register and start incubation
    db_egg = await register_and_incubate(sim)
    assert db_egg.free_boost is True

    # Check that user is in DB
    db_user = await User.find_one(User.userid == 12345)
    assert db_user is not None


@pytest.mark.asyncio
async def test_egg_boost_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=54321, username="booster_bob")
    
    # 1. Register and Incubate
    egg = await register_and_incubate(sim)
    
    # 2. Boost and Birth
    dino = await boost_and_birth(sim, egg)
    assert dino is not None
    print(f"Dinosaur successfully born via boost: {dino.alt_id}")


@pytest.mark.asyncio
async def test_dino_menu_and_inline_buttons(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=98765, username="menu_tester")

    # 1. Prepare dinosaur by running registration and boost stages
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    # 2. Open dinosaur profile menu by sending the "🦖 Динозавр" keyboard button command (fetched from localization)
    sim.clear_sent_requests()
    lang = await get_lang(sim.user_id, "ru")
    dino_profile_cmd = t("commands_name.dino_profile", lang)
    await sim.send_message(dino_profile_cmd)

    requests = sim.get_sent_requests()
    assert len(requests) > 0, "No response after requesting profile"

    # Find profile photo message
    profile_photo_req = next((r for r in reversed(requests) if isinstance(r, SendPhoto)), None)
    assert profile_photo_req is not None, "Profile photo message was not sent"
    assert profile_photo_req.reply_markup is not None, "Profile message has no inline buttons"

    inline_keyboard = profile_photo_req.reply_markup.inline_keyboard
    assert len(inline_keyboard) > 0, "Inline keyboard is empty"

    # 3. Simulate clicking every inline button in the dinosaur profile menu
    combat_callback_data = None
    for row in inline_keyboard:
        for button in row:
            callback_data = button.callback_data
            assert callback_data is not None

            if "combat" in callback_data:
                combat_callback_data = callback_data

            print(f"Testing dinosaur profile button: '{button.text}' -> callback: '{callback_data}'")
            sim.clear_sent_requests()
            await sim.click_callback(callback_data)

            # Verify that clicking the button produces some response
            button_responses = sim.get_sent_requests()
            assert len(button_responses) > 0, f"Dino profile button '{button.text}' ({callback_data}) did not return any bot response!"

    # 4. Deep Test: Click the Combat menu option and test all its sub-buttons
    assert combat_callback_data is not None, "Combat button was not found in inline keyboard"
    sim.clear_sent_requests()
    await sim.click_callback(combat_callback_data)

    combat_responses = sim.get_sent_requests()
    combat_menu_req = next((r for r in reversed(combat_responses) if isinstance(r, EditMessageMedia)), None)
    assert combat_menu_req is not None, "Combat parameters sub-menu was not updated via EditMessageMedia"
    assert combat_menu_req.reply_markup is not None, "Combat sub-menu has no inline buttons"

    combat_keyboard = combat_menu_req.reply_markup.inline_keyboard
    assert len(combat_keyboard) > 0, "Combat inline keyboard is empty"

    for row in combat_keyboard:
        for button in row:
            callback_data = button.callback_data
            assert callback_data is not None

            print(f"Testing combat menu button: '{button.text}' -> callback: '{callback_data}'")
            sim.clear_sent_requests()
            await sim.click_callback(callback_data)

            # Verify response
            resps = sim.get_sent_requests()
            assert len(resps) > 0, f"Combat menu button '{button.text}' ({callback_data}) did not return any bot response!"


@pytest.mark.asyncio
async def test_premium_kindergarten_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=88888, username="premium_bob")

    # 1. Prepare dinosaur
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None

    # 2. Grant premium to the user in database
    from bot.models.user import Subscription
    await Subscription.award_premium(sim.user_id, "inf")

    # Verify user now has premium
    db_user = await User.find_one(User.userid == sim.user_id)
    assert await db_user.premium is True, "User premium status not updated"

    # 3. Open profile and request Kindergarten
    sim.clear_sent_requests()
    lang = await get_lang(sim.user_id, "ru")
    dino_profile_cmd = t("commands_name.dino_profile", lang)
    await sim.send_message(dino_profile_cmd)

    # Click "🏡 Детский сад (⭐)" button (callback: 'dino_menu kindergarten {dino.alt_id}')
    await sim.click_callback(f"dino_menu kindergarten {dino.alt_id}")

    # Check response offers the start button
    requests = sim.get_sent_requests()
    msg_req = next((r for r in reversed(requests) if isinstance(r, SendMessage)), None)
    assert msg_req is not None, "Kindergarten info message not sent"
    
    inline_kb = msg_req.reply_markup.inline_keyboard
    start_button_data = inline_kb[0][0].callback_data
    assert start_button_data == f"kindergarten start {dino.alt_id}"

    # 4. Click start button to trigger duration selection FSM
    sim.clear_sent_requests()
    await sim.click_callback(start_button_data)

    # 5. Send hour option "1 час" (simulating reply keyboard selection)
    hour_str = f"1 {t('time_format.hour.0', lang)}"
    sim.clear_sent_requests()
    await sim.send_message(hour_str)

    # Verify confirmation text
    last_msg = sim.get_last_message_text()
    assert t("kindergarten.ok", lang) in last_msg, f"Expected ok notification, got: {last_msg}"

    # Verify dinosaur status is now "kindergarten"
    from bot.models.enums import DinoStatus
    dino_status = await Dino.check_status_by_id(dino.id)
    assert dino_status == DinoStatus.KINDERGARTEN, f"Expected dino status kindergarten, got: {dino_status}"

    # 6. Stop/Retrieve from kindergarten
    sim.clear_sent_requests()
    await sim.send_message(dino_profile_cmd)
    
    # Click "🏡 Детский сад (⭐)" button again
    await sim.click_callback(f"dino_menu kindergarten {dino.alt_id}")
    
    # Check stop button callback is present
    requests = sim.get_sent_requests()
    msg_req = next((r for r in reversed(requests) if isinstance(r, SendMessage)), None)
    assert msg_req is not None
    inline_kb = msg_req.reply_markup.inline_keyboard
    stop_button_data = inline_kb[0][0].callback_data
    assert stop_button_data == f"kindergarten stop {dino.alt_id}"

    # Click stop button
    sim.clear_sent_requests()
    await sim.click_callback(stop_button_data)

    # Verify dinosaur status returned to "pass"
    dino_status = await Dino.check_status_by_id(dino.id)
    assert dino_status == DinoStatus.PASS, f"Expected dino status pass after stop, got: {dino_status}"


@pytest.mark.asyncio
async def test_non_premium_kindergarten_flow(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=99999, username="standard_bob")

    # 1. Prepare dinosaur
    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)
    assert dino is not None


    # 2. Open profile and request Kindergarten
    sim.clear_sent_requests()
    lang = await get_lang(sim.user_id, "ru")
    dino_profile_cmd = t("commands_name.dino_profile", lang)
    await sim.send_message(dino_profile_cmd)

    # Click "🏡 Детский сад (⭐)" button
    await sim.click_callback(f"dino_menu kindergarten {dino.alt_id}")

    # Check response text is "no_premium"
    last_msg = sim.get_last_message_text()
    assert t("no_premium", lang) in last_msg, f"Expected no_premium notification, got: {last_msg}"

    # Verify no start/stop button is present in markup
    requests = sim.get_sent_requests()
    msg_req = next((r for r in reversed(requests) if isinstance(r, SendMessage)), None)
    assert msg_req is not None
    assert msg_req.reply_markup is None or getattr(msg_req.reply_markup, "inline_keyboard", []) == []


# @pytest.mark.asyncio
# async def test_backgrounds_flow(test_dp, test_bot):
#     sim = BotSimulator(test_dp, test_bot, user_id=11111, username="bg_tester")

#     egg = await register_and_incubate(sim)
#     dino = await boost_and_birth(sim, egg)
#     assert dino is not None

#     lang = await get_lang(sim.user_id, "ru")

#     # 1. Custom background without premium should fail
#     sim.clear_sent_requests()
#     await sim.send_message(t('commands_name.backgrounds.custom_profile', lang))
#     last_msg = sim.get_last_message_text()
#     assert t('no_premium', lang) in last_msg, f"Expected no_premium error, got: {last_msg}"

#     # Grant premium
#     from bot.models.user import Subscription
#     await Subscription.award_premium(sim.user_id, "inf")

#     # Custom background with premium should prompt to choose dinosaur (or directly prompt for image if only 1 dino exists)
#     sim.clear_sent_requests()
#     await sim.send_message(t('commands_name.backgrounds.custom_profile', lang))
#     last_msg = sim.get_last_message_text()
#     assert "изображение" in last_msg.lower() or "dino" in last_msg.lower()

#     # 2. View all backgrounds
#     sim.clear_sent_requests()
#     await sim.send_message(t('commands_name.backgrounds.backgrounds', lang))
    
#     # Check page 1 is displayed
#     last_msg = sim.get_last_message_text()
#     assert "№ 1" in last_msg

#     # Click Right arrow to go to page 2 (callback: 'back_m page 2')
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m page 2")
#     last_msg = sim.get_last_message_text()
#     assert "№ 2" in last_msg

#     # Click page number button (callback: 'back_m page_n 2')
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m page_n 2")
#     last_msg = sim.get_last_message_text()
#     assert t('backgrounds.page', lang) in last_msg

#     # Send page number "3"
#     sim.clear_sent_requests()
#     await sim.send_message("3")
#     last_msg = sim.get_last_message_text()
#     assert "№ 3" in last_msg

#     # Try buying without coins (callback: 'back_m buy_coins 3')
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m buy_coins 3")
#     # Click confirm callback (confirm_text is buttons_name.confirm)
#     confirm_text = t('buttons_name.confirm', lang)
#     sim.clear_sent_requests()
#     await sim.send_message(confirm_text)
#     last_msg = sim.get_last_message_text()
#     assert t('backgrounds.no_coins', lang) in last_msg

#     # Add coins
#     user = await User.find_one(User.userid == sim.user_id)
#     await user.add_coins(10000)

#     # Buy with coins again
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m buy_coins 3")
#     sim.clear_sent_requests()
#     await sim.send_message(confirm_text)
#     last_msg = sim.get_last_message_text()
#     assert t('backgrounds.buy', lang) in last_msg

#     # Check background 3 in inventory
#     user = await User.find_one(User.userid == sim.user_id)
#     assert 3 in user.saved.get('backgrounds', [])

#     # Try buying page 4 with super coins (no super coins first)
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m buy_super_coins 4")
#     sim.clear_sent_requests()
#     await sim.send_message(confirm_text)
#     last_msg = sim.get_last_message_text()
#     assert t('backgrounds.no_coins', lang) in last_msg

#     # Add super coins
#     await user.update({'$set': {'super_coins': 20}})

#     # Buy with super coins
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m buy_super_coins 4")
#     sim.clear_sent_requests()
#     await sim.send_message(confirm_text)
#     last_msg = sim.get_last_message_text()
#     assert t('backgrounds.buy', lang) in last_msg

#     # Check background 4 in inventory
#     user = await User.find_one(User.userid == sim.user_id)
#     assert 4 in user.saved.get('backgrounds', [])

#     # Set background 3 on dinosaur (ChooseDinoHandler auto-selects the only dino)
#     sim.clear_sent_requests()
#     await sim.click_callback("back_m set 3")
#     last_msg = sim.get_last_message_text()
#     assert t('backgrounds.set', lang) in last_msg

#     # Check dino profile background is set to saved 3
#     from bot.models.dinosaur import Dino
#     db_dino = await Dino.find_one(Dino.id == dino.id)
#     assert db_dino.profile.get('background_type') == 'saved'
#     assert db_dino.profile.get('background_id') == 3

#     # Reset standard background (ChooseDinoHandler auto-selects the only dino)
#     sim.clear_sent_requests()
#     await sim.send_message(t('commands_name.backgrounds.standart', lang))
#     last_msg = sim.get_last_message_text()
#     assert t('standart_background', lang) in last_msg

#     db_dino = await Dino.find_one(Dino.id == dino.id)
#     assert db_dino.profile.get('background_type') == 'standart'
#     assert db_dino.profile.get('background_id') == 0

