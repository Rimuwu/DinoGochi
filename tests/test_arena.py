import pytest
from bot.const import GAME_SETTINGS

def calculate_elo_change(r_a, r_b, outcome_a, streak_a=0):
    # Standard ELO formula
    e_a = 1 / (1 + 10 ** ((r_b - r_a) / 400))
    
    arena_cfg = GAME_SETTINGS.get('arena', {})
    k_factor = arena_cfg.get('elo_k_factor', 40)
    change_a = int(round(k_factor * (outcome_a - e_a)))

    # Novice league thresholds
    novice_thr = arena_cfg.get('novice_league_threshold', 1200)
    novice_loss = arena_cfg.get('novice_max_loss', 5)

    if outcome_a < 0.5: # loss
        if r_a < novice_thr and change_a < 0:
            change_a = max(change_a, -novice_loss)

    # Win streak bonuses
    streak_bonuses = arena_cfg.get('win_streak_bonuses', {"3": 5, "4": 10, "5": 15})
    if outcome_a > 0.5: # win
        bonus = 0
        if streak_a >= 3:
            bonus = streak_bonuses.get(str(streak_a), 15)
        change_a += bonus
        
    return change_a

def test_elo_calculations():
    # 1. Equal ratings, A wins
    change = calculate_elo_change(1000, 1000, 1.0)
    assert change == 20

    # 2. Novice league loss protection: A (1000 Elo) loses to B (1000 Elo)
    # Without protection: change = -20. With protection: -5
    change = calculate_elo_change(1000, 1000, 0.0)
    assert change == -5

    # 3. No protection for non-novice: A (1300 Elo) loses to B (1300 Elo)
    change = calculate_elo_change(1300, 1300, 0.0)
    assert change == -20

    # 4. Streak bonus: A wins with streak = 3
    # Base change = 20. Streak 3 bonus = 5. Total = 25.
    change = calculate_elo_change(1000, 1000, 1.0, streak_a=3)
    assert change == 25

    # 5. Streak bonus: A wins with streak = 5
    # Base change = 20. Streak 5 bonus = 15. Total = 35.
    change = calculate_elo_change(1000, 1000, 1.0, streak_a=5)
    assert change == 35
