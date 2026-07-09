import os
import sys
# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from bot.models.user import User
from bot.models.dinosaur import Dino

@pytest.mark.asyncio
async def test_user_creation():
    # Test creating a new user model in DB
    user = User(userid=111111, name="Alice")
    await user.insert()

    # Query from DB
    db_user = await User.find_one(User.userid == 111111)
    assert db_user is not None
    assert db_user.name == "Alice"
    assert db_user.coins == 100  # default coins

@pytest.mark.asyncio
async def test_user_coins():
    user = User(userid=222222, name="Bob", coins=500)
    await user.insert()

    # Test adding coins
    await user.add_coins(100)
    assert user.coins == 600

    # Retrieve from DB and verify persistency
    db_user = await User.find_one(User.userid == 222222)
    assert db_user.coins == 600

    # Test removing coins
    success = await user.remove_coins(250)
    assert success is True
    assert user.coins == 350

    # Test removing too many coins (should fail and keep amount same)
    success = await user.remove_coins(1000)
    assert success is False
    assert user.coins == 350

@pytest.mark.asyncio
async def test_dino_creation():
    # Test creating a dinosaur
    dino = Dino(data_id=1, alt_id="dino_test")
    await dino.insert()

    db_dino = await Dino.find_one(Dino.alt_id == "dino_test")
    assert db_dino is not None
    assert db_dino.data_id == 1

@pytest.mark.asyncio
async def test_combat_arrows():
    from bot.modules.combat.auto_combat import AutoCombat, CombatParticipant
    
    # 1. Attacker with a bow but NO arrows
    attacker_no_arrows = CombatParticipant(
        unique_id="attacker_1",
        name="ArcherNoArrows",
        participant_type="dino",
        max_hp=100.0,
        hp=100.0,
        max_energy=100.0,
        energy=100.0,
        stats={"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10},
        role="carry",
        weapon={"item_id": "bow_regular", "abilities": {"endurance": 50}},
        inventory=[]
    )
    
    target = CombatParticipant(
        unique_id="target_1",
        name="TargetDummy",
        participant_type="mob",
        max_hp=100.0,
        hp=100.0,
        max_energy=100.0,
        energy=100.0,
        stats={"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10},
        role="tank"
    )
    
    combat = AutoCombat([attacker_no_arrows], [target])
    
    # Run attack evasion to 0 to prevent evading during test
    target.stats["evasion"] = 0.0
    target.danger_point = 0.0
    
    # Execute attack
    combat.execute_attack(attacker_no_arrows, target, None)
    
    # Verify no arrows log is recorded
    assert any(log["key"] == "combat_log.no_arrows" for log in combat.log)
    
    # 2. Attacker with a bow AND wood arrows
    attacker_with_arrows = CombatParticipant(
        unique_id="attacker_2",
        name="ArcherWithArrows",
        participant_type="dino",
        max_hp=100.0,
        hp=100.0,
        max_energy=100.0,
        energy=100.0,
        stats={"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10},
        role="carry",
        weapon={"item_id": "bow_regular", "abilities": {"endurance": 50}},
        inventory=[{"item_id": "arrow_wood", "count": 5}]
    )
    
    target_2 = CombatParticipant(
        unique_id="target_2",
        name="TargetDummy2",
        participant_type="mob",
        max_hp=100.0,
        hp=100.0,
        max_energy=100.0,
        energy=100.0,
        stats={"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10},
        role="tank"
    )
    
    combat_2 = AutoCombat([attacker_with_arrows], [target_2])
    combat_2.execute_attack(attacker_with_arrows, target_2, None)
    
    # Verify wood arrow was used and count decremented
    assert attacker_with_arrows.inventory[0]["count"] == 4
    assert any(log["key"] == "combat_log.arrow_shot" for log in combat_2.log)
    
    # 3. Attacker with a bow AND platinum arrows (stun effect)
    attacker_with_plat = CombatParticipant(
        unique_id="attacker_3",
        name="ArcherWithPlat",
        participant_type="dino",
        max_hp=100.0,
        hp=100.0,
        max_energy=100.0,
        energy=100.0,
        stats={"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10},
        role="carry",
        weapon={"item_id": "bow_regular", "abilities": {"endurance": 50}},
        inventory=[{"item_id": "arrow_platinum", "count": 2}]
    )
    
    target_3 = CombatParticipant(
        unique_id="target_3",
        name="TargetDummy3",
        participant_type="mob",
        max_hp=100.0,
        hp=100.0,
        max_energy=100.0,
        energy=100.0,
        stats={"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10},
        role="tank"
    )
    
    combat_3 = AutoCombat([attacker_with_plat], [target_3])
    combat_3.execute_attack(attacker_with_plat, target_3, None)
    
    # Verify platinum arrow was used and target was stunned
    assert attacker_with_plat.inventory[0]["count"] == 1
    assert target_3.is_stunned is True

@pytest.mark.asyncio
async def test_item_info_arrows():
    from bot.modules.items.item import item_info
    
    # Test arrow_gold card info in Russian
    gold_arrow_info, _ = await item_info({"item_id": "arrow_gold"}, "ru")
    assert "Доп. урон: 3" in gold_arrow_info
    assert "Кровотечение" in gold_arrow_info
    
    # Test bow_regular card info in Russian
    bow_info, _ = await item_info({"item_id": "bow_regular"}, "ru")
    assert "Боеприпасы: 🏹 Стрелы" in bow_info

@pytest.mark.asyncio
async def test_journey_defeat_and_ejection():
    from bot.models.activity.journey import JourneyActivity
    from bot.models.dinosaur import Dino
    from bson import ObjectId
    
    dino = Dino(
        id=ObjectId(),
        data_id=1,
        alt_id="test_dino_123",
        name="Testosaur",
        quality="com",
        stats={"heal": 9, "energy": 100, "eat": 100, "game": 100, "mood": 100}
    )
    await dino.save()
    
    journey = JourneyActivity(
        id=ObjectId(),
        userid=77777,
        sended=77777,
        location="forest",
        dino_ids=[dino.id],
        pregenerated_events=[{
            "tick_index": 0,
            "trigger_time": 1000,
            "status": "pending",
            "type": "standard",
            "event_data": {
                "dino_edit": {"heal": -5}
            }
        }]
    )
    await journey.save()
    
    ejected = JourneyActivity._eject_weak_dinos(journey, [dino], journey.pregenerated_events[0])
    assert len(ejected) == 1
    assert len(journey.dino_ids) == 0
    left_events = [e for e in journey.pregenerated_events if e.get("type") == "dino_left"]
    assert len(left_events) == 1
    assert left_events[0]["event_data"]["dino_name"] == "Testosaur"
    
    await dino.delete()
    await journey.delete()

@pytest.mark.asyncio
async def test_custom_book_info_rendering():
    from bot.modules.items.item import item_info
    
    # Test book with default description
    default_info, _ = await item_info({"item_id": "custom_book"}, "ru")
    assert "Книга для записей" in default_info
    
    # Test book with custom content
    custom_content = "This is my custom diary note!"
    custom_info, _ = await item_info({
        "item_id": "custom_book",
        "abilities": {"content": custom_content}
    }, "ru")
    assert custom_content in custom_info
    assert "Ваша личная книга" not in custom_info

@pytest.mark.asyncio
async def test_durability_and_recipe_preview():
    from bot.models.activity.journey import JourneyActivity
    found_damaged = False
    for _ in range(200):
        rolled = JourneyActivity.roll_items_to_add(["bow_hunting"])
        if rolled and rolled[0].get("abilities") and "endurance" in rolled[0]["abilities"]:
            found_damaged = True
            assert rolled[0]["abilities"]["endurance"] >= 1
    assert found_damaged, "Should have rolled at least one damaged item in 200 trials"

