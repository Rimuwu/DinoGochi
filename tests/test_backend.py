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
