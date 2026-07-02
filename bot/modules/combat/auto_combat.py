# -*- coding: utf-8 -*-
import json
import random
import uuid
from typing import List, Dict, Any, Tuple, Optional, Union
from bson import ObjectId

from bot.models.dinosaur import Dino
from bot.models.items import Item
from bot.modules.items.item import get_data, get_item_level, UseAutoRemove, get_item_damage, get_item_reflection
from bot.modules.items.combat_properties import get_item_properties
from bot.modules.localization import t
from bot.modules.data_format import transform
from bot.modules.notifications import dino_notification
from bot.modules.combat.strategies import select_action, select_target

# Load settings
try:
    with open('bot/json/combat_mobs_settings.json', encoding='utf-8') as f:
        COMBAT_SETTINGS = json.load(f)
except Exception:
    COMBAT_SETTINGS = {}

class CombatParticipant:
    def __init__(
        self,
        unique_id: str,
        name: str,
        participant_type: str,  # "dino" or "mob"
        max_hp: float,
        hp: float,
        max_energy: float,
        energy: float,
        stats: Dict[str, float],  # power, dexterity, intelligence, charisma
        role: str,  # "carry", "tank", "support"
        weapon: Optional[dict] = None,
        shield: Optional[dict] = None,
        inventory: Optional[List[dict]] = None,
        original_obj: Optional[Any] = None,
        danger_point: float = 0.0,
        mob_id: Optional[str] = None
    ):
        self.unique_id = unique_id
        self.name = name
        self.type = participant_type
        self.max_hp = max_hp
        self.hp = hp
        self.max_energy = max_energy
        self.energy = energy
        self.stats = stats
        self.role = role
        self.weapon = weapon
        self.shield = shield
        self.inventory = inventory or []  # List of healing items
        self.original_obj = original_obj
        self.danger_point = danger_point
        self.mob_id = mob_id
        
        self.ap = 2.0
        self.aggro = 0.0
        self.cooldowns = {}  # prop_id -> turns
        self.effects = []  # list of active effect dicts
        self.is_stunned = False

    def is_alive(self) -> bool:
        if self.type == "mob":
            return self.hp > 0 and self.energy > 0
        return self.hp > 10 and self.energy > 0

    @property
    def min_hp(self) -> float:
        return 0.0 if self.type == "mob" else 10.0

    def get_base_damage(self) -> float:
        """Returns the base attack damage (scaled for mobs)."""
        if self.type == "mob":
            # Return mean damage or roll within damage range
            dmg_range = self.stats.get("damage_range", {"min": 5, "max": 10})
            return random.uniform(dmg_range["min"], dmg_range["max"])
        return 1.0

    def get_heal_items(self) -> List[dict]:
        """Returns heal items from inventory that can be used."""
        heals = []
        for item in self.inventory:
            if item.get("count", 0) <= 0:
                continue
            item_id = item.get("item_id")
            data_item = get_data(item_id)
            buffs = data_item.get("buffs", {})
            if "heal" in buffs or "energy" in buffs:
                heals.append(item)
        return heals

    def get_usable_skills(self) -> List[Tuple[str, dict]]:
        """Returns weapon skills that are off cooldown and can be cast."""
        if not self.weapon or self.weapon.get("abilities", {}).get("endurance", 0) <= 0:
            return []
        
        level = get_item_level(self.weapon)
        props = get_item_properties(self.weapon, level)
        usable = []
        for prop_id, prop_data in props:
            # Check if active skill (costs AP/energy or has cooldown)
            is_active = prop_data.get("points_cost", 0) > 0 or prop_data.get("energy_cost", 0) > 0
            if not is_active:
                continue
            
            # Check cooldown
            if self.cooldowns.get(prop_id, 0) > 0:
                continue
                
            # Check AP and Energy cost
            if self.ap < prop_data.get("points_cost", 1.0):
                continue
            if self.energy < prop_data.get("energy_cost", 0):
                continue
                
            usable.append((prop_id, prop_data))
        return usable

    def get_passive_properties(self) -> List[Tuple[str, dict]]:
        """Returns passive properties of weapon/armor (points_cost == 0)."""
        passives = []
        # Weapon passives
        if self.weapon and self.weapon.get("abilities", {}).get("endurance", 0) > 0:
            level = get_item_level(self.weapon)
            props = get_item_properties(self.weapon, level)
            for prop_id, prop_data in props:
                if prop_data.get("points_cost", 0) == 0:
                    passives.append((prop_id, prop_data))
        
        # Shield/Armor passives
        if self.shield and self.shield.get("abilities", {}).get("endurance", 0) > 0:
            level = get_item_level(self.shield)
            props = get_item_properties(self.shield, level)
            for prop_id, prop_data in props:
                passives.append((prop_id, prop_data))
                
        return passives

    @classmethod
    async def from_dino(cls, dino: Dino, inventory_ids: List[ObjectId]) -> "CombatParticipant":
        # Calculate combat stats/caps
        combat_caps = await dino.get_combat_capabilities()
        
        # Fetch equipped weapons & shields
        equipped_weapons = await Item.find_accessory(dino.id, "weapon")
        equipped_shields = await Item.find_accessory(dino.id, "armor")
        
        weapon = equipped_weapons[0].items_data if equipped_weapons else None
        shield = equipped_shields[0].items_data if equipped_shields else None

        # Fetch inventory healing items
        inventory_items = []
        if inventory_ids:
            db_items = await Item.find({"_id": {"$in": list(inventory_ids)}}).to_list()
            for db_item in db_items:
                inventory_items.append({
                    "_id": db_item.id,
                    "item_id": db_item.item_id,
                    "items_data": db_item.items_data,
                    "count": db_item.count
                })

        # Calculate role based on stats
        pwr = dino.stats.get("power", 0.0)
        dex = dino.stats.get("dexterity", 0.0)
        itl = dino.stats.get("intelligence", 0.0)
        
        highest = max(pwr, dex, itl)
        if highest == itl and highest > 5:
            role = "support"
        elif highest == dex and highest > 5:
            role = "tank"
        else:
            role = "carry"

        # Map stats dict
        stats = {
            "power": pwr,
            "dexterity": dex,
            "intelligence": itl,
            "charisma": dino.stats.get("charisma", 0.0)
        }

        return cls(
            unique_id=str(dino.id),
            name=dino.name,
            participant_type="dino",
            max_hp=100.0,
            hp=max(10.0, float(dino.stats.get("heal", 100.0))),
            max_energy=100.0,
            energy=float(dino.stats.get("energy", 100.0)),
            stats=stats,
            role=role,
            weapon=weapon,
            shield=shield,
            inventory=inventory_items,
            original_obj=dino
        )

class AutoCombat:
    def __init__(self, team_x: List[CombatParticipant], team_y: List[CombatParticipant]):
        self.team_x = team_x
        self.team_y = team_y
        self.log = []
        self.round_num = 0
        self.winner = None
        self.loot_collected = []
        self.consumed_items = {}  # user_id -> {item_id: count}

        # Set team identifiers
        for p in self.team_x:
            p.team = "X"
        for p in self.team_y:
            p.team = "Y"

    def add_log(self, key: str, **kwargs):
        # Round float arguments to 1 decimal place to prevent long decimal outputs
        for k, v in list(kwargs.items()):
            if isinstance(v, float):
                kwargs[k] = round(v, 1)
        self.log.append({"key": key, "args": kwargs})

    def get_allies_and_opponents(self, actor: CombatParticipant) -> Tuple[List[CombatParticipant], List[CombatParticipant]]:
        if actor.team == "X":
            return self.team_x, self.team_y
        return self.team_y, self.team_x

    def run(self) -> dict:
        """Executes the battle turn-by-turn until a team is defeated or max rounds limit is hit."""
        max_rounds = 50
        
        def get_starting_info(p):
            return {
                "name": p.name,
                "type": p.type,
                "hp": p.hp,
                "max_hp": p.max_hp,
                "energy": p.energy,
                "max_energy": p.max_energy,
                "role": p.role,
                "weapon": p.weapon["item_id"] if p.weapon else None,
                "shield": p.shield["item_id"] if p.shield else None,
                "mob_id": p.mob_id
            }

        starting_data = {
            "X": [get_starting_info(p) for p in self.team_x],
            "Y": [get_starting_info(p) for p in self.team_y]
        }

        self.add_log("combat_log.battle_start")

        while self.round_num < max_rounds and self.is_battle_active():
            self.round_num += 1
            self.execute_round()

        # Determine winner
        alive_x = any(p.is_alive() for p in self.team_x)
        alive_y = any(p.is_alive() for p in self.team_y)
        
        reason_key = ""
        if alive_x and not alive_y:
            self.winner = "X"
            reason_key = "combat_log.reason_victory"
            self.add_log("combat_log.reason_victory")
            self.add_log("combat_log.battle_end", winner_team="X")
        elif alive_y and not alive_x:
            self.winner = "Y"
            reason_key = "combat_log.reason_victory"
            self.add_log("combat_log.reason_victory")
            self.add_log("combat_log.battle_end", winner_team="Y")
        else:
            self.winner = "DRAW"
            reason_key = "combat_log.reason_defeat_all"
            self.add_log("combat_log.reason_defeat_all")
            self.add_log("combat_log.battle_end", winner_team="DRAW")

        # Roll loot from defeated mobs
        self.generate_rewards()

        return {
            "winner": self.winner,
            "rounds": self.round_num,
            "reason_key": reason_key,
            "starting_data": starting_data,
            "log": self.log,
            "loot": self.loot_collected,
            "survivors": {
                "X": [{"name": p.name, "hp": p.hp, "energy": p.energy} for p in self.team_x],
                "Y": [{"name": p.name, "hp": p.hp, "energy": p.energy} for p in self.team_y]
            }
        }

    @staticmethod
    def format_log(log_data: Union[dict, list], lang: str) -> List[str]:
        if isinstance(log_data, list):
            result = {"log": log_data, "starting_data": {}}
        else:
            result = log_data
        
        grouped = AutoCombat.group_and_format_log(result, lang)
        flat_list = []
        for r_num in sorted(grouped.keys()):
            flat_list.extend(grouped[r_num])
        return flat_list

    @staticmethod
    def group_and_format_log(result: Union[dict, list], lang: str) -> dict:
        from bot.modules.localization import t
        from bot.modules.items.item import get_name
        from collections import Counter
        
        if isinstance(result, dict):
            log_data = result.get("log", [])
            starting_data = result.get("starting_data", {})
        else:
            log_data = result
            starting_data = {}
            
        name_map = {}
        for team in ["X", "Y"]:
            for p in starting_data.get(team, []):
                p_copy = p.copy()
                p_copy["team"] = team
                name_map[p["name"]] = p_copy

        def translate_participant_name(p_name: str) -> str:
            if p_name in name_map:
                p = name_map[p_name]
                if p["type"] == "mob" and p.get("mob_id"):
                    translated = t(f"mobs.{p['mob_id']}.name", lang)
                    if "mobs." in translated:
                        translated = p['mob_id'].capitalize()
                    mob_emoji = t(f"mobs.{p['mob_id']}.emoji", lang)
                    if "mobs." in mob_emoji or not mob_emoji:
                        mob_emoji = "👾"
                    return f"{mob_emoji} {translated}"
                else:
                    name_base = p_name
                    for suffix in [" (X)", " (Y)"]:
                        if name_base.endswith(suffix):
                            name_base = name_base[:-len(suffix)]
                    return name_base
            return p_name

        round_logs = {}
        current_round = 1
        last_was_skill = False
        
        for entry in log_data:
            key = entry["key"]
            args_dict = entry["args"].copy()

            if key == "combat_log.turn_start":
                current_round = args_dict["turn"]
                last_was_skill = False
            
            for arg_key, arg_val in args_dict.items():
                if isinstance(arg_val, str) and arg_val in name_map:
                    args_dict[arg_key] = translate_participant_name(arg_val)
                elif isinstance(arg_val, float):
                    args_dict[arg_key] = round(arg_val, 1)

            # Localize skill_name / item_name
            for field in ["skill_name", "item_name"]:
                if field in args_dict:
                    item_id = args_dict[field]
                    translated_val = t(f"combat_properties.names.{item_id}", lang)
                    if "combat_properties.names" in translated_val:
                        translated_val = get_name(item_id, lang)
                    args_dict[field] = translated_val

            if key == "combat_log.round_order" and "order" in args_dict:
                order_str = args_dict["order"]
                parts = order_str.split(" ➔ ")
                translated_parts = [translate_participant_name(p_name) for p_name in parts]
                args_dict["order"] = " ➔ ".join(translated_parts)

            if key == "combat_log.loot_dropped" and "loot_list" in args_dict:
                loot_val = args_dict["loot_list"]
                if isinstance(loot_val, list):
                    counts = Counter(loot_val)
                else:
                    items = [i.strip() for i in loot_val.split(",") if i.strip()]
                    counts = Counter(items)
                
                translated_loot = []
                for item_id, count in counts.items():
                    translated_name = get_name(item_id, lang)
                    if count > 1:
                        translated_loot.append(f"{translated_name} x{count}")
                    else:
                        translated_loot.append(translated_name)
                args_dict["loot_list"] = ", ".join(translated_loot)

            try:
                line = t(key, lang, **args_dict)
            except Exception:
                line = f"{key} (args: {args_dict})"

            # Highlight and append combat explanations for skills
            if key in ["combat_log.basic_attack", "combat_log.counter_attack", "combat_log.aoe_damage"]:
                extra_desc = []
                if args_dict.get("ignored_armor"):
                    if lang == "ru": extra_desc.append("пробивая броню")
                    elif lang == "es": extra_desc.append("ignorando armadura")
                    elif lang == "id": extra_desc.append("menembus pertahanan")
                    else: extra_desc.append("ignoring armor")
                if args_dict.get("applied_effect") == "stun":
                    if lang == "ru": extra_desc.append("оглушая цель")
                    elif lang == "es": extra_desc.append("aturdiendo al objetivo")
                    elif lang == "id": extra_desc.append("membuat target pingsan")
                    else: extra_desc.append("stunning target")
                elif args_dict.get("applied_effect") == "dot":
                    if lang == "ru": extra_desc.append("вызывая кровотечение")
                    elif lang == "es": extra_desc.append("causando sangrado")
                    elif lang == "id": extra_desc.append("menyebabkan pendarahan")
                    else: extra_desc.append("causing bleeding")
                
                if extra_desc:
                    line += f" ({', '.join(extra_desc)})"

            # Prepend turn start with actor team emoji
            if key == "combat_log.turn_start" and "name" in args_dict:
                actor_name = entry["args"]["name"]
                team_emoji = "🟢"
                if actor_name in name_map:
                    team_emoji = "🟢" if name_map[actor_name]["team"] == "X" else "🔴"
                if "🎬" in line:
                    line = line.replace("🎬", team_emoji)
                else:
                    line = f"{team_emoji} {line}"

            # Format skill subpoint
            if key == "combat_log.skill_activation":
                last_was_skill = True
            elif last_was_skill and key not in ["combat_log.turn_start", "combat_log.round_order"]:
                line = f"   ↳ {line}"

            round_logs.setdefault(current_round, []).append(line)
        return round_logs

    def is_battle_active(self) -> bool:
        alive_x = any(p.is_alive() for p in self.team_x)
        alive_y = any(p.is_alive() for p in self.team_y)
        return alive_x and alive_y

    def execute_round(self):
        # 1. Determine Turn Order: Priority = random(0..10) + intelligence * 0.5
        all_participants = [p for p in self.team_x + self.team_y if p.is_alive()]
        
        def turn_priority(p):
            intel = p.stats.get("intelligence", 5)
            # Smart dinos transform intelligence
            intel_mod = intel * 0.5
            return random.uniform(0, 10) + intel_mod

        turn_order = sorted(all_participants, key=turn_priority, reverse=True)
        order_str = " ➔ ".join(p.name for p in turn_order)
        self.add_log("combat_log.round_order", order=order_str)

        for actor in turn_order:
            if not actor.is_alive() or not self.is_battle_active():
                continue

            self.execute_turn(actor)

    def execute_turn(self, actor: CombatParticipant):
        self.add_log("combat_log.turn_start", turn=self.round_num, name=actor.name)
        
        # 1. Update active effects (buffs/debuffs) at start of turn
        self.process_start_turn_effects(actor)
        if not actor.is_alive():
            return

        if actor.is_stunned:
            self.add_log("combat_log.stunned", name=actor.name)
            actor.is_stunned = False
            return

        # 2. Reset AP
        actor.ap = 2.0

        # Decrement cooldowns
        for skill_id in list(actor.cooldowns.keys()):
            if actor.cooldowns[skill_id] > 0:
                actor.cooldowns[skill_id] -= 1

        # 3. Action Loop
        allies, opponents = self.get_allies_and_opponents(actor)
        action_count = 0
        
        while actor.ap >= 0.5 and actor.is_alive() and self.is_battle_active() and action_count < 5:
            action_count += 1
            action, arg = select_action(actor, allies, opponents)
            
            if action == "skip":
                break
                
            elif action == "heal":
                target_ally, item_dict = arg
                item_id = item_dict.get("item_id")
                data_item = get_data(item_id)
                buffs = data_item.get("buffs", {})
                
                heal_val = buffs.get("heal", 0)
                energy_val = buffs.get("energy", 0)
                
                target_ally.hp = min(target_ally.max_hp, target_ally.hp + heal_val)
                target_ally.energy = min(target_ally.max_energy, target_ally.energy + energy_val)
                
                # Consume item
                item_dict["count"] -= 1
                owner_id = item_dict.get("owner_id") or actor.unique_id
                if owner_id not in self.consumed_items:
                    self.consumed_items[owner_id] = {}
                self.consumed_items[owner_id][item_id] = self.consumed_items[owner_id].get(item_id, 0) + 1

                actor.ap -= 0.5
                self.add_log(
                    "combat_log.use_heal",
                    name=actor.name,
                    target=target_ally.name,
                    item_name=item_id,
                    heal=heal_val,
                    energy=energy_val,
                    ap_spent=0.5
                )

            elif action == "skill":
                skill_id, skill_data = arg
                target = select_target(actor, opponents, actor.stats.get("intelligence", 5))
                if not target:
                    break

                points_cost = skill_data.get("points_cost", 1.0)
                energy_cost = skill_data.get("energy_cost", 0)
                
                actor.ap -= points_cost
                actor.energy -= energy_cost
                actor.cooldowns[skill_id] = skill_data.get("cooldown", 0) + 1

                self.add_log("combat_log.skill_activation", name=actor.name, skill_name=skill_id)
                sd_copy = skill_data.copy()
                sd_copy["skill_id"] = skill_id
                self.execute_attack(actor, target, sd_copy)

            elif action == "attack":
                target = arg
                actor.ap -= 1.0
                actor.energy -= 5  # basic attack energy cost
                self.execute_attack(actor, target, None)

    def process_start_turn_effects(self, actor: CombatParticipant):
        """Processes and ticks effects at the start of a turn."""
        # Passive self_repair
        passives = actor.get_passive_properties()
        for prop_id, prop_data in passives:
            if prop_data.get("type") == "self_repair":
                val = prop_data.get("params", {}).get("repair_val", 0)
                if actor.shield and actor.shield.get("abilities", {}).get("endurance", 0) > 0:
                    dur_max = get_item_reflection(actor.shield) * 20  # estimate max durability or use helper
                    actor.shield["abilities"]["endurance"] = min(dur_max, actor.shield["abilities"]["endurance"] + val)
                    self.add_log("combat_log.self_repair", name=actor.name, val=val, skill_name=prop_id)

        # Active effects ticking
        expired_effects = []
        for eff in actor.effects:
            eff["duration"] -= 1
            eff_type = eff.get("type")
            eff_name = eff.get("name", eff_type)
            val = eff.get("val", 0)

            if eff_type == "dot":
                actor.hp = max(actor.min_hp, actor.hp - val)
                self.add_log("combat_log.effect_damage", damage=val, target=actor.name, effect_name=eff_name)
                if actor.hp <= actor.min_hp:
                    self.add_log("combat_log.defeat_hp", name=actor.name)
                    break
            elif eff_type == "corrosion":
                if actor.shield and actor.shield.get("abilities", {}).get("endurance", 0) > 0:
                    actor.shield["abilities"]["endurance"] = max(0, actor.shield["abilities"]["endurance"] - val)
                    self.add_log("combat_log.effect_corrosion", target=actor.name, val=val, effect_name=eff_name)
            elif eff_type == "heal_over_time":
                actor.hp = min(actor.max_hp, actor.hp + val)
            elif eff_type == "energy_over_time":
                actor.energy = min(actor.max_energy, actor.energy + val)

            if eff["duration"] <= 0:
                expired_effects.append(eff)

        # Clean expired effects
        for eff in expired_effects:
            if eff in actor.effects:
                actor.effects.remove(eff)

    def execute_attack(self, attacker: CombatParticipant, target: CombatParticipant, skill_data: Optional[dict]):
        # Evasion check
        dexterity = target.stats.get("dexterity", 0)
        evasion_chance = target.danger_point * 20.0 if target.type == "mob" else transform(dexterity, 20.0, 45.0)
        
        if random.uniform(0, 100) < evasion_chance:
            self.add_log("combat_log.evaded", target=target.name, attacker=attacker.name)
            return

        # Base weapon damage
        if attacker.weapon and attacker.weapon.get("abilities", {}).get("endurance", 0) > 0:
            dmg_data = get_item_damage(attacker.weapon) or {"min": 1, "max": 2}
            min_dmg = dmg_data.get("min", 1)
            max_dmg = dmg_data.get("max", 2)
            if min_dmg > max_dmg:
                min_dmg, max_dmg = max_dmg, min_dmg
            base_dmg = random.randint(int(min_dmg), int(max_dmg))
        else:
            base_dmg = attacker.get_base_damage()

        # Strength Damage Buff
        pwr = attacker.stats.get("power", 0)
        strength_buff = transform(pwr, 20.0, 15.0)
        
        # Roll base damage
        base_dmg += strength_buff

        # Active Skill or Passive weapon modifications
        ignore_percent = 0.0
        aoe_percent = 0.0
        multi_strike = False
        apply_enemy_eff = None
        apply_self_eff = None

        props = []
        if skill_data:
            props.append((skill_data.get("skill_id", "skill"), skill_data))
        else:
            props.extend(attacker.get_passive_properties())

        for prop_id, prop_data in props:
            p_type = prop_data.get("type")
            params = prop_data.get("params", {})
            
            if p_type == "ignore_armor":
                ignore_percent = max(ignore_percent, params.get("ignore_percent", 0.0))
            elif p_type == "aoe":
                aoe_percent = max(aoe_percent, params.get("aoe_percent", 0.0))
            elif p_type == "multi_strike":
                multi_strike = True
                multi_strike_params = params
            elif p_type == "apply_effect_enemy":
                apply_enemy_eff = (prop_id, prop_data)
            elif p_type == "apply_effect_self":
                apply_self_eff = (prop_id, prop_data)

        # Block reduction
        block = 0.0
        if target.shield and target.shield.get("abilities", {}).get("endurance", 0) > 0:
            block = get_item_reflection(target.shield)
            # Reduce shield durability
            target.shield["abilities"]["endurance"] = max(0, target.shield["abilities"]["endurance"] - 1)
            if target.shield["abilities"]["endurance"] <= 0:
                self.add_log("combat_log.shield_broke", target=target.name)
        else:
            block = target.stats.get("reflection", 0.0)

        # Apply armor ignore
        if ignore_percent > 0:
            block = block * (1.0 - ignore_percent)

        final_dmg = max(1.0, base_dmg - block)

        # Apply weapon durability loss
        if attacker.weapon and attacker.weapon.get("abilities", {}).get("endurance", 0) > 0:
            attacker.weapon["abilities"]["endurance"] = max(0, attacker.weapon["abilities"]["endurance"] - 1)
            if attacker.weapon["abilities"]["endurance"] <= 0:
                self.add_log("combat_log.weapon_broke", attacker=attacker.name)

        # Deal damage
        target.hp = max(target.min_hp, target.hp - final_dmg)
        
        # Increase attacker threat/aggro
        attacker.aggro += final_dmg

        self.add_log(
            "combat_log.basic_attack",
            attacker=attacker.name,
            target=target.name,
            damage=final_dmg,
            ap_spent=1.0 if not skill_data else skill_data.get("points_cost", 1.0),
            energy_spent=5 if not skill_data else skill_data.get("energy_cost", 0),
            ignored_armor=(skill_data is not None and ignore_percent > 0)
        )

        if target.hp <= target.min_hp:
            self.add_log("combat_log.defeat_hp", name=target.name)
            return

        # Handle Counter-Attack
        if target.is_alive() and target.shield:
            passives = target.get_passive_properties()
            for prop_id, prop_data in passives:
                if prop_data.get("type") == "counter_attack":
                    chance = prop_data.get("params", {}).get("chance", 0.0)
                    if random.uniform(0, 1) < chance:
                        # Immediate basic counter attack
                        counter_dmg = max(1.0, target.get_base_damage() - (attacker.stats.get("reflection", 0)))
                        attacker.hp = max(attacker.min_hp, attacker.hp - counter_dmg)
                        self.add_log("combat_log.counter_attack", target=target.name, attacker=attacker.name, damage=counter_dmg)
                        
                        if attacker.hp <= attacker.min_hp:
                            self.add_log("combat_log.defeat_hp", name=attacker.name)
                            return

        # Handle Multi-Strike
        if multi_strike and target.is_alive():
            extra_chance = multi_strike_params.get("extra_chance", 0.0)
            max_strikes = multi_strike_params.get("max_strikes", 2)
            strikes = 1
            
            while strikes < max_strikes and random.uniform(0, 1) < extra_chance:
                strikes += 1
                extra_dmg = max(1.0, (random.randint(int(min_dmg), int(max_dmg)) * 0.7) - block)
                target.hp = max(target.min_hp, target.hp - extra_dmg)
                attacker.aggro += extra_dmg
                self.add_log("combat_log.basic_attack", attacker=attacker.name, target=target.name, damage=extra_dmg, ap_spent=0, energy_spent=0)
                
                if target.hp <= target.min_hp:
                    self.add_log("combat_log.defeat_hp", name=target.name)
                    return

        # Handle AoE
        if aoe_percent > 0:
            allies, opponents = self.get_allies_and_opponents(target)
            try:
                target_idx = opponents.index(target)
            except ValueError:
                target_idx = -1
                
            if target_idx != -1:
                neighbors = []
                if target_idx - 1 >= 0:
                    neighbors.append(opponents[target_idx - 1])
                if target_idx + 1 < len(opponents):
                    neighbors.append(opponents[target_idx + 1])

                for neighbor in neighbors:
                    if neighbor.is_alive():
                        aoe_dmg = max(1.0, (final_dmg * aoe_percent) - neighbor.stats.get("reflection", 0))
                        neighbor.hp = max(neighbor.min_hp, neighbor.hp - aoe_dmg)
                        attacker.aggro += aoe_dmg
                        self.add_log("combat_log.aoe_damage", attacker=attacker.name, target=neighbor.name, damage=aoe_dmg)
                        
                        if neighbor.hp <= neighbor.min_hp:
                            self.add_log("combat_log.defeat_hp", name=neighbor.name)

        # Handle apply_effect_enemy
        if apply_enemy_eff and target.is_alive():
            prop_id, prop_data = apply_enemy_eff
            chance = prop_data.get("base_chance", 1.0)
            
            # Apply stat scale (dexterity increases chance)
            scale = prop_data.get("stat_scale")
            if scale:
                stat_val = attacker.stats.get(scale.get("stat", ""), 0)
                chance += stat_val * scale.get("multiplier", 0.0)

            if random.uniform(0, 1) < chance:
                # Target ignore effects check
                ignored = False
                target_passives = target.get_passive_properties()
                for t_prop_id, t_prop_data in target_passives:
                    if t_prop_data.get("type") == "ignore_effects":
                        eff_type = prop_data.get("params", {}).get("effect_type", "")
                        if eff_type in t_prop_data.get("params", {}).get("ignored_types", []):
                            ignore_chance = t_prop_data.get("params", {}).get("chance", 0.0)
                            if random.uniform(0, 1) < ignore_chance:
                                ignored = True
                                break

                if ignored:
                    self.add_log("combat_log.effect_ignored", target=target.name, effect_name=prop_id)
                else:
                    params = prop_data.get("params", {})
                    eff_type = params.get("effect_type")
                    duration = params.get("duration", 1)
                    val = params.get("val", 0)
                    
                    if eff_type == "stun":
                        target.is_stunned = True
                        
                    target.effects.append({
                        "type": eff_type,
                        "name": prop_id,
                        "duration": duration,
                        "val": val
                    })
                    self.add_log("combat_log.effect_applied", target=target.name, effect_name=prop_id, duration=duration)
                    for entry in reversed(self.log):
                        if entry["key"] == "combat_log.basic_attack" and entry["args"].get("attacker") == attacker.name:
                            entry["args"]["applied_effect"] = eff_type
                            break

        # Handle apply_effect_self
        if apply_self_eff:
            prop_id, prop_data = apply_self_eff
            chance = prop_data.get("base_chance", 1.0)
            if random.uniform(0, 1) < chance:
                params = prop_data.get("params", {})
                duration = params.get("duration", 1)
                
                # Apply instant healing/energy
                heal_inst = params.get("heal_instant", 0)
                energy_inst = params.get("energy_regen", 0)
                
                if heal_inst > 0:
                    attacker.hp = min(attacker.max_hp, attacker.hp + heal_inst)
                if energy_inst > 0:
                    attacker.energy = min(attacker.max_energy, attacker.energy + energy_inst)
                
                # Apply buffs
                buff_stats = params.get("buff_stats", {})
                if buff_stats:
                    # Apply stat changes dynamically
                    for k, v in buff_stats.items():
                        attacker.stats[k] = attacker.stats.get(k, 0) + v
                
                attacker.effects.append({
                    "type": "buff",
                    "name": prop_id,
                    "duration": duration,
                    "val": 0,
                    "buff_stats": buff_stats
                })
                self.add_log("combat_log.effect_applied", target=attacker.name, effect_name=prop_id, duration=duration)

    def generate_rewards(self):
        """Rolls loot for the victorious team based on defeated mobs' danger points."""
        # Identify defeated mobs
        defeated_mobs = []
        if self.winner == "X":
            defeated_mobs = [p for p in self.team_y if p.type == "mob"]
        elif self.winner == "Y":
            defeated_mobs = [p for p in self.team_x if p.type == "mob"]
        else:
            return  # DRAW has no loot

        loot_pool = COMBAT_SETTINGS.get("loot_pool", [])
        loot_groups = COMBAT_SETTINGS.get("loot_groups", {})

        for mob in defeated_mobs:
            D = mob.danger_point
            
            # Roll from mob's specific loot (from journey.json / original journey object)
            mob_loot_pool = []
            if mob.original_obj and "loot" in mob.original_obj:
                mob_loot_pool = mob.original_obj["loot"]
                
            # Filter global loot pool by danger point
            eligible_loot = []
            for entry in loot_pool:
                if entry.get("min_danger", 0.0) <= D <= entry.get("max_danger", 1.0):
                    eligible_loot.append(entry)

            # Roll mob-specific loot: choose 1 item/group with probability D
            if mob_loot_pool and random.random() < max(0.2, D):
                chosen_loot_key = random.choice(mob_loot_pool)
                # Resolve group or specific item
                if chosen_loot_key in loot_groups:
                    item_id = random.choice(loot_groups[chosen_loot_key])
                    self.loot_collected.append(item_id)
                else:
                    self.loot_collected.append(chosen_loot_key)

            # Roll global danger-based loot
            for loot_entry in eligible_loot:
                chance = loot_entry.get("chance", 0.5)
                if random.random() < chance:
                    loot_item = loot_entry.get("item")
                    is_group = loot_entry.get("is_group", False)
                    
                    if is_group and loot_item in loot_groups:
                        item_id = random.choice(loot_groups[loot_item])
                        self.loot_collected.append(item_id)
                    else:
                        self.loot_collected.append(loot_item)

        if self.loot_collected:
            self.add_log("combat_log.loot_dropped", loot_list=", ".join(self.loot_collected))

    async def sync_to_database(self):
        """Applies HP, energy, item consumption, and durability changes to the database."""
        # 1. Sync Dinosaur HP and Energy
        for p in self.team_x + self.team_y:
            if p.type == "dino" and p.original_obj:
                dino = p.original_obj
                dino.stats["heal"] = max(10, int(p.hp))
                dino.stats["energy"] = max(0, int(p.energy))
                
                # Check status
                if dino.stats["heal"] <= 10:
                    # Dino leaves battle, but if it dies in real game, let's keep HP at 10
                    # The prompt says: "динозавр считается проигравшим и выходит из боя при достижении 10хп, даже если было 11 хп и нанеслось -1к, то всё равно 10хп останется."
                    # We don't trigger self.dead() because it stays at 10hp!
                    pass

                await dino.save()

                # Sync Equipped Weapon & Shield durability
                if p.weapon:
                    # Find weapon document in DB and update
                    weapon_doc = await Item.find_one(Item.owner_id == str(dino.id), {"items_data.item_id": p.weapon["item_id"]})
                    if weapon_doc:
                        new_dur = p.weapon["abilities"].get("endurance", 0)
                        if new_dur <= 0:
                            await weapon_doc.delete()
                            await dino_notification(dino.id, 'broke_accessory', item_id=p.weapon["item_id"])
                        else:
                            weapon_doc.items_data["abilities"]["endurance"] = new_dur
                            await weapon_doc.save()

                if p.shield:
                    shield_doc = await Item.find_one(Item.owner_id == str(dino.id), {"items_data.item_id": p.shield["item_id"]})
                    if shield_doc:
                        new_dur = p.shield["abilities"].get("endurance", 0)
                        if new_dur <= 0:
                            await shield_doc.delete()
                            await dino_notification(dino.id, 'broke_accessory', item_id=p.shield["item_id"])
                        else:
                            shield_doc.items_data["abilities"]["endurance"] = new_dur
                            await shield_doc.save()

        # 2. Sync Used Healing Items (remove them from player inventories)
        for owner_id, items_used in self.consumed_items.items():
            try:
                user_id = int(owner_id)
            except ValueError:
                # Not a user ID, skip
                continue

            for item_id, count_used in items_used.items():
                # We need the abilities dictionary of the item to remove it.
                # Let's find any item in user's inventory with this item_id and remove count_used of it.
                # Use standard RemoveItemFromUser helper
                await UseAutoRemove(user_id, {"item_id": item_id}, count_used)

def generate_opponents(
    count: int,
    preferred_types: Optional[List[str]] = None,
    total_danger: float = 1.0
) -> List[CombatParticipant]:
    """Generates count opponents from journey.json with danger scores."""
    # Load mobs from journey.json
    try:
        with open('bot/json/journey.json', encoding='utf-8') as f:
            journey_data = json.load(f)
            mobs_pool = journey_data.get("mobs", {})
    except Exception:
        mobs_pool = {"crocodile": {"loot": ["skin", "bone"]}}

    # Load strategy weapons/shields from mob_weapon.json
    try:
        with open('bot/json/mob_weapon.json', encoding='utf-8') as f:
            mob_weapon_data = json.load(f)
    except Exception:
        mob_weapon_data = {}

    # Determine types
    types = []
    if preferred_types:
        for t_name in preferred_types:
            if t_name in mobs_pool:
                types.append(t_name)
    
    # Fill remaining count with random mobs
    while len(types) < count:
        types.append(random.choice(list(mobs_pool.keys())))

    # Distribute danger points evenly or with slight variance
    danger_share = total_danger / count
    participants = []

    mobs_cfg = COMBAT_SETTINGS.get("mobs_default_stats", {
        "hp": {"min": 60, "max": 160},
        "energy": {"min": 50, "max": 100},
        "damage": {"min": 3, "max": 12},
        "reflection": {"min": 0, "max": 5},
        "evasion": {"min": 0.05, "max": 0.25},
        "intelligence": {"min": 1, "max": 20}
      })

    for i, t_name in enumerate(types):
        D = danger_share * random.uniform(0.8, 1.2)
        D = max(0.0, min(1.0, D))
        
        # Scale stats
        hp_min, hp_max = mobs_cfg["hp"]["min"], mobs_cfg["hp"]["max"]
        max_hp = hp_min + D * (hp_max - hp_min)
        
        e_min, e_max = mobs_cfg["energy"]["min"], mobs_cfg["energy"]["max"]
        max_energy = e_min + D * (e_max - e_min)
        
        dmg_min_cfg = mobs_cfg["damage"]["min"]
        dmg_max_cfg = mobs_cfg["damage"]["max"]
        dmg_min = dmg_min_cfg + D * (dmg_min_cfg * 0.5)
        dmg_max = dmg_max_cfg + D * (dmg_max_cfg * 0.5)
        
        refl_min, refl_max = mobs_cfg["reflection"]["min"], mobs_cfg["reflection"]["max"]
        refl = refl_min + D * (refl_max - refl_min)
        
        eva_min, eva_max = mobs_cfg["evasion"]["min"], mobs_cfg["evasion"]["max"]
        eva = eva_min + D * (eva_max - eva_min)
        
        itl_min, itl_max = mobs_cfg["intelligence"]["min"], mobs_cfg["intelligence"]["max"]
        intel = itl_min + D * (itl_max - itl_min)

        # Role select first to determine gear choices
        role = random.choices(["carry", "tank", "support"], weights=[40, 40, 20])[0]

        # Weapon selection from role-specific choices in mob_weapon.json
        weapon = None
        role_weapons = mob_weapon_data.get(role, {}).get("weapons", [])
        eligible_weapons = [w for w in role_weapons if w.get("min_danger", 0.0) <= D <= w.get("max_danger", 1.0)]
        if eligible_weapons and random.random() < D:
            weapon_entry = random.choice(eligible_weapons)
            abilities = weapon_entry.get("abilities", {}).copy()
            if "lvl" not in abilities:
                abilities["lvl"] = int(D * 5)
            if "endurance" not in abilities:
                abilities["endurance"] = int(50 + D * 100)
            weapon = {
                "item_id": weapon_entry["item_id"],
                "abilities": abilities
            }

        # Shield selection from role-specific choices in mob_weapon.json
        shield = None
        role_shields = mob_weapon_data.get(role, {}).get("shields", [])
        eligible_shields = [s for s in role_shields if s.get("min_danger", 0.0) <= D <= s.get("max_danger", 1.0)]
        if eligible_shields and random.random() < D:
            shield_entry = random.choice(eligible_shields)
            abilities = shield_entry.get("abilities", {}).copy()
            if "lvl" not in abilities:
                abilities["lvl"] = int(D * 5)
            if "endurance" not in abilities:
                abilities["endurance"] = int(50 + D * 100)
            shield = {
                "item_id": shield_entry["item_id"],
                "abilities": abilities
            }

        stats = {
            "power": 5 + D * 10,
            "dexterity": 5 + D * 10,
            "intelligence": intel,
            "charisma": 5 + D * 10,
            "damage_range": {"min": dmg_min, "max": dmg_max},
            "reflection": refl,
            "evasion": eva * 100.0
        }

        mob_info = mobs_pool.get(t_name, {"loot": ["skin", "bone"]})

        part = CombatParticipant(
            unique_id=f"mob_{t_name}_{uuid.uuid4().hex[:6]}",
            name=f"{t_name.capitalize()}",
            participant_type="mob",
            max_hp=max_hp,
            hp=max_hp,
            max_energy=max_energy,
            energy=max_energy,
            stats=stats,
            role=role,
            weapon=weapon,
            shield=shield,
            original_obj=mob_info,
            danger_point=D,
            mob_id=t_name
        )
        participants.append(part)

    return participants
