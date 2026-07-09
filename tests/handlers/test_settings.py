import os
import sys
import re
# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import asyncio
from tests.simulator import BotSimulator
from tests.handlers.test_general import register_and_incubate, boost_and_birth
from bot.models.user import User, Lang
from bot.modules.localization import t, get_lang, get_all_locales, get_data
from bot.modules.markup import tranlate_data

@pytest.fixture
async def prep_user(test_dp, test_bot):
    """Fixture to register a user for settings tests."""
    sim = BotSimulator(test_dp, test_bot, user_id=77777, username="settings_tester")
    # Quick insert of user and language document in DB to authorize them in Russian
    user = User(userid=77777, name="Settings Tester")
    await user.insert()
    
    lang_doc = Lang(userid=77777, lang="ru")
    await lang_doc.insert()
    return sim

@pytest.mark.asyncio
async def test_settings_notification(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")
    
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.notification', lang))

    # Respond to ChooseConfirmHandler with 'enable'
    btn_text = t('buttons_name.enable', lang)
    sim.clear_sent_requests()
    await sim.send_message(btn_text)

    # Verify settings updated in DB
    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.settings.get('notifications') is True


@pytest.mark.asyncio
async def test_settings_dino_profile(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")
    
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.dino_profile', lang))

    # Choose first option from profile_view.ans
    options = get_data('profile_view.ans', lang)
    option_choice = options[0]
    
    sim.clear_sent_requests()
    await sim.send_message(option_choice)

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.settings.get('profile_view') == 1


@pytest.mark.asyncio
async def test_settings_inv_sort(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.inv_sort', lang))

    options = get_data('inv_sort.ans', lang)
    option_choice = options[0]

    sim.clear_sent_requests()
    await sim.send_message(option_choice)

    db_user = await User.find_one(User.userid == sim.user_id)
    keys_list = get_data('inv_sort.keys', lang)
    assert db_user.settings.get('inv_sort') == keys_list[0]


@pytest.mark.asyncio
async def test_settings_inventory(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.inventory', lang))

    options = get_data('inv_set_pages.data', lang)
    option_choice = options[0]

    sim.clear_sent_requests()
    await sim.send_message(option_choice)

    db_user = await User.find_one(User.userid == sim.user_id)
    expected_list = list(int(strn) for strn in option_choice.split(' | '))
    assert db_user.settings.get('inv_view') == expected_list


@pytest.mark.asyncio
async def test_settings_rename_dino(test_dp, test_bot):
    sim = BotSimulator(test_dp, test_bot, user_id=77778, username="rename_tester")
    # Quick insert of language document to authorize user in Russian
    lang_doc = Lang(userid=77778, lang="ru")
    await lang_doc.insert()

    egg = await register_and_incubate(sim)
    dino = await boost_and_birth(sim, egg)

    lang = await get_lang(sim.user_id, "ru")
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.dino_name', lang))

    # Click the callback for the dino selection
    await sim.click_callback(f"dino {dino.id}")

    # Send new dinosaur name
    new_name = "Rexy"
    sim.clear_sent_requests()
    await sim.send_message(new_name)

    from bot.models.dinosaur import Dino
    db_dino = await Dino.find_one(Dino.id == dino.id)
    assert db_dino.name == new_name


@pytest.mark.asyncio
async def test_settings_delete_me(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.delete_me', lang))

    # 3 confirmation steps
    confirm_text = t('buttons_name.confirm', lang)
    for _ in range(3):
        sim.clear_sent_requests()
        await sim.send_message(confirm_text)

    # Read the generated random code from the last sent message
    last_msg = sim.get_last_message_text()
    match = re.search(r'\b\d{3,4}\b', last_msg)
    assert match is not None, f"Code not found in confirmation message: '{last_msg}'"
    code = match.group(0)

    sim.clear_sent_requests()
    await sim.send_message(code)

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user is None, "User was not deleted after entering confirmation steps"


@pytest.mark.asyncio
async def test_settings_my_name(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings2.my_name', lang))

    new_owner_name = "Arthur Pendragon"
    sim.clear_sent_requests()
    await sim.send_message(new_owner_name)

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.settings.get('my_name') == new_owner_name


@pytest.mark.asyncio
async def test_settings_lang(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings2.lang', lang))

    lang_data = get_all_locales('language_name')
    # Pick first available language name (e.g. English option)
    choice = list(lang_data.values())[0]
    expected_lang_key = lang_data[choice] if choice in lang_data else list(lang_data.keys())[0]

    sim.clear_sent_requests()
    await sim.send_message(choice)

    new_lang = await get_lang(sim.user_id)
    assert new_lang == expected_lang_key


@pytest.mark.asyncio
async def test_settings_dino_talk(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings2.dino_talk', lang))

    btn_text = t('buttons_name.disable', lang)
    sim.clear_sent_requests()
    await sim.send_message(btn_text)

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.settings.get('no_talk') is False


@pytest.mark.asyncio
async def test_settings_nick(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    # Give user coins so they can pay for the nickname change
    user = await User.find_one(User.userid == sim.user_id)
    await user.add_coins(10000)

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings2.nick', lang))

    new_nickname = "MasterDino"
    sim.clear_sent_requests()
    await sim.send_message(new_nickname)

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.name == new_nickname


@pytest.mark.asyncio
async def test_settings_reset_avatar(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    # Pre-set avatar
    user = await User.find_one(User.userid == sim.user_id)
    await user.update({"$set": {'avatar': "http://some-avatar-url"}})

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings2.reset_avatar', lang))

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.avatar == ""


@pytest.mark.asyncio
async def test_settings_confidentiality(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    # Give premium status to avoid paying super coins
    from bot.models.user import Subscription
    await Subscription.award_premium(sim.user_id, "inf")
    # Set super_coins as a backup
    user = await User.find_one(User.userid == sim.user_id)
    await user.update({'$set': {'super_coins': 1000}})

    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings2.confidentiality', lang))

    btn_text = t('buttons_name.enable', lang)
    sim.clear_sent_requests()
    await sim.send_message(btn_text)

    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user.settings.get('confidentiality') is True


@pytest.mark.asyncio
async def test_settings_delete_account(prep_user):
    sim = prep_user
    lang = await get_lang(sim.user_id, "ru")

    # Send delete_me command to open deletion state flow
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.delete_me', lang))

    # Confirmations (confirm, confirm2, confirm3)
    # 1. confirm
    await sim.send_message(t('buttons_name.yes', lang))
    # 2. confirm2
    await sim.send_message(t('buttons_name.yes', lang))
    # 3. confirm3
    await sim.send_message(t('buttons_name.yes', lang))

    # Get the code from the state to send it
    from bot.modules.get_state import get_state
    state = await get_state(sim.user_id, sim.user_id)
    state_data = await state.get_data()
    transmitted_data = state_data.get('transmitted_data', {})
    code = transmitted_data.get('code')
    assert code is not None, "Code should be generated in ChooseStepHandler transmitted_data"

    # Send correct code
    await sim.send_message(code)
    await asyncio.sleep(0.3)

    # Verify user record is completely removed from the database
    db_user = await User.find_one(User.userid == sim.user_id)
    assert db_user is None, "User should be completely deleted from DB"

    # Verify Redis cooldown exists
    from bot.redismanager import get_redis
    r = get_redis()
    ttl = await r.ttl(f"delete_cooldown:{sim.user_id}")
    assert ttl > 0, "Redis delete cooldown TTL should be greater than 0"

    # Re-insert the user to test cooldown enforcement
    new_user = User(userid=sim.user_id, name="Recreated User")
    await new_user.insert()
    new_lang = Lang(userid=sim.user_id, lang="ru")
    await new_lang.insert()

    # Attempt to delete account again while cooldown is active
    sim.clear_sent_requests()
    await sim.send_message(t('commands_name.settings.delete_me', lang))
    await asyncio.sleep(0.3)

    # Check bot response
    sent_msgs = sim.get_sent_requests()
    assert len(sent_msgs) > 0
    response_text = sent_msgs[-1].text
    assert "Вы недавно удалили аккаунт" in response_text, f"Expected cooldown message, got: {response_text}"
