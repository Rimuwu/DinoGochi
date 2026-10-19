import pytest
from bot.modules.markup import calculate_feed_options

def test_feed_calc_basic():
    # Dino eat = 40, act = 25, max_col = 5
    # Needed: 60. col_to_full = 2.
    # 1 piece: 65% = 1
    # 2 pieces: 90% = 2
    # 3 pieces: 100% = 3
    options = calculate_feed_options(dino_eat=40, item_act=25, max_col=5)
    assert len(options) == 3
    assert options[0] == {'text': '65% = 1', 'qty': 1, 'percent': 65}
    assert options[1] == {'text': '90% = 2', 'qty': 2, 'percent': 90}
    assert options[2] == {'text': '100% = 3', 'qty': 3, 'percent': 100}

def test_feed_calc_one_piece_reaches_full():
    # Dino eat = 70, act = 30, max_col = 5
    # 1 piece reaches 100%
    options = calculate_feed_options(dino_eat=70, item_act=30, max_col=5)
    assert len(options) == 1
    assert options[0] == {'text': '100% = 1', 'qty': 1, 'percent': 100}

def test_feed_calc_one_piece_almost_full():
    # Dino eat = 80, act = 15, max_col = 5
    # 1 piece gives 95%, 2 pieces gives 100%
    options = calculate_feed_options(dino_eat=80, item_act=15, max_col=5)
    assert len(options) == 2
    assert options[0] == {'text': '95% = 1', 'qty': 1, 'percent': 95}
    assert options[1] == {'text': '100% = 2', 'qty': 2, 'percent': 100}

def test_feed_calc_not_enough_items():
    # Dino eat = 10, act = 10, max_col = 3
    # Needed: 90. Player only has 3 items.
    # 1 piece gives 20%, 3 pieces gives 40%
    options = calculate_feed_options(dino_eat=10, item_act=10, max_col=3)
    assert len(options) == 2
    assert options[0] == {'text': '20% = 1', 'qty': 1, 'percent': 20}
    assert options[1] == {'text': '40% = 3', 'qty': 3, 'percent': 40}

def test_feed_calc_already_full():
    options = calculate_feed_options(dino_eat=100, item_act=20, max_col=5)
    assert len(options) == 1
    assert options[0] == {'text': '100% = 1', 'qty': 1, 'percent': 100}

def test_feed_calc_zero_max_col():
    options = calculate_feed_options(dino_eat=50, item_act=20, max_col=0)
    assert options == []

def test_feed_calc_zero_act():
    options = calculate_feed_options(dino_eat=90, item_act=0, max_col=5)
    assert len(options) >= 1
    assert options[0]['qty'] == 1
