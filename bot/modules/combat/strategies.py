# -*- coding: utf-8 -*-
import json
import random
from typing import List, Dict, Any, Tuple, Optional

from bot.const import COMBAT_STRATEGIES
COMBAT_SETTINGS = COMBAT_STRATEGIES if COMBAT_STRATEGIES else {
    "strategies": {
        "carry": {
            "target_weights": {"aggro": -0.5, "hp_percent": -2.0, "base_damage": 1.5},
            "heal_threshold_self": 0.3,
            "skill_preference": ["multi_strike", "ignore_armor", "aoe"]
        },
        "tank": {
            "target_weights": {"aggro": 0.5, "hp_percent": -0.5, "base_damage": 1.0},
            "heal_threshold_self": 0.4,
            "skill_preference": ["apply_effect_self", "counter_attack", "self_repair"]
        },
        "support": {
            "target_weights": {"aggro": 0.0, "hp_percent": -1.0, "base_damage": 0.5},
            "heal_threshold_self": 0.4,
            "heal_threshold_ally": 0.6,
            "skill_preference": ["apply_effect_self", "apply_effect_enemy"]
        }
    }
}

def get_strategy_weights(role: str) -> dict:
    """Returns the weights configuration for the specified role."""
    strategies = COMBAT_SETTINGS.get("strategies", {})
    return strategies.get(role, strategies.get("carry"))

def select_target(
    actor: Any,
    opponents: List[Any],
    intelligence: float
) -> Optional[Any]:
    """
    Selects the optimal target from opponents based on actor intelligence and role.
    
    Simple Intelligence (<= 5):
      - Submits blindly to aggro/taunts. Attacks the enemy with the highest aggro (80% chance) or a random target (20% chance).
      
    Medium Intelligence (5 < intelligence <= 15):
      - Standard role weights, but with small random variance.
      
    Smart Intelligence (> 15):
      - Evaluates target weights precisely according to the role settings.
    """
    alive_opponents = [o for o in opponents if o.is_alive()]
    if not alive_opponents:
        return None

    # Simple Intelligence (<= 5)
    if intelligence <= 5:
        if random.random() < 0.8:
            # Sort by aggro descending
            alive_opponents.sort(key=lambda x: x.aggro, reverse=True)
            return alive_opponents[0]
        else:
            return random.choice(alive_opponents)

    # For Medium and Smart Intelligence, use weights
    role = getattr(actor, "role", "carry")
    weights_cfg = get_strategy_weights(role)
    target_weights = weights_cfg.get("target_weights", {})
    
    aggro_w = target_weights.get("aggro", 0.0)
    hp_w = target_weights.get("hp_percent", 0.0)
    dmg_w = target_weights.get("base_damage", 0.0)

    # For medium intelligence, add a bit of noise/randomness
    noise_factor = 0.2 if intelligence <= 15 else 0.0

    best_target = None
    best_score = -999999.0

    for enemy in alive_opponents:
        hp_percent = (enemy.hp / getattr(enemy, "max_hp", 100)) * 100.0
        
        # Calculate target score
        score = (
            (enemy.aggro * aggro_w) +
            (hp_percent * hp_w) +
            (enemy.get_base_damage() * dmg_w)
        )
        
        # Add random noise if medium intelligence
        if noise_factor > 0:
            score += random.uniform(-10.0, 10.0) * noise_factor

        if score > best_score:
            best_score = score
            best_target = enemy

    return best_target

def select_action(
    actor: Any,
    allies: List[Any],
    opponents: List[Any]
) -> Tuple[str, Any]:
    """
    Selects what action to perform on the actor's turn.
    Returns a tuple: (action_type, action_arg)
    Where action_type is:
      - "heal": use a healing item from inventory. action_arg is the item dictionary.
      - "skill": activate a weapon/shield combat property. action_arg is (prop_id, prop_data).
      - "attack": basic attack. action_arg is the target.
      - "skip": do nothing (AP exhausted or no options).
    """
    if actor.ap < 0.5:
        return "skip", None

    intelligence = actor.stats.get("intelligence", 5)
    role = getattr(actor, "role", "carry")
    weights_cfg = get_strategy_weights(role)

    # 1. Check Healing Options (requires >= 0.5 AP and has healing items)
    heal_items = actor.get_heal_items()
    if heal_items:
        # Check self-healing
        self_hp_pct = actor.hp / actor.max_hp
        self_threshold = weights_cfg.get("heal_threshold_self", 0.3)
        
        # Simple intelligence only heals if extremely low (<= 20% HP)
        if intelligence <= 5:
            self_threshold = 0.2

        if self_hp_pct < self_threshold:
            # Use the best healing item (highest heal/energy recovery)
            best_heal_item = max(heal_items, key=lambda x: x.get("items_data", {}).get("buffs", {}).get("heal", 0))
            return "heal", (actor, best_heal_item)

        # Check ally-healing (only for Medium & Smart support role, or Smart carry/tanks if very critical)
        if intelligence > 5:
            ally_threshold = weights_cfg.get("heal_threshold_ally", 0.6)
            if role != "support":
                # Carries/Tanks only heal allies if they are near death (<= 25% HP)
                ally_threshold = 0.25

            critical_allies = [a for a in allies if a.is_alive() and (a.hp / a.max_hp) < ally_threshold]
            if critical_allies:
                # Find the ally with the lowest HP percent
                worst_ally = min(critical_allies, key=lambda a: a.hp / a.max_hp)
                best_heal_item = max(heal_items, key=lambda x: x.get("items_data", {}).get("buffs", {}).get("heal", 0))
                return "heal", (worst_ally, best_heal_item)

    # 2. Check Active Skills/Combat Properties (requires AP >= points_cost, energy >= energy_cost, cooldown == 0)
    if actor.ap >= 1.0:
        available_skills = actor.get_usable_skills()
        if available_skills:
            # Filter skills based on preferences
            pref_types = weights_cfg.get("skill_preference", [])
            
            # Simple intelligence picks a random available skill (50% chance) or uses basic attack
            if intelligence <= 5:
                if random.random() < 0.5:
                    chosen_skill = random.choice(available_skills)
                    return "skill", chosen_skill
            else:
                # Sort skills by preference order
                sorted_skills = []
                for pref in pref_types:
                    for skill in available_skills:
                        if skill[1].get("type") == pref:
                            sorted_skills.append(skill)
                
                # Append remaining skills not in preference list
                for skill in available_skills:
                    if skill not in sorted_skills:
                        sorted_skills.append(skill)

                if sorted_skills:
                    # Smart intelligence avoids using high-energy skills if energy is low (< 25)
                    for skill_id, skill_data in sorted_skills:
                        e_cost = skill_data.get("energy_cost", 0)
                        if intelligence > 15 and actor.energy - e_cost < 20 and e_cost > 0:
                            continue  # Save energy
                        
                        return "skill", (skill_id, skill_data)

    # 3. Fallback to Basic Attack (requires >= 1.0 AP)
    if actor.ap >= 1.0:
        target = select_target(actor, opponents, intelligence)
        if target:
            return "attack", target

    return "skip", None
