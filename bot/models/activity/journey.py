from typing import Dict, Any, Optional, List, Union, ClassVar
from bson.objectid import ObjectId
import time
import json
from random import choice, choices, randint, random
from pydantic import Field
from beanie import PydanticObjectId
from bot.models.activity.base import Activity
from bot.modules.overwriting.DataCalsses import Transaction
from bot.models.dinosaur import Dino
from bot.models.user import User

# Load journey configs
try:
    with open('bot/json/mobs.json', encoding='utf-8') as f: 
        JOURNEY_DATA = json.load(f)
except Exception:
    JOURNEY_DATA = {}

try:
    with open('bot/json/journey_config.json', encoding='utf-8') as f:
        JOURNEY_CONFIG = json.load(f)
except Exception:
    JOURNEY_CONFIG = {}

events = JOURNEY_CONFIG.get('events', {})
locations = JOURNEY_CONFIG.get('locations', {})
chance = JOURNEY_CONFIG.get('chance', {})
rarity_lvl = JOURNEY_CONFIG.get('rarity_lvl', [])

SUB_LOCATIONS = JOURNEY_CONFIG.get('sub_locations', {})
choice_events_pool = []
for ev_key, ev_data in events.items():
    if ev_data.get("is_choice"):
        choice_events_pool.append({
            "key": ev_key,
            "options_count": ev_data.get("options_count", 2),
            "outcomes": ev_data.get("outcomes", [])
        })

class JourneyActivity(Activity):
    _processing = False

    userid: int = 0
    location: str = "forest"
    items: List[Any] = Field(default_factory=list)
    coins: int = 0
    friend: Optional[Any] = None

    dino_ids: List[PydanticObjectId] = Field(default_factory=list)
    bag: List[Dict[str, Any]] = Field(default_factory=list)
    pregenerated_events: List[Dict[str, Any]] = Field(default_factory=list)
    route_path: List[Dict[str, Any]] = Field(default_factory=list)
    status_message_id: Optional[int] = None  # Telegram message ID of the active status message

    @property
    def completed_log(self) -> List[Dict[str, Any]]:
        log_entries = []
        for ev in self.pregenerated_events:
            status = ev.get("status")
            if status in ["completed", "waiting_choice"]:
                if ev.get("type") == "choice" and status != "completed":
                    continue
                entry = ev.get("event_data", {}).copy()
                entry["type"] = entry.get("type", ev.get("type"))
                
                if ev.get("type") == "choice":
                    if status == "completed":
                        entry["type"] = "choice_resolution"
                    else:
                        entry["type"] = "choice"
                elif ev.get("type") == "autofeed":
                    entry["type"] = "autofeed"
                elif ev.get("type") == "battle":
                    entry["type"] = "battle"
                
                entry["tick_index"] = ev.get("tick_index")
                entry["trigger_time"] = ev.get("trigger_time")
                log_entries.append(entry)
        return log_entries
    @classmethod
    async def start(cls, dino_ids: List[ObjectId], owner_id: int, duration: int = 1800, location: str = 'forest', bag_items: List[dict] = None) -> bool:
        from pymongo.errors import DuplicateKeyError
        from bot.models.user import User

        if bag_items is None:
            bag_items = []
            
        # Check if any dino is already busy
        for d_id in dino_ids:
            existing = await Activity.find_one(Activity.dino.id == d_id)
            if existing:
                return False

        user_obj = await User.find_one(User.userid == owner_id)
        if not user_obj:
            return False

        dino_obj = await Dino.find_one(Dino.id == dino_ids[0])
        if not dino_obj:
            return False

        start_time = int(time.time())
        end_time = start_time + duration

        # Pregenerate event path
        pregenerated, route_path = await cls.pregenerate_path(dino_ids, duration, location, bag_items, start_time, owner_id)

        act = cls(
            dino=dino_obj,
            activity_type="journey",
            userid=owner_id,
            location=location,
            items=[],
            coins=0,
            start_time=start_time,
            end_time=end_time,
            dino_ids=dino_ids,
            bag=bag_items,
            pregenerated_events=pregenerated,
            route_path=route_path
        )
        try:
            await act.insert()
            pending_events = [ev for ev in act.pregenerated_events if ev.get("status") == "pending"]
            first_ev_time, first_ev_tick = None, None
            if pending_events:
                pending_events.sort(key=lambda x: x.get("trigger_time", 0))
                first_ev_time = pending_events[0]["trigger_time"]
                first_ev_tick = pending_events[0]["tick_index"]
            await cls.create_task(act.id, act.end_time, first_ev_time, first_ev_tick)
            # Инвалидируем кеш статуса для всех динозавров путешествия
            from bot.modules.dino_status_cache import invalidate_status_cache
            for _did in dino_ids:
                await invalidate_status_cache(_did)

            # Логируем начало путешествия для статистики
            try:
                import json
                from bot.redismanager import get_redis
                redis = get_redis()
                await redis.rpush("global_journeys_today", json.dumps({
                    "userid": owner_id,
                    "location": location,
                    "timestamp": start_time
                }))
            except Exception as e:
                log(f"Failed to log journey start to Redis: {e}", 3)
        except DuplicateKeyError:
            return False

        return True

    @classmethod
    async def calculate_event_chance(cls, event_key: str, event_data: dict, dinos: list, bag: list, triggered_keys: set, location: str = "", owner_id: int = 0) -> float:
        if event_key in ["friend_meeting", "friend_gift", "friend_coop"]:
            if not owner_id or not location:
                return 0.0
            from bot.modules.user.friends import get_frineds
            friends_data = await get_frineds(owner_id)
            friends_list = friends_data.get("friends", [])
            if not friends_list:
                return 0.0
            from bot.models.user import User
            from beanie.operators import In
            friend_users = await User.find(In(User.userid, friends_list)).to_list()
            friend_user_ids = [fu.id for fu in friend_users]
            active_friends_in_loc = await cls.find({
                "location": location,
                "user.id": {"$in": friend_user_ids}
            }).to_list()
            if not active_friends_in_loc:
                return 0.0

        from random import uniform
        chance_cfg = event_data.get("chance_config", {})
        c_type = chance_cfg.get("type", "static")
        base = chance_cfg.get("base", 0.5)

        if c_type == "static":
            return base
        elif c_type == "random":
            return uniform(chance_cfg.get("min", 0.1), chance_cfg.get("max", 0.9))
        elif c_type == "dino_stat":
            stat = chance_cfg.get("stat", "intelligence")
            mult = chance_cfg.get("multiplier", 0.0)
            max_stat_val = 0.0
            for d in dinos:
                val = d.stats.get(stat, 0.0)
                if val > max_stat_val:
                    max_stat_val = val
            return max(0.0, base + max_stat_val * mult)
        elif c_type == "item":
            item_id = chance_cfg.get("item_id")
            bonus = chance_cfg.get("bonus", 0.0)
            item_present = False
            for b_item in bag:
                if b_item.get("item_id") == item_id and b_item.get("count", 0) > 0:
                    item_present = True
                    break
            return base + bonus if item_present else base
        elif c_type == "history":
            req_ev = chance_cfg.get("required_event")
            bonus = chance_cfg.get("bonus", 0.0)
            has_history = req_ev in triggered_keys
            return base + bonus if has_history else base
        return base

    @classmethod
    def roll_items_to_add(cls, items_add_cfg: list) -> list:
        from random import random, randint, choices, choice
        items_to_add = []
        if not items_add_cfg:
            return items_to_add
        for it in items_add_cfg:
            if isinstance(it, str):
                from bot.modules.items.item import get_data as get_item_data
                item_data = get_item_data(it)
                abilities = {}
                if item_data.get("type") in ["weapon", "armor"] and it.startswith("shield_") or item_data.get("type") == "weapon":
                    if random() <= 0.4:
                        from bot.modules.items.item import get_item_endurance_max
                        lvl = choices([0, 1, 2], weights=[70, 20, 10])[0]
                        max_end = get_item_endurance_max({"item_id": it, "abilities": {"lvl": lvl}}) or 100
                        min_end = max(1, int(max_end * 0.01))
                        endurance_val = randint(min_end, max(min_end, int(max_end * 0.4)))
                        abilities = {"endurance": endurance_val, "lvl": lvl}
                items_to_add.append({
                    "item_id": it,
                    "count": 1,
                    "abilities": abilities
                })
                continue
            
            if not isinstance(it, dict):
                continue
            
            # Roll drop chance
            chance = it.get("chance", 1.0)
            if random() > chance:
                continue
                
            # Determine item_id
            item_id = None
            if "item_id" in it:
                item_id = it["item_id"]
            elif "group" in it:
                from bot.modules.items.items_groups import get_group
                group_items = get_group(it["group"])
                if group_items:
                    item_id = choice(group_items)
            elif "pool" in it:
                pool = it["pool"]
                if pool:
                    item_ids = [p.get("item_id") for p in pool]
                    weights = [p.get("weight", 100) for p in pool]
                    item_id = choices(item_ids, weights=weights)[0]
            
            if not item_id:
                continue
                
            # Determine count
            count_cfg = it.get("count", 1)
            count = 1
            if isinstance(count_cfg, int):
                count = count_cfg
            elif isinstance(count_cfg, dict):
                c_type = count_cfg.get("type", "static")
                if c_type == "random":
                    count = randint(count_cfg.get("min", 1), count_cfg.get("max", 1))
                else:
                    count = count_cfg.get("base", 1)
            
            # Extract abilities
            abilities = it.get("abilities", {}).copy()
            
            from bot.modules.items.item import get_data as get_item_data
            item_data = get_item_data(item_id)
            if item_data.get("type") in ["weapon", "armor"] and item_id.startswith("shield_") or item_data.get("type") == "weapon":
                if random() <= 0.4:
                    from bot.modules.items.item import get_item_endurance_max
                    lvl = choices([0, 1, 2], weights=[70, 20, 10])[0]
                    abilities["lvl"] = lvl
                    max_end = get_item_endurance_max({"item_id": item_id, "abilities": {"lvl": lvl}}) or 100
                    min_end = max(1, int(max_end * 0.01))
                    abilities["endurance"] = randint(min_end, max(min_end, int(max_end * 0.4)))
            
            items_to_add.append({
                "item_id": item_id,
                "count": count,
                "abilities": abilities
            })

        # Add a general small chance (6%) of finding a special item whenever items are rolled:
        if random() <= 0.06:
            r = random()
            if r <= 0.1:  # 0.6% total
                items_to_add.append({
                    "item_id": "stone_resurrection",
                    "count": 1,
                    "abilities": {}
                })
            elif r <= 0.2:  # 0.6% total
                items_to_add.append({
                    "item_id": "transport_egg",
                    "count": 1,
                    "abilities": {}
                })
            elif r <= 0.6:  # 2.4% total
                rune_id = choice(["rune_lvl1", "rune_lvl2", "rune_lvl3", "rune_lvl4", "rune_lvl5"])
                items_to_add.append({
                    "item_id": rune_id,
                    "count": 1,
                    "abilities": {}
                })
            else:  # 2.4% total
                combat_keys = ["blade_regular", "blade_bleed", "hammer_regular", "hammer_heavy", 
                               "spear_regular", "spear_piercing", "bow_regular", "bow_hunting", 
                               "crossbow_regular", "crossbow_heavy", "sword_regular", "sword_hero", 
                               "staff_regular", "staff_druid", "axe_regular", "axe_executioner",
                               "shield_wooden", "shield_buckler", "shield_iron", "shield_magical"]
                item_id = choice(combat_keys)
                lvl = choices([0, 1, 2], weights=[70, 20, 10])[0]
                items_to_add.append({
                    "item_id": item_id,
                    "count": 1,
                    "abilities": {
                        "endurance": 0,
                        "lvl": lvl
                    }
                })
        return items_to_add

    @classmethod
    async def pregenerate_path(cls, dino_ids: List[ObjectId], duration: int, location: str, bag: List[dict], start_time: int, owner_id: int):
        from random import choice, choices, randint, random

        interval = 300  # 5 minutes
        ticks_count = duration // interval
        
        # Add main location entry log at tick 0
        pregenerated = [
            {
                "tick_index": 0,
                "trigger_time": start_time,
                "status": "completed",
                "type": "standard",
                "event_data": {
                    "type": "enter_main_location",
                    "location": location,
                    "depth": 0
                }
            }
        ]
        route_path = [{"type": "location", "name": location, "depth": 0}]

        # Load all dinosaurs
        dinos = []
        for d_id in dino_ids:
            dino = await Dino().create(d_id)
            if dino:
                dinos.append(dino)

        # Track history of triggered event keys
        triggered_keys = set()

        middle_tick = ticks_count // 2
        
        # Stack elements: {"sub_loc": sub_loc, "ticks": sub_loc_ticks, "depth": depth}
        sub_loc_stack = []

        # General base chance of an event triggering in a tick
        base_trigger_chance = 0.6
        hiking_bag = None
        for item in bag:
            if item.get("item_id") == "hiking_bag" and item.get("count", 0) > 0:
                hiking_bag = item
                break
        if hiking_bag:
            lvl = hiking_bag.get("abilities", {}).get("lvl", 0)
            base_trigger_chance += 0.3 + lvl * 0.05

        for tick_idx in range(1, ticks_count + 1):
            trigger_time = start_time + tick_idx * interval

            # 1. Choice Event at the middle
            if tick_idx == middle_tick:
                choice_event = choice(choice_events_pool).copy()
                current_sub = sub_loc_stack[-1]["sub_loc"] if sub_loc_stack else None
                current_depth = sub_loc_stack[-1]["depth"] if sub_loc_stack else 0
                if current_sub:
                    choice_event["sub_location"] = current_sub
                    choice_event["depth"] = current_depth

                pregenerated.append({
                    "tick_index": tick_idx,
                    "trigger_time": trigger_time,
                    "status": "pending",
                    "type": "choice",
                    "event_data": choice_event
                })
                route_path.append({"type": "choice", "name": choice_event["key"], "depth": current_depth})
                continue

            # 2. Sub-location transitions check
            if sub_loc_stack:
                # Decrement ticks of the top sub-location
                sub_loc_stack[-1]["ticks"] -= 1
                
                # Check if the current sub-location has expired
                if sub_loc_stack[-1]["ticks"] <= 0:
                    expired_sub = sub_loc_stack.pop()
                    
                    # Exit sub-location event
                    pregenerated.append({
                        "tick_index": tick_idx,
                        "trigger_time": trigger_time,
                        "status": "pending",
                        "type": "standard",
                        "event_data": {
                            "type": f"exit_{expired_sub['sub_loc']}",
                            "location": location,
                            "sub_location": expired_sub["sub_loc"],
                            "depth": expired_sub["depth"]
                        }
                    })
                    
                    # Log returning to parent location / sub-location
                    if sub_loc_stack:
                        parent_sub = sub_loc_stack[-1]["sub_loc"]
                        parent_depth = sub_loc_stack[-1]["depth"]
                        route_path.append({
                            "type": "sub_location",
                            "name": parent_sub,
                            "depth": parent_depth
                        })
                    else:
                        last_loc = None
                        for node in reversed(route_path):
                            if node.get("type") == "location":
                                last_loc = node.get("name")
                                break
                        if last_loc != location:
                            route_path.append({
                                "type": "location",
                                "name": location,
                                "depth": 0
                            })
                    continue
                else:
                    # Still inside the top sub-location
                    current_sub_data = sub_loc_stack[-1]
                    active_sub_loc = current_sub_data["sub_loc"]
                    active_depth = current_sub_data["depth"]
                    
                    # Roll transition to an even deeper sub-location (nesting)
                    loc_sub_locs = locations.get(location, {}).get("sub_locations", [])
                    active_subs_in_stack = {s["sub_loc"] for s in sub_loc_stack}
                    available_subs = [s for s in loc_sub_locs if s not in active_subs_in_stack]
                    
                    if len(sub_loc_stack) < 3 and random() <= 0.15 and available_subs:
                        new_sub = choice(available_subs)
                        new_ticks = randint(2, 4)
                        new_depth = len(sub_loc_stack) + 1
                        
                        pregenerated.append({
                            "tick_index": tick_idx,
                            "trigger_time": trigger_time,
                            "status": "pending",
                            "type": "standard",
                            "event_data": {
                                "type": f"enter_{new_sub}",
                                "location": location,
                                "sub_location": new_sub,
                                "depth": new_depth
                            }
                        })
                        
                        sub_loc_stack.append({
                            "sub_loc": new_sub,
                            "ticks": new_ticks,
                            "depth": new_depth
                        })
                        
                        route_path.append({
                            "type": "sub_location",
                            "name": new_sub,
                            "depth": new_depth
                        })
                        continue
                    else:
                        # Standard event generation inside the active sub-location
                        pool = SUB_LOCATIONS.get(active_sub_loc, {}).get("events", [])
            else:
                # We are in the main location. Roll transition to a sub-location (depth 1)
                if random() <= 0.15:
                    loc_sub_locs = locations.get(location, {}).get("sub_locations", [])
                    if loc_sub_locs:
                        new_sub = choice(loc_sub_locs)
                        new_ticks = randint(2, 4)
                        new_depth = 1
                        
                        pregenerated.append({
                            "tick_index": tick_idx,
                            "trigger_time": trigger_time,
                            "status": "pending",
                            "type": "standard",
                            "event_data": {
                                "type": f"enter_{new_sub}",
                                "location": location,
                                "sub_location": new_sub,
                                "depth": new_depth
                            }
                        })
                        
                        sub_loc_stack.append({
                            "sub_loc": new_sub,
                            "ticks": new_ticks,
                            "depth": new_depth
                        })
                        
                        route_path.append({
                            "type": "sub_location",
                            "name": new_sub,
                            "depth": new_depth
                        })
                        continue
                
                pool = locations.get(location, {}).get("events", [])

            # 3. Trigger standard event
            current_sub = sub_loc_stack[-1]["sub_loc"] if sub_loc_stack else None
            current_depth = sub_loc_stack[-1]["depth"] if sub_loc_stack else 0

            # Roll for battle based on location danger (only in main location)
            danger = locations.get(location, {}).get("danger", 1.0)
            battle_chance = 0.15 * danger
            mobs_cfg = locations.get(location, {}).get("mobs", {})
            mob_names = mobs_cfg.get("mobs", [])
            if not sub_loc_stack and mob_names and random() <= battle_chance:
                mob_count = 1 if danger <= 1.1 else randint(1, 2)
                mobs_list = [choice(mob_names) for _ in range(mob_count)]
                pregenerated.append({
                    "tick_index": tick_idx,
                    "trigger_time": trigger_time,
                    "status": "pending",
                    "type": "battle",
                    "event_data": {
                        "type": "battle",
                        "location": location,
                        "sub_location": current_sub,
                        "depth": current_depth,
                        "mobs": mobs_list
                    }
                })
                continue
            
            # Guarantee at least one event in sub-locations by forcing 100% trigger chance
            trigger_chance = 1.0 if sub_loc_stack else base_trigger_chance
            if random() <= trigger_chance:
                eligible_events = []
                weights = []
                for ev_key in pool:
                    ev_data = events.get(ev_key, {})
                    w = await cls.calculate_event_chance(ev_key, ev_data, dinos, bag, triggered_keys, location, owner_id)
                    if w > 0:
                        eligible_events.append(ev_key)
                        weights.append(w)

                if eligible_events:
                    # Exclude is_choice events from standard pool - they only appear in middle_tick
                    selected_ev_key = choices(eligible_events, weights=weights)[0]
                    ev_cfg = events.get(selected_ev_key, {})
                    if ev_cfg.get("is_choice"):
                        # Skip – re-roll or just skip this tick
                        continue
                    triggered_keys.add(selected_ev_key)

                    if selected_ev_key in ["battle", "cave_bat", "oasis_camel", "shark_attack"]:
                        if selected_ev_key == "cave_bat":
                            mobs_list = ["bat"]
                        elif selected_ev_key == "oasis_camel":
                            mobs_list = ["camel"]
                        elif selected_ev_key == "shark_attack":
                            mobs_list = ["shark"]
                        else:
                            danger = locations.get(location, {}).get("danger", 1.0)
                            mobs_cfg = locations.get(location, {}).get("mobs", {})
                            mob_names = mobs_cfg.get("mobs", ["crocodile"])
                            mob_count = 1 if danger <= 1.1 else randint(1, 2)
                            mobs_list = [choice(mob_names) for _ in range(mob_count)]
                        pregenerated.append({
                            "tick_index": tick_idx,
                            "trigger_time": trigger_time,
                            "status": "pending",
                            "type": "battle",
                            "event_data": {
                                "type": selected_ev_key,
                                "location": location,
                                "sub_location": current_sub,
                                "depth": current_depth,
                                "mobs": mobs_list
                            }
                        })
                    else:
                        ev_data = events.get(selected_ev_key, {})
                        outcomes = ev_data.get("outcomes", [])
                        
                        selected_outcome = None
                        # Check each outcome for requirement match
                        for out in outcomes:
                            reqs = out.get("requirements")
                            if not reqs:
                                continue
                            
                            # 1. Check item requirement
                            if "item_id" in reqs:
                                req_item = reqs["item_id"]
                                req_count = reqs.get("count", 1)
                                has_qty = 0
                                for bag_item in bag:
                                    if bag_item.get("item_id") == req_item:
                                        has_qty += bag_item.get("count", 0)
                                if has_qty < req_count:
                                    continue
                                # Consume items if needed
                                if reqs.get("consume_item"):
                                    rem = req_count
                                    for bag_item in bag:
                                        if bag_item.get("item_id") == req_item:
                                            cnt = bag_item.get("count", 0)
                                            if cnt >= rem:
                                                bag_item["count"] -= rem
                                                break
                                            else:
                                                rem -= cnt
                                                bag_item["count"] = 0
                            
                            # 2. Check stats requirement
                            if "stat" in reqs:
                                stat_reqs = reqs["stat"]
                                match_stats = True
                                for d in dinos:
                                    for s_name, s_val in stat_reqs.items():
                                        val = d.stats.get(s_name)
                                        if val is None:
                                            combat_caps = await d.get_combat_capabilities()
                                            val = combat_caps.get(s_name, 0)
                                        if val < s_val:
                                            match_stats = False
                                            break
                                    if not match_stats:
                                        break
                                if not match_stats:
                                    continue
                            
                            # 3. Check chance requirement
                            if "chance" in reqs:
                                if random() > reqs["chance"]:
                                    continue
                            
                            # Requirements met! Success / Fail check
                            succ_chance = reqs.get("success_chance", 1.0)
                            if random() <= succ_chance:
                                selected_outcome = out.get("success", out)
                            else:
                                selected_outcome = out.get("fail", out)
                            break
                        
                        if not selected_outcome:
                            # Fallback to standard weighted outcome
                            fallback_outcomes = [out for out in outcomes if "requirements" not in out]
                            if fallback_outcomes:
                                out_weights = [out.get("weight", 100) for out in fallback_outcomes]
                                selected_outcome = choices(fallback_outcomes, weights=out_weights)[0]
                            else:
                                selected_outcome = {"story_key": "success"}

                        affected_dino = choice(dinos) if dinos else None
                        items_add = cls.roll_items_to_add(selected_outcome.get("items_add", []))

                        event_dict = {
                            "type": selected_ev_key,
                            "location": location,
                            "sub_location": current_sub,
                            "depth": current_depth,
                            "story_key": selected_outcome.get("story_key", "success"),
                            "affected_dino_id": str(affected_dino.id) if affected_dino else None,
                            "dino_edit": selected_outcome.get("dino_edit", {}),
                            "coins": selected_outcome.get("coins", 0),
                            "items_add": items_add,
                            "items_remove": selected_outcome.get("items_remove", [])
                        }

                        if "change_location" in selected_outcome:
                            location = selected_outcome["change_location"]
                            event_dict["change_location"] = location
                            route_path.append({
                                "type": "location",
                                "name": location,
                                "depth": 0
                            })

                        # Friend details resolution for friend events
                        if selected_ev_key in ["friend_meeting", "friend_gift", "friend_coop"]:
                            from bot.modules.user.friends import get_frineds
                            from bot.models.user import User
                            friend_owner_name = None
                            friend_dino_name = None
                            
                            friends_data = await get_frineds(owner_id)
                            friends_list = friends_data.get("friends", [])
                            if friends_list:
                                friend_users = await User.find(User.userid.in_(friends_list)).to_list()
                                friend_user_ids = [fu.userid for fu in friend_users]
                                active_friends_in_loc = await cls.find({
                                    "location": location,
                                    "userid": {"$in": friend_user_ids}
                                }).to_list()
                                active_friends_in_loc = [f for f in active_friends_in_loc if f.end_time > int(time.time())]
                                if active_friends_in_loc:
                                    selected_friend_journey = choice(active_friends_in_loc)
                                    friend_id = selected_friend_journey.userid
                                    if friend_id and selected_friend_journey.dino_ids:
                                        from bot.models.user import User as UserModel
                                        friend_user = await UserModel.find_one(UserModel.userid == friend_id)
                                        friend_owner_name = (friend_user.name if friend_user else None) or f"User_{friend_id}"
                                        friend_dino_id = selected_friend_journey.dino_ids[0]
                                        friend_dino = await Dino.find_one(Dino.id == friend_dino_id)
                                        if friend_dino:
                                            friend_dino_name = friend_dino.name
                                            try:
                                                from bot.models.user import DinoCollection
                                                await DinoCollection.add_to_collection(owner_id, friend_dino.data_id)
                                            except Exception:
                                                pass

                            if not friend_owner_name:
                                continue
                            
                            event_dict["friend_owner_name"] = friend_owner_name
                            event_dict["friend_dino_name"] = friend_dino_name

                        pregenerated.append({
                            "tick_index": tick_idx,
                            "trigger_time": trigger_time,
                            "status": "pending",
                            "type": "standard",
                            "event_data": event_dict
                        })

        return pregenerated, route_path

    @classmethod
    async def end(cls, dino_id: ObjectId):
        from bot.models.user import User
        from bot.modules.items.item import AddItemToUser
        from bot.modules.logs import log
        from bot.redismanager import redis_set, redis_get
        
        act = await cls.get(dino_id)
        if not act:
            act = await cls.find_one(cls.dino_ids == ObjectId(dino_id))
        if not act:
            act = await cls.find_one(cls.dino.id == ObjectId(dino_id))

        if act:
            owner_id = act.userid
            owner_user = await User.find_one(User.userid == owner_id)
            async with Transaction():
                # Delete active/waiting choice messages if any
                for ev in act.pregenerated_events:
                    if ev.get("type") == "choice" and ev.get("message_id"):
                        try:
                            from bot.exec import bot
                            await bot.delete_message(chat_id=owner_id, message_id=ev["message_id"])
                        except Exception:
                            pass

                # 1. Return remaining items in the bag to user (this includes both leftovers and found items)
                for bag_item in act.bag:
                    cnt = bag_item.get("count", 0)
                    if cnt > 0 and owner_id:
                        await AddItemToUser(owner_id, bag_item.get("item_id"), cnt, bag_item.get("abilities", {}))

                # 2. Add coins to user
                if owner_user:
                    await owner_user.add_coins(act.coins)

                log(f"Edit coins: user: {owner_id} col: {act.coins}", 0, "take_coins")

                # 3. Save to Redis Completed Journeys History (distinct TTL by premium status)
                journey_id_str = str(act.id)
                duration = act.end_time - act.start_time
                
                dino_names = []
                for d_id in act.dino_ids:
                    dino_obj = await Dino.find_one(Dino.id == d_id)
                    if dino_obj:
                        dino_names.append(dino_obj.name)
                dinos_text = ", ".join(dino_names)

                # Clean and optimize journey log size
                clean_log = []
                for entry in act.completed_log:
                    clean_entry = {}
                    for k in ["type", "location", "sub_location", "story_key", "dino_edit", 
                              "coins", "items_add", "items_remove", "remove_items", "winner", 
                              "dinos_status", "mobs", "replic", "choice_key", "success", 
                              "expired", "option_idx", "affected_dino_id", "change_location",
                              "key", "tick_index", "trigger_time"]:
                        if k in entry:
                            clean_entry[k] = entry[k]
                    clean_log.append(clean_entry)

                history_details = {
                    "id": journey_id_str,
                    "location": act.location,
                    "duration": duration,
                    "start_time": act.start_time,
                    "end_time": act.end_time,
                    "coins": act.coins,
                    "items": act.items,
                    "dinos": dinos_text,
                    "dino_names_list": dino_names,
                    "journey_log": clean_log,
                    "route_path": getattr(act, "route_path", [])
                }
                
                from bot.modules.user.premium import premium
                is_prem = await premium(owner_id) if owner_id else False
                history_ttl = 7776000 if is_prem else 604800

                await redis_set(f"journey_details:{journey_id_str}", history_details, ex=history_ttl)

                user_journeys_key = f"user_journeys:{owner_id}"
                history_list = await redis_get(user_journeys_key) or []

                current_time = int(time.time())
                history_list = [h for h in history_list if current_time - h.get("time_end", 0) < history_ttl]
                history_list.append({
                    "id": journey_id_str,
                    "location": act.location,
                    "duration": duration,
                    "time_end": current_time,
                    "coins": act.coins,
                    "items_count": len(act.items)
                })

                await redis_set(user_journeys_key, history_list, ex=history_ttl)

                if owner_id:
                    visited_locations = [act.location]
                    for entry in act.completed_log:
                        if "location" in entry and entry["location"]:
                            visited_locations.append(entry["location"])
                    unique_visited = list(set(visited_locations))
                    from bot.models.user import User
                    user = await User.find_one(User.userid == owner_id)
                    if user:
                        if 'journey_count' not in user.settings:
                            user.settings['journey_count'] = 0
                        user.settings['journey_count'] += 1
                        await user.save()
                    from bot.modules.user.achievements import check_achievements
                    await check_achievements(owner_id, "journey_end", unique_visited)
                    await check_achievements(owner_id, "journey_end", duration)


                # Send end of journey notification to the user
                from bot.modules.localization import t, get_lang, get_data
                from bot.exec import bot
                from bot.modules.markup import markups_menu as m
                from bot.modules.data_format import seconds_to_str
                
                lang = await get_lang(owner_id) if owner_id else "en"
                dino_name = dinos_text if dino_names else t("journey.dinosaur_fallback", lang, default="dinosaur")
                
                # Generate route map
                map_lines = []
                for node in act.route_path:
                    node_type = node.get("type")
                    node_name = node.get("name")
                    depth = node.get("depth", 0)
                    indent = "  " * depth
                    if node_type == "location":
                        loc_data = get_data(f"journey_start.locations.{node_name}", lang)
                        loc_lbl = loc_data.get("name", node_name) if isinstance(loc_data, dict) else node_name
                        map_lines.append(f"{indent}📍 {loc_lbl}")
                    elif node_type == "sub_location":
                        sub_data = get_data(f"journey_start.sub_locations.{node_name}", lang)
                        sub_lbl = sub_data.get("name", node_name) if isinstance(sub_data, dict) else node_name
                        sub_emoji = sub_data.get("emoji", "🕳️") if isinstance(sub_data, dict) else "🕳️"
                        map_lines.append(f"{indent}↳ {sub_emoji} {sub_lbl}")
                    elif node_type == "choice":
                        choice_data = get_data(f"journey_choices.{node_name}", lang)
                        choice_lbl = choice_data.get("name", node_name) if isinstance(choice_data, dict) else node_name
                        if "no_text_key" in str(choice_lbl):
                            choice_lbl = t(f"journey_choices.{node_name}.text", lang)[:20] + "..."
                        choice_indent = "  " * (depth + 1)
                        map_lines.append(f"{choice_indent}↳ ❓ {choice_lbl}")
                
                route_map_str = "\n".join(map_lines)

                from bot.modules.items.item import counts_items
                items_str_raw = counts_items(act.items, lang) if act.items else "-"
                # Wrap each item name in backticks for visual formatting, excluding emojis
                def wrap_text_in_code(p: str) -> str:
                    import re
                    prefix_parts = []
                    rest = p
                    while True:
                        m_custom = re.match(r'^(!\[.*?\]\(tg://emoji\?id=\d+\)\s*)', rest)
                        if m_custom:
                            prefix_parts.append(m_custom.group(1))
                            rest = rest[len(m_custom.group(1)):]
                            continue
                        m_std = re.match(r'^([\u2600-\u27BF\U0001f300-\U0001f64F\U0001f680-\U0001f6FF\U0001f900-\U0001f9FF\U0001f1e0-\U0001f1ff]\s*)', rest)
                        if m_std:
                            prefix_parts.append(m_std.group(1))
                            rest = rest[len(m_std.group(1)):]
                            continue
                        m_sym = re.match(r'^([↳🔹⛺🐊🏛️❓🪨📍⏱🦖🪙🎒⏱]\s*)', rest)
                        if m_sym:
                            prefix_parts.append(m_sym.group(1))
                            rest = rest[len(m_sym.group(1)):]
                            continue
                        break
                    prefix = "".join(prefix_parts)
                    return f"{prefix}<code>{rest}</code>" if rest else prefix

                if act.items:
                    items_parts = [p.strip() for p in items_str_raw.split(',') if p.strip()]
                    items_str = ", ".join(wrap_text_in_code(p) for p in items_parts)
                else:
                    items_str = "-"
                log_key = "journey_log_plural" if len(dino_names) > 1 else "journey_log"
                notification_text = t(log_key, lang, 
                                      coins=act.coins, 
                                      items=items_str, 
                                      time=seconds_to_str(duration, lang), 
                                      col=len(act.completed_log), 
                                      name=dino_name)
                
                if route_map_str:
                    notification_text += f"\n\n{t('journey.route_map', lang, default='🗺️ <b>Journey Map:</b>')}\n{route_map_str}"

                try:
                    from bot.modules.data_format import list_to_inline
                    log_markup = list_to_inline([
                        {t("journey_menu.buttons.logs", lang): f"j_hlog:{journey_id_str}:1"}
                    ])
                    if owner_id:
                        # Build dino species list for photo
                        dino_species_ids = []
                        for d_id in act.dino_ids:
                            dino_obj_cached = await Dino.find_one(Dino.id == d_id)
                            if dino_obj_cached:
                                dino_species_ids.append(dino_obj_cached.data_id)

                        # Try editing the existing status message first
                        edited = False
                        if act.status_message_id:
                            try:
                                await bot.edit_message_caption(
                                    chat_id=owner_id,
                                    message_id=act.status_message_id,
                                    caption=notification_text,
                                    reply_markup=log_markup
                                )
                                edited = True
                            except Exception:
                                pass

                        if not edited:
                            try:
                                from bot.modules.images import dino_journey
                                photo_input = await dino_journey(dino_species_ids, act.location)
                                await bot.send_photo(owner_id, photo=photo_input,
                                                     caption=notification_text,
                                                     reply_markup=log_markup)
                            except Exception:
                                await bot.send_message(owner_id, notification_text,
                                                       reply_markup=log_markup)
                except Exception:
                    pass

                await act.delete()
                await cls.cancel_task(act.id)
                # Инвалидируем кеш статуса для всех участников путешествия
                from bot.modules.dino_status_cache import invalidate_status_cache
                for _did in (act.dino_ids or []):
                    await invalidate_status_cache(_did)
                if act.dino and act.dino.ref:
                    await invalidate_status_cache(act.dino.ref.id)


    JOURNEY_HP_FLOOR: ClassVar[int] = 10

    @classmethod
    def _eject_weak_dinos(cls, journey: "JourneyActivity", dinos: list, ev: dict) -> list:
        """Removes dinos at/below HP floor from journey.dino_ids and logs 'dino_left'.
        Returns list of ejected dinos."""
        ejected = []
        for d in dinos:
            if d.stats.get("heal", 100) <= cls.JOURNEY_HP_FLOOR:
                left_entry = {
                    "tick_index": ev.get("tick_index", -1),
                    "trigger_time": int(time.time()),
                    "status": "completed",
                    "type": "dino_left",
                    "event_data": {
                        "type": "dino_left",
                        "dino_name": d.name,
                        "dino_id": str(d.id),
                        "depth": ev.get("depth", 0),
                        "trigger_time": int(time.time()),
                        "tick_index": ev.get("tick_index", 0)
                    }
                }
                journey.pregenerated_events.append(left_entry)
                if d.id in journey.dino_ids:
                    journey.dino_ids.remove(d.id)
                ejected.append(d)
        return ejected

    @classmethod
    async def process_ticks(cls, current_time: int):
        active_journeys = await cls.find().to_list()
        for journey in active_journeys:
            await cls.process_journey_ticks(journey, current_time)

    @classmethod
    async def process_journey_ticks(cls, journey: "JourneyActivity", current_time: int, tick_index: Optional[int] = None):
        from bot.modules.logs import log
        from bot.modules.task_queue import enqueue_task
        try:
            has_waiting_choice = False
            for ev in journey.pregenerated_events:
                if ev.get("status") == "waiting_choice":
                    timeout = ev.get("timeout", 0)
                    if current_time >= timeout:
                        resolved = False
                        for opt_i in range(len(ev.get("event_data", {}).get("outcomes", []))):
                            try:
                                await cls.resolve_choice_event(journey, ev, option_idx=opt_i, expired=True)
                                resolved = True
                                break
                            except ValueError:
                                continue
                        if not resolved:
                            await cls.resolve_choice_event(journey, ev, option_idx=0, expired=True, force=True)
                    else:
                        has_waiting_choice = True
                    break

            if has_waiting_choice:
                return

            events_to_trigger = []
            for ev in journey.pregenerated_events:
                st = ev.get("status")
                if st == "pending":
                    if tick_index is not None:
                        if ev.get("tick_index") == tick_index:
                            events_to_trigger.append(ev)
                            break
                    else:
                        t_time = ev.get("trigger_time")
                        if t_time is not None and t_time <= current_time:
                            events_to_trigger.append(ev)

            log(prefix="journey", message=f"  journey {journey.id}: {len(events_to_trigger)} events to trigger", lvl=0)
            events_to_trigger.sort(key=lambda x: x.get("trigger_time", 0))
            
            for ev in events_to_trigger:
                for stored_ev in journey.pregenerated_events:
                    if stored_ev.get("tick_index") == ev.get("tick_index"):
                        stored_ev["status"] = "active"
                        ev = stored_ev
                        break
                await journey.save()

                try:
                    if ev.get("type") == "standard":
                        await cls.trigger_standard_event(journey, ev)
                        # Fire journey_event_seen achievement trigger
                        event_key = ev.get("event_data", {}).get("event_key") or ev.get("event_key")
                        if event_key and journey.userid:
                            from bot.modules.user.achievements import check_achievements
                            await check_achievements(journey.userid, "journey_event_seen", event_key)
                    elif ev.get("type") == "battle":
                        await cls.trigger_battle_event(journey, ev)
                    elif ev.get("type") == "choice":
                        await cls.trigger_choice_event(journey, ev)
                        break
                except Exception as trigger_exc:
                    log(prefix="journey", message=f"Error triggering event {ev.get('type')}: {trigger_exc}", lvl="error")
                    for stored_ev in journey.pregenerated_events:
                        if stored_ev.get("tick_index") == ev.get("tick_index"):
                            stored_ev["status"] = "pending"
                            break
                    await journey.save()
                    break

            # Reload to get fresh state
            journey = await cls.find_one(cls.id == journey.id)
            if not journey:
                return

            has_waiting_choice = False
            for ev in journey.pregenerated_events:
                if ev.get("status") == "waiting_choice":
                    has_waiting_choice = True
                    break

            if not has_waiting_choice:
                pending_events = [ev for ev in journey.pregenerated_events if ev.get("status") == "pending"]
                if pending_events:
                    pending_events.sort(key=lambda x: x.get("trigger_time", 0))
                    next_ev = pending_events[0]
                    await enqueue_task("journey_event", {
                        "journey_id": str(journey.id),
                        "tick_index": next_ev["tick_index"]
                    }, run_at=next_ev["trigger_time"], resource_id=f"journey_event:{journey.id}")

        except Exception as exc:
            log(prefix="journey", message=f"process_journey_ticks error: {exc}", lvl="error")


    @classmethod
    async def downgrade_bag_item(cls, bag: List[dict], item_id: str, amount: int = 2) -> bool:
        from bot.modules.items.item import get_item_endurance_max, get_data
        for item in bag:
            if item.get("item_id") == item_id and item.get("count", 0) > 0:
                if "abilities" not in item or not isinstance(item["abilities"], dict):
                    item["abilities"] = {}
                if "endurance" not in item["abilities"]:
                    max_end = get_item_endurance_max(item)
                    if max_end is None:
                        item_static = get_data(item_id)
                        max_end = item_static.get("endurance_max", 100) if isinstance(item_static, dict) else 100
                    item["abilities"]["endurance"] = max_end

                item["abilities"]["endurance"] -= amount
                if item["abilities"]["endurance"] <= 0:
                    item["count"] -= 1
                    if item["count"] > 0:
                        max_end = get_item_endurance_max(item)
                        if max_end is None:
                            item_static = get_data(item_id)
                            max_end = item_static.get("endurance_max", 100) if isinstance(item_static, dict) else 100
                        item["abilities"]["endurance"] = max_end
                    else:
                        item["abilities"]["endurance"] = 0
                return True
        return False

    @classmethod
    async def create_task(cls, journey_id: ObjectId, end_time: int, first_ev_time: Optional[int] = None, first_ev_tick: Optional[int] = None):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task("end_journey_time", {"journey_id": str(journey_id)}, run_at=end_time, resource_id=f"journey_end:{journey_id}")
        if first_ev_time is not None and first_ev_tick is not None:
            await enqueue_task("journey_event", {
                "journey_id": str(journey_id),
                "tick_index": first_ev_tick
            }, run_at=first_ev_time, resource_id=f"journey_event:{journey_id}")

    @classmethod
    async def cancel_task(cls, journey_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"journey_end:{journey_id}")
        await cancel_task_by_resource(f"journey_event:{journey_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        current_time = int(time.time())
        journeys = await cls.find().to_list()
        for act in journeys:
            # End journey task
            res_id = f"journey_end:{act.id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, act.end_time)
                from bot.modules.task_queue import enqueue_task
                await enqueue_task("end_journey_time", {"journey_id": str(act.id)}, run_at=run_at, resource_id=res_id)
                
            # Event task
            res_ev_id = f"journey_event:{act.id}"
            
            # Revert any active events back to pending (e.g. if bot crashed/restarted while event was triggering)
            revert_needed = False
            for ev in act.pregenerated_events:
                if ev.get("status") == "active":
                    ev["status"] = "pending"
                    revert_needed = True
            if revert_needed:
                act.pregenerated_events = [e.copy() for e in act.pregenerated_events]
                await act.save()

            if not await is_task_scheduled(res_ev_id):
                has_waiting_choice = False
                waiting_ev = None
                for ev in act.pregenerated_events:
                    if ev.get("status") == "waiting_choice":
                        has_waiting_choice = True
                        waiting_ev = ev
                        break
                if not has_waiting_choice:
                    pending_events = [ev for ev in act.pregenerated_events if ev.get("status") == "pending"]
                    if pending_events:
                        pending_events.sort(key=lambda x: x.get("trigger_time", 0))
                        next_ev = pending_events[0]
                        run_at = max(current_time, next_ev["trigger_time"])
                        from bot.modules.task_queue import enqueue_task
                        await enqueue_task("journey_event", {
                            "journey_id": str(act.id),
                            "tick_index": next_ev["tick_index"]
                        }, run_at=run_at, resource_id=res_ev_id)
                else:
                    run_at = max(current_time, waiting_ev.get("timeout", 0))
                    from bot.modules.task_queue import enqueue_task
                    await enqueue_task("journey_event", {
                        "journey_id": str(act.id),
                        "tick_index": waiting_ev["tick_index"]
                    }, run_at=run_at, resource_id=res_ev_id)

    @classmethod
    async def add_items_to_journey_bag(cls, journey: "JourneyActivity", items_to_add: list) -> list:
        from bot.models.dinosaur import Dino
        from bot.models.items import Item
        from bot.modules.items.item import get_item_capacity

        dino_db_ids = []
        for d_val in journey.dino_ids:
            dino_obj = Dino()
            if await dino_obj.create(d_val):
                dino_db_ids.append(dino_obj.id)

        backpack_cap = 0
        for dino_id in dino_db_ids:
            accs = await Item.find_accessory(dino_id, 'backpack')
            backpack_cap += sum(get_item_capacity(acc.items_data) for acc in accs)

        base_cap = 10 * len(journey.dino_ids)
        bonus_slots = 0
        for bag_item in journey.bag:
            bonus_slots += get_item_capacity(bag_item) * bag_item.get("count", 0)
        max_capacity = base_cap + backpack_cap + bonus_slots


        updated_items = []
        for it in items_to_add:
            it_id = it.get("item_id")
            it_cnt = it.get("count", 1)
            it_ab = it.get("abilities", {})
            
            current_total = sum(bag_item.get("count", 0) for bag_item in journey.bag)
            fit_count = min(it_cnt, max(0, max_capacity - current_total))
            
            if fit_count > 0:
                found = False
                for bag_item in journey.bag:
                    if bag_item.get("item_id") == it_id and bag_item.get("abilities") == it_ab:
                        bag_item["count"] += fit_count
                        found = True
                        break
                if not found:
                    journey.bag.append({
                        "item_id": it_id,
                        "count": fit_count,
                        "abilities": it_ab
                    })
            
            lost_cnt = it_cnt - fit_count
            if lost_cnt > 0:
                updated_items.append({
                    "item_id": it_id,
                    "count": lost_cnt,
                    "abilities": it_ab,
                    "lost_no_space": True
                })
            if fit_count > 0:
                updated_items.append({
                    "item_id": it_id,
                    "count": fit_count,
                    "abilities": it_ab
                })
        # Explicitly copy list to mark dirty for Beanie
        journey.bag = [b.copy() for b in journey.bag]
        return updated_items

    @classmethod
    async def trigger_standard_event(cls, journey: "JourneyActivity", ev: dict):
        from random import choice
        from bot.modules.items.item import get_data as get_item_data

        for e in journey.pregenerated_events:
            if e.get("tick_index") == ev.get("tick_index"):
                ev = e
                break

        event_dict = ev["event_data"]
        dinos = [await Dino().create(d_id) for d_id in journey.dino_ids]
        dinos = [d for d in dinos if d]

        max_dex = max((d.stats.get("dexterity", 0) for d in dinos), default=0)
        max_pwr = max((d.stats.get("power", 0) for d in dinos), default=0)
        max_itl = max((d.stats.get("intelligence", 0) for d in dinos), default=0)
        max_cha = max((d.stats.get("charisma", 0) for d in dinos), default=0)

        dino_edit = event_dict.get("dino_edit", {}).copy()

        # Apply rain/cold_wind cloak/clothing protections
        if event_dict["type"] == "rain" and await cls.downgrade_bag_item(journey.bag, "cloak", amount=2):
            dino_edit = {}
            event_dict["dino_edit"] = {}
            event_dict["story_key"] = "anti_rain"
        elif event_dict["type"] == "cold_wind" and await cls.downgrade_bag_item(journey.bag, "leather_clothing", amount=2):
            dino_edit = {}
            event_dict["dino_edit"] = {}
            event_dict["story_key"] = "anti_cold_wind"

        # Apply protections/mitigations based on stat values
        for key in list(dino_edit.keys()):
            val = dino_edit[key]
            if val < 0:
                if key == "game":
                    if await cls.downgrade_bag_item(journey.bag, "rubik_cube", amount=2):
                        dino_edit[key] = 0
                    else:
                        dino_edit[key] = min(0, val + int(max_cha * 0.3))
                elif key == "eat":
                    if await cls.downgrade_bag_item(journey.bag, "bag_goodies", amount=2):
                        dino_edit[key] = 0
                    else:
                        dino_edit[key] = min(0, val + int(max_pwr * 0.3))
                elif key == "heal":
                    jacket_def = 0
                    if await cls.downgrade_bag_item(journey.bag, "leather_jacket", amount=2):
                        jacket_def = 8
                    dino_edit[key] = min(0, val + int(max_dex * 0.4 + max_pwr * 0.2) + jacket_def)
                elif key == "energy":
                    dino_edit[key] = min(0, val + int(max_pwr * 0.3))
            elif val > 0:
                bonus = int(val * (max_itl * 0.02 + max_cha * 0.01))
                dino_edit[key] = val + bonus

        # Mutate dino stats — heal damage clamped so HP never drops below floor
        for dino in dinos:
            for key, val in dino_edit.items():
                if val != 0:
                    if key == "heal" and val < 0:
                        current_hp = dino.stats.get("heal", cls.JOURNEY_HP_FLOOR)
                        val = max(val, cls.JOURNEY_HP_FLOOR - current_hp)  # keep HP >= floor
                    if val != 0:
                        await Dino.mutate_stat(dino, key, val)

        # Eject any dinos now at/below HP floor
        ejected = cls._eject_weak_dinos(journey, dinos, ev)

        if not journey.dino_ids:
            journey.end_time = int(time.time())
            ev["status"] = "completed"
            await journey.save()
            await cls.end(journey.id)
            return

        # Coins modifier
        coins_gained = event_dict.get("coins", 0)
        if coins_gained > 0:
            coins_gained += int(coins_gained * (max_itl * 0.02 + max_cha * 0.01))
            journey.coins += coins_gained
            event_dict["coins"] = coins_gained
        elif coins_gained < 0:
            journey.coins = max(0, journey.coins + coins_gained)

        # Items modifier
        items_add = event_dict.get("items_add", [])
        if items_add:
            updated_items = await cls.add_items_to_journey_bag(journey, items_add)
            event_dict["items_add"] = updated_items
            for it in updated_items:
                if not it.get("lost_no_space"):
                    journey.items.append(it)

        # Items removal
        remove_count = len(event_dict.get("items_remove", []))
        if remove_count > 0:
            if await cls.downgrade_bag_item(journey.bag, "lock_bag", amount=2):
                pass
            else:
                for _ in range(remove_count):
                    eligible = [it for it in journey.bag if it.get("count", 0) > 0 and it.get("item_id") not in ["hiking_bag", "bag_goodies", "lock_bag"]]
                    if not eligible:
                        eligible = [it for it in journey.bag if it.get("count", 0) > 0]
                    if eligible:
                        removed_item = choice(eligible)
                        removed_item["count"] -= 1
                        event_dict.setdefault("remove_items", []).append(removed_item["item_id"])
                        for it in list(journey.items):
                            if isinstance(it, dict) and it.get("item_id") == removed_item["item_id"]:
                                journey.items.remove(it)
                                break
                            elif isinstance(it, str) and it == removed_item["item_id"]:
                                journey.items.remove(it)
                                break
                journey.bag = [b.copy() for b in journey.bag]

        # Autofeed logic
        for dino in dinos:
            if dino.stats.get("eat", 100) < 50:
                food_item = None
                for item in journey.bag:
                    if item.get("count", 0) > 0:
                        it_data = get_item_data(item["item_id"])
                        if it_data.get("type") == "eat":
                            food_item = item
                            break
                if food_item:
                    food_item["count"] -= 1
                    feed_val = get_item_data(food_item["item_id"]).get("act", 20)
                    await Dino.mutate_stat(dino, "eat", feed_val)
                    journey.pregenerated_events.append({
                        "tick_index": -1,
                        "trigger_time": int(time.time()),
                        "status": "completed",
                        "type": "autofeed",
                        "event_data": {
                            "type": "autofeed",
                            "dino_name": dino.name,
                            "food_id": food_item["item_id"],
                            "feed_value": feed_val,
                            "sub_location": event_dict.get("sub_location")
                        }
                    })

        event_dict["dino_edit"] = dino_edit
        ev["status"] = "completed"
        if "change_location" in event_dict:
            # Check if any dino has a treasure_map equipped — it cancels location change and loses durability
            map_blocked = False
            from bot.models.items import Item as ItemModel
            from bot.modules.notifications import dino_notification
            for dino in dinos:
                map_item = await ItemModel.find_one({"owner": str(dino.id), "items_data.item_id": "treasure_map"})
                if map_item:
                    # Reduce map endurance by exactly 1
                    abilities = map_item.items_data.get("abilities", {})
                    abilities["endurance"] = abilities.get("endurance", 1) - 1
                    map_item.items_data["abilities"] = abilities
                    if abilities["endurance"] <= 0:
                        await map_item.delete()
                        await dino_notification(dino.id, "broke_accessory", item_id="treasure_map")
                    else:
                        await map_item.save()
                    event_dict["map_blocked_location"] = event_dict.pop("change_location")
                    map_blocked = True
                    break
            if not map_blocked:
                journey.location = event_dict["change_location"]

        journey.items = list(journey.items)
        journey.bag = [b.copy() for b in journey.bag]
        journey.pregenerated_events = [e.copy() for e in journey.pregenerated_events]
        await journey.save()

    @classmethod
    async def trigger_battle_event(cls, journey: "JourneyActivity", ev: dict):
        import uuid
        from bot.redismanager import redis_set
        from bot.modules.combat.auto_combat import AutoCombat, CombatParticipant, generate_opponents
        from bot.modules.items.item import get_data as get_item_data

        for e in journey.pregenerated_events:
            if e.get("tick_index") == ev.get("tick_index"):
                ev = e
                break

        event_dict = ev["event_data"]
        location = event_dict["location"]
        mobs_list = event_dict["mobs"]

        dinos = [await Dino().create(d_id) for d_id in journey.dino_ids]
        dinos = [d for d in dinos if d]

        medicine_items = []
        for item in journey.bag:
            if item.get("count", 0) > 0:
                item_id = item.get("item_id")
                data_item = get_item_data(item_id)
                if data_item.get("type") in ["heal", "ammunition"]:
                    medicine_items.append({
                        "item_id": item_id,
                        "items_data": item,
                        "count": item.get("count")
                    })

        team_x = []
        for d in dinos:
            part = await CombatParticipant.from_dino(d, [])
            part.inventory = medicine_items
            team_x.append(part)

        danger = locations.get(location, {}).get("danger", 1.0)
        team_y = generate_opponents(len(mobs_list), mobs_list, total_danger=danger)

        if journey.friend:
            companions = journey.friend if isinstance(journey.friend, list) else [journey.friend]
            for comp in companions:
                if not isinstance(comp, dict):
                    continue
                comp_part = CombatParticipant(
                    unique_id=comp.get("unique_id", f"companion<i>{comp.get('mob_id', 'unknown')}</i>{uuid.uuid4().hex[:6]}"),
                    name=comp.get("name", "Компаньон"),
                    participant_type="mob",
                    max_hp=comp.get("max_hp", 100.0),
                    hp=comp.get("hp", 100.0),
                    max_energy=comp.get("max_energy", 100.0),
                    energy=comp.get("energy", 100.0),
                    stats=comp.get("stats", {"power": 10, "dexterity": 10, "intelligence": 10, "charisma": 10}),
                    role=comp.get("role", "carry"),
                    weapon=comp.get("weapon"),
                    shield=comp.get("shield"),
                    mob_id=comp.get("mob_id")
                )
                if comp.get("combat_role") == "dino":
                    team_x.append(comp_part)
                else:
                    team_y.append(comp_part)

        combat = AutoCombat(team_x, team_y)
        result = combat.run()

        # Save turn-by-turn battle logs to Redis (distinct TTL based on user premium status)
        owner_id = journey.userid
        from bot.modules.user.premium import premium
        is_prem = await premium(owner_id)
        history_ttl = 7776000 if is_prem else 604800
        max_battles = 1000 if is_prem else 200

        battle_id = f"combat_log:{uuid.uuid4().hex}"
        await redis_set(battle_id, result, ex=history_ttl)

        # Save battle record to dinosaur page history in Redis
        from bot.redismanager import get_redis
        r = get_redis()
        for d in dinos:
            dino_battles_key = f"dino_battles:{d.id}"
            summary = {
                "battle_id": battle_id,
                "winner": result["winner"],
                "mobs": [m.name for m in team_y],
                "time": int(time.time()),
                "location": location
            }
            await r.lpush(dino_battles_key, json.dumps(summary, default=str))
            await r.ltrim(dino_battles_key, 0, max_battles)
            await r.expire(dino_battles_key, history_ttl)

        # Sync outcomes
        await cls.sync_battle_outcome(journey, combat)

        loot = result.get("loot", [])
        if loot and await cls.downgrade_bag_item(journey.bag, "skinning_knife", amount=2):
            for mob in team_y:
                mob_loot = mob.original_obj.get("loot", [])
                for item_id in mob_loot:
                    if randint(1, 2) == 2:
                        loot.append(item_id)

        loot_items = [{"item_id": it_id, "count": 1, "abilities": {}} for it_id in loot]
        if loot_items:
            updated_loot = await cls.add_items_to_journey_bag(journey, loot_items)
            loot = updated_loot
            for it in updated_loot:
                if not it.get("lost_no_space"):
                    journey.items.append(it)

        winner_text = "Динозавры" if result["winner"] == "X" else ("Противники" if result["winner"] == "Y" else "Ничья")
        dinos_status = [f"{p.name} (HP: {int(p.hp)}/{int(p.max_hp)})" for p in team_x]

        journey.friend = None

        log_entry = {
            "type": "battle",
            "location": location,
            "worldview": "negative" if result["winner"] == "Y" else "positive",
            "mobs": ", ".join([m.name for m in team_y]),
            "winner": winner_text,
            "dinos_status": ", ".join(dinos_status),
            "loot": loot,
            "battle_id": battle_id
        }
        ev["event_data"].update(log_entry)
        ev["status"] = "completed"
        journey.items = list(journey.items)
        journey.bag = [b.copy() for b in journey.bag]
        journey.pregenerated_events = [e.copy() for e in journey.pregenerated_events]
        await journey.save()

        # Track kill quests if player team won
        if result["winner"] == "X":
            from bot.modules.quests import quest_process as qp
            killed_mob_ids = [m.mob_id for m in team_y if m.mob_id]
            if killed_mob_ids:
                await qp(journey.userid, "kill", items=killed_mob_ids)
                try:
                    from bot.redismanager import get_redis
                    redis = get_redis()
                    for mob_id in killed_mob_ids:
                        await redis.rpush("global_defeated_mobs_today", mob_id)
                except Exception as e:
                    log(f"Failed to log defeated mobs to Redis: {e}", 3)

            # Fire battle_win achievement event
            if journey.userid:
                from bot.models.user import User
                u = await User.find_one(User.userid == journey.userid)
                if u:
                    if 'battle_wins' not in u.settings:
                        u.settings['battle_wins'] = 0
                    u.settings['battle_wins'] += 1
                    await u.save()
                from bot.modules.user.achievements import check_achievements
                await check_achievements(journey.userid, "battle_win", killed_mob_ids)

        # Process fainted dinos
        fainted_dinos = []
        for p in team_x:
            if p.type == "dino" and p.original_obj and not p.is_alive():
                fainted_dinos.append(p.original_obj)

        alive_count = len([p for p in team_x if p.type == "dino"]) - len(fainted_dinos)

        for fd in fainted_dinos:
            # 1. Log that the dino left the route
            left_entry = {
                "tick_index": ev.get("tick_index", -1),
                "trigger_time": int(time.time()),
                "status": "completed",
                "type": "dino_left",
                "event_data": {
                    "type": "dino_left",
                    "dino_name": fd.name,
                    "dino_id": str(fd.id),
                    "depth": ev.get("depth", 0),
                    "trigger_time": int(time.time()),
                    "tick_index": ev.get("tick_index", 0)
                }
            }
            journey.pregenerated_events.append(left_entry)

            if alive_count > 0:
                # 2. Remove from active journey dino_ids only if others are still alive
                if fd.id in journey.dino_ids:
                    journey.dino_ids.remove(fd.id)

        if fainted_dinos and alive_count > 0:
            if journey.dino_id not in journey.dino_ids:
                journey.dino_id = journey.dino_ids[0]
            journey.pregenerated_events = [e.copy() for e in journey.pregenerated_events]
            await journey.save()

        alive_x = any(p.is_alive() for p in team_x)
        if not alive_x or result["winner"] == "Y":
            # Fire battle_lose achievement event
            if journey.userid:
                from bot.models.user import User
                u = await User.find_one(User.userid == journey.userid)
                if u:
                    if 'battle_losses' not in u.settings:
                        u.settings['battle_losses'] = 0
                    u.settings['battle_losses'] += 1
                    await u.save()
                from bot.modules.user.achievements import check_achievements
                await check_achievements(journey.userid, "battle_lose")

            journey.end_time = int(time.time())
            await journey.save()

            from bot.modules.notifications import user_notification
            from bot.modules.localization import get_lang, get_data
            lang = await get_lang(journey.userid)
            loc_data = get_data(f"journey_start.locations.{location}", lang)
            loc_name = loc_data.get("name", location) if isinstance(loc_data, dict) else location
            await user_notification(journey.userid, "journey_defeat", location=loc_name)
            await cls.end(journey.id)
            return

    @classmethod
    async def sync_battle_outcome(cls, journey: "JourneyActivity", combat):
        from bot.models.items import Item
        from bot.modules.notifications import dino_notification

        for p in combat.team_x:
            if p.type == "dino" and p.original_obj:
                dino = p.original_obj
                dino.stats["heal"] = max(10, int(p.hp))
                dino.stats["energy"] = max(0, int(p.energy))
                await dino.save()

                if p.weapons:
                    for w in p.weapons:
                        weapon_doc = await Item.find_one(Item.owner_id == str(dino.id), {"items_data.item_id": w["item_id"]})
                        if weapon_doc:
                            new_dur = w.get("abilities", {}).get("endurance", 0)
                            if new_dur <= 0:
                                await weapon_doc.delete()
                                await dino_notification(dino.id, 'broke_accessory', item_id=w["item_id"])
                            else:
                                if "abilities" not in weapon_doc.items_data or not isinstance(weapon_doc.items_data["abilities"], dict):
                                    weapon_doc.items_data["abilities"] = {}
                                weapon_doc.items_data["abilities"]["endurance"] = new_dur
                                await weapon_doc.save()

                if p.shields:
                    for s in p.shields:
                        shield_doc = await Item.find_one(Item.owner_id == str(dino.id), {"items_data.item_id": s["item_id"]})
                        if shield_doc:
                            new_dur = s.get("abilities", {}).get("endurance", 0)
                            if new_dur <= 0:
                                await shield_doc.delete()
                                await dino_notification(dino.id, 'broke_accessory', item_id=s["item_id"])
                            else:
                                if "abilities" not in shield_doc.items_data or not isinstance(shield_doc.items_data["abilities"], dict):
                                    shield_doc.items_data["abilities"] = {}
                                shield_doc.items_data["abilities"]["endurance"] = new_dur
                                await shield_doc.save()

        # Consume medicine from bag
        for owner_id, items_used in combat.consumed_items.items():
            for item_id, count_used in items_used.items():
                for item in journey.bag:
                    if item.get("item_id") == item_id:
                        item["count"] = max(0, item["count"] - count_used)

    @classmethod
    async def trigger_choice_event(cls, journey: "JourneyActivity", ev: dict):
        from bot.modules.localization import t
        from bot.modules.data_format import list_to_inline
        from bot.exec import bot

        for e in journey.pregenerated_events:
            if e.get("tick_index") == ev.get("tick_index"):
                ev = e
                break

        event_dict = ev["event_data"]
        
        # Update status and timeout using copy-on-write
        new_events = []
        for e in journey.pregenerated_events:
            if e.get("tick_index") == ev.get("tick_index"):
                new_e = e.copy()
                new_e["status"] = "waiting_choice"
                new_e["timeout"] = int(time.time()) + 900
                new_events.append(new_e)
                ev = new_e
            else:
                new_events.append(e.copy())
        journey.pregenerated_events = new_events
        await journey.save()

        event_idx = None
        for idx, item in enumerate(journey.pregenerated_events):
            if item.get("tick_index") == ev.get("tick_index"):
                event_idx = idx
                break

        from bot.modules.localization import get_lang
        lang = await get_lang(journey.userid)

        # Get actual options list via get_data to avoid stringified list formatting
        from bot.modules.localization import get_data
        choice_key = event_dict["key"]
        options_list = get_data(f"journey_choices.{choice_key}.options", lang) or []
        choice_text = t(f"journey_choices.{choice_key}.text", lang) or ""

        # Retrieve dinos names and location
        dino_names = []
        for d_id in journey.dino_ids:
            d = await Dino.find_one(Dino.id == d_id)
            if d:
                dino_names.append(d.name)
        dinos_str = ", ".join(dino_names)

        location = journey.location
        loc_name = get_data(f"journey_start.locations.{location}", lang).get("name", location)

        btn_dict = {}
        for opt_idx in range(event_dict.get("options_count", len(options_list))):
            if opt_idx < len(options_list):
                opt_text = options_list[opt_idx]
                btn_dict[opt_text] = f"j_choice {journey.id} {event_idx} {opt_idx}"

        markup = list_to_inline([btn_dict])
        message_text = t("journey_choice.title", lang, location=loc_name, dinos=dinos_str, text=choice_text)

        try:
            mes = await bot.send_message(journey.userid, message_text, reply_markup=markup)
            
            # Update message_id using copy-on-write
            new_events = []
            for e in journey.pregenerated_events:
                if e.get("tick_index") == ev.get("tick_index"):
                    new_e = e.copy()
                    new_e["message_id"] = mes.message_id
                    new_events.append(new_e)
                    ev = new_e
                else:
                    new_events.append(e.copy())
            journey.pregenerated_events = new_events
            await journey.save()

            from bot.modules.task_queue import enqueue_task
            await enqueue_task("journey_event", {
                "journey_id": str(journey.id),
                "tick_index": ev["tick_index"]
            }, run_at=ev["timeout"], resource_id=f"journey_event:{journey.id}")
        except Exception:
            resolved = False
            for opt_i in range(len(ev.get("event_data", {}).get("outcomes", []))):
                try:
                    await cls.resolve_choice_event(journey, ev, option_idx=opt_i, expired=True)
                    resolved = True
                    break
                except ValueError:
                    continue
            if not resolved:
                await cls.resolve_choice_event(journey, ev, option_idx=0, expired=True, force=True)

    @classmethod
    async def resolve_choice_event(cls, journey: "JourneyActivity", ev: dict, option_idx: int, expired: bool = False, chat_id: Optional[int] = None, message_id: Optional[int] = None, force: bool = False):
        from bot.modules.localization import t
        from bot.exec import bot

        event_dict = ev["event_data"]
        from bot.modules.localization import get_lang
        lang = await get_lang(journey.userid)

        outcome = event_dict["outcomes"][option_idx]
        
        # Validate item requirements
        conseq_success = outcome.get("success", outcome)
        conseq_fail = outcome.get("fail", outcome)
        required_items = []

        # Check requirements key
        reqs = outcome.get("requirements")
        if reqs and "item_id" in reqs:
            req_count = reqs.get("count", 1)
            required_items.append({"item_id": reqs["item_id"], "count": req_count})

        if "items_remove" in outcome:
            for it in outcome["items_remove"]:
                if isinstance(it, str):
                    required_items.append({"item_id": it, "count": 1})
                elif isinstance(it, dict):
                    required_items.append(it)
        if "success" in outcome and "items_remove" in outcome["success"]:
            for it in outcome["success"]["items_remove"]:
                if isinstance(it, str):
                    required_items.append({"item_id": it, "count": 1})
                elif isinstance(it, dict):
                    required_items.append(it)
        if "fail" in outcome and "items_remove" in outcome["fail"]:
            for it in outcome["fail"]["items_remove"]:
                if isinstance(it, str):
                    required_items.append({"item_id": it, "count": 1})
                elif isinstance(it, dict):
                    required_items.append(it)

        req_counts = {}
        for it in required_items:
            it_id = it["item_id"]
            it_count = it["count"]
            req_counts[it_id] = req_counts.get(it_id, 0) + it_count

        for req_item, req_qty in req_counts.items():
            has_qty = 0
            for bag_item in journey.bag:
                if bag_item.get("item_id") == req_item:
                    has_qty += bag_item.get("count", 0)
            if has_qty < req_qty:
                if not force:
                    raise ValueError(req_item)

        # Consume items from bag
        for req_item, req_qty in req_counts.items():
            rem_qty = req_qty
            for bag_item in journey.bag:
                if bag_item.get("item_id") == req_item:
                    cnt = bag_item.get("count", 0)
                    if cnt >= rem_qty:
                        bag_item["count"] -= rem_qty
                        rem_qty = 0
                        break
                    else:
                        rem_qty -= cnt
                        bag_item["count"] = 0

        success = True
        if "success_chance" in outcome or (reqs and "success_chance" in reqs):
            chance = outcome.get("success_chance", reqs.get("success_chance", 1.0) if reqs else 1.0)
            if "stat_check" in outcome:
                stat_name = outcome["stat_check"]["stat"]
                difficulty = outcome["stat_check"]["difficulty"]
                mult = outcome["stat_check"].get("success_chance_mult", 0.05)
                dinos = [await Dino().create(d_id) for d_id in journey.dino_ids]
                dinos = [d for d in dinos if d]
                max_stat = max((d.stats.get(stat_name, 0) for d in dinos), default=0)
                chance = min(1.0, max(0.05, chance + (max_stat - difficulty) * mult))
            success = random() <= chance

        conseq = outcome["success"] if success else outcome["fail"]
        
        # Add to conseq items_remove list dynamically for UI logs display
        if required_items:
            if "items_remove" not in conseq:
                conseq["items_remove"] = []
            for it in required_items:
                it_id = it["item_id"]
                if it_id not in conseq["items_remove"]:
                    conseq["items_remove"].append(it_id)
        dinos = [await Dino().create(d_id) for d_id in journey.dino_ids]
        dinos = [d for d in dinos if d]

        for key in ["heal", "energy", "eat", "game", "mood"]:
            mod = conseq.get(key, 0)
            if mod == 0 and "dino_edit" in conseq:
                mod = conseq["dino_edit"].get(key, 0)
            if mod != 0:
                for d in dinos:
                    effective_mod = mod
                    if key == "heal" and mod < 0:
                        current_hp = d.stats.get("heal", cls.JOURNEY_HP_FLOOR)
                        effective_mod = max(mod, cls.JOURNEY_HP_FLOOR - current_hp)  # keep HP >= floor
                    if effective_mod != 0:
                        await Dino.mutate_stat(d, key, effective_mod)

        # Eject dinos now at/below HP floor
        ejected = cls._eject_weak_dinos(journey, dinos, ev)

        if not journey.dino_ids:
            journey.end_time = int(time.time())
            ev["status"] = "completed"
            await journey.save()
            await cls.end(journey.id)
            return

        coins_gained = conseq.get("coins", 0)
        if coins_gained > 0:
            journey.coins += coins_gained

        choice_items = cls.roll_items_to_add(conseq.get("items", []) + conseq.get("items_add", []))
        if choice_items:
            choice_items = await cls.add_items_to_journey_bag(journey, choice_items)
            for it in choice_items:
                if not it.get("lost_no_space"):
                    journey.items.append(it)

        if "change_location" in conseq:
            journey.location = conseq["change_location"]
            ev["event_data"]["change_location"] = conseq["change_location"]
            journey.route_path.append({
                "type": "location",
                "name": conseq["change_location"],
                "depth": 0
            })

        if "companion" in conseq:
            journey.friend = conseq["companion"]

        if "trigger_immediate_battle" in conseq:
            pending_indices = [idx for idx, e in enumerate(journey.pregenerated_events) if e.get("status") == "pending"]
            if pending_indices:
                idx_next = pending_indices[0]
                journey.pregenerated_events[idx_next]["type"] = "battle"
                journey.pregenerated_events[idx_next]["event_data"] = {
                    "type": "battle",
                    "location": journey.location,
                    "sub_location": ev["event_data"].get("sub_location"),
                    "depth": ev["event_data"].get("depth", 0),
                    "mobs": conseq["trigger_immediate_battle"].get("mobs", ["crocodile"])
                }
                # Trigger battle on the next tick
                journey.pregenerated_events[idx_next]["trigger_time"] = int(time.time())

        if "change_sub_location" in conseq:
            sub_loc = conseq["change_sub_location"]
            pending_indices = [idx for idx, e in enumerate(journey.pregenerated_events) if e.get("status") == "pending"]
            if len(pending_indices) >= 3:
                from random import choice as rchoice, randint
                from bot.models.activity.journey import SUB_LOCATIONS, events
                
                # 1. First event: enter sub-location
                idx_1 = pending_indices[0]
                journey.pregenerated_events[idx_1]["type"] = "standard"
                journey.pregenerated_events[idx_1]["event_data"] = {
                    "type": f"enter_{sub_loc}",
                    "location": journey.location,
                    "sub_location": sub_loc,
                    "depth": 1
                }
                
                # 2. Second event: standard/battle event inside sub-location
                idx_2 = pending_indices[1]
                pool = SUB_LOCATIONS.get(sub_loc, {}).get("events", [])
                pool = [k for k in pool if not events.get(k, {}).get("is_choice")]
                if pool:
                    selected_ev_key = rchoice(pool)
                    ev_cfg = events.get(selected_ev_key, {})
                    is_battle = selected_ev_key in ["battle", "cave_bat", "oasis_camel", "shark_attack"]
                    
                    if is_battle:
                        if selected_ev_key == "cave_bat":
                            mobs_list = ["bat"]
                        elif selected_ev_key == "oasis_camel":
                            mobs_list = ["camel"]
                        elif selected_ev_key == "shark_attack":
                            mobs_list = ["shark"]
                        else:
                            from bot.models.activity.journey import locations
                            danger = locations.get(journey.location, {}).get("danger", 1.0)
                            mobs_cfg = locations.get(journey.location, {}).get("mobs", {})
                            mob_names = mobs_cfg.get("mobs", ["crocodile"])
                            mob_count = 1 if danger <= 1.1 else randint(1, 2)
                            mobs_list = [rchoice(mob_names) for _ in range(mob_count)]
                        journey.pregenerated_events[idx_2]["type"] = "battle"
                        journey.pregenerated_events[idx_2]["event_data"] = {
                            "type": selected_ev_key,
                            "location": journey.location,
                            "sub_location": sub_loc,
                            "depth": 1,
                            "mobs": mobs_list
                        }
                    else:
                        outcomes = ev_cfg.get("outcomes", [])
                        selected_outcome = outcomes[0].get("success", outcomes[0]) if outcomes else {"story_key": "success"}
                        
                        affected_dino = rchoice(dinos) if dinos else None
                        items_add = cls.roll_items_to_add(selected_outcome.get("items_add", []))
                        
                        journey.pregenerated_events[idx_2]["type"] = "standard"
                        journey.pregenerated_events[idx_2]["event_data"] = {
                            "type": selected_ev_key,
                            "location": journey.location,
                            "sub_location": sub_loc,
                            "depth": 1,
                            "story_key": selected_outcome.get("story_key", "success"),
                            "affected_dino_id": str(affected_dino.id) if affected_dino else None,
                            "dino_edit": selected_outcome.get("dino_edit", {}),
                            "coins": selected_outcome.get("coins", 0),
                            "items_add": items_add,
                            "items_remove": selected_outcome.get("items_remove", [])
                        }
                
                # 3. Third event: exit sub-location
                idx_3 = pending_indices[2]
                journey.pregenerated_events[idx_3]["type"] = "standard"
                journey.pregenerated_events[idx_3]["event_data"] = {
                    "type": f"exit_{sub_loc}",
                    "location": journey.location,
                    "sub_location": sub_loc,
                    "depth": 1
                }

        from bot.modules.localization import get_data
        choice_key = event_dict["key"]
        options_list = get_data(f"journey_choices.{choice_key}.options", lang) or []
        choice_text = t(f"journey_choices.{choice_key}.text", lang) or ""
        outcomes_list = get_data(f"journey_choices.{choice_key}.outcomes", lang) or []
        
        opt_text = options_list[option_idx] if option_idx < len(options_list) else ""
        outcome_texts = outcomes_list[option_idx] if option_idx < len(outcomes_list) else {}
        if isinstance(outcome_texts, dict):
            outcome_text = outcome_texts.get("success" if success else "fail", "")
        else:
            outcome_text = str(outcome_texts)

        # Build dynamic effect string for final edited message & completed log
        effect_parts = []
        dino_edit = conseq.get("dino_edit", {})
        from bot.modules.localization import get_data
        signs = get_data('journey.signs', lang)
        for stat, val in dino_edit.items():
            if val != 0:
                sign = "+" if val > 0 else ""
                stat_emoji = signs.get(stat, "")
                effect_parts.append(f"{sign}{val}{stat_emoji}")

        coins = conseq.get("coins", 0)
        if coins != 0:
            sign = "+" if coins > 0 else ""
            effect_parts.append(f"{sign}{coins}🪙")

        from bot.modules.items.item import get_name
        for it in choice_items:
            if isinstance(it, dict):
                it_id = it.get("item_id")
                it_cnt = it.get("count", 1)
                effect_parts.append(f"+{it_cnt} {get_name(it_id, lang)}")
            else:
                effect_parts.append(f"+1 {get_name(it, lang)}")
        for it in conseq.get("items_remove", []):
            effect_parts.append(f"-1 {get_name(it, lang)}")

        effect_str = ", ".join(effect_parts) if effect_parts else ""
        if effect_str:
            outcome_text += f" ({effect_str})"

        # Update event data in the list using copy-on-write
        new_events = []
        for e in journey.pregenerated_events:
            if e.get("tick_index") == ev.get("tick_index"):
                new_e = e.copy()
                new_e["event_data"] = new_e.get("event_data", {}).copy()
                new_e["event_data"]["dino_edit"] = dino_edit
                new_e["event_data"]["coins"] = coins
                new_e["event_data"]["items_add"] = choice_items
                new_e["event_data"]["items_remove"] = conseq.get("items_remove", [])
                new_e["status"] = "completed"
                new_e["event_data"]["success"] = success
                new_e["event_data"]["expired"] = expired
                new_e["event_data"]["option_idx"] = option_idx
                new_events.append(new_e)
                ev = new_e
            else:
                new_events.append(e.copy())
        journey.pregenerated_events = new_events
        journey.items = list(journey.items)
        journey.bag = [b.copy() for b in journey.bag]
        await journey.save()

        # Reschedule next pending event after choice resolution
        pending_events = [ev for ev in journey.pregenerated_events if ev.get("status") == "pending"]
        if pending_events:
            pending_events.sort(key=lambda x: x.get("trigger_time", 0))
            next_ev = pending_events[0]
            from bot.modules.task_queue import enqueue_task
            await enqueue_task("journey_event", {
                "journey_id": str(journey.id),
                "tick_index": next_ev["tick_index"]
            }, run_at=next_ev["trigger_time"], resource_id=f"journey_event:{journey.id}")

        cid = chat_id or journey.userid
        msg_id = message_id or ev.get("message_id")
        if msg_id:
            try:
                if expired:
                    final_text = t("journey_choice.no_answer", lang, text=choice_text) + f"\n👉 {outcome_text}"
                else:
                    title_text = t("journey_menu.choice_title", lang)
                    selected_lbl = t("journey_menu.choice_selected", lang, option=opt_text)
                    final_text = f"{title_text}\n\n{choice_text}\n\n{selected_lbl}\n{outcome_text}"

                # Parse markdown to HTML in final_text
                import re
                final_text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', final_text)
                final_text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', final_text)
                final_text = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', final_text)
                final_text = re.sub(r'_([^_]+)_', r'<i>\1</i>', final_text)

                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                btn_logs = InlineKeyboardButton(
                    text=t("journey_menu.buttons.logs", lang),
                    callback_data=f"j_active_log:{journey.id}:1"
                )
                markup = InlineKeyboardMarkup(inline_keyboard=[[btn_logs]])

                await bot.edit_message_text(final_text, chat_id=cid, message_id=msg_id, reply_markup=markup)
            except Exception:
                pass

    @classmethod
    async def generate_event_message(cls, event: dict, lang: str, journey_id: ObjectId, encode: bool = False) -> str:
        from bot.modules.data_format import encoder_text
        from bot.modules.items.item import counts_items, get_name
        from bot.modules.localization import get_data, t

        event_type = event['type']
        location = event.get('location', 'forest')
        signs = get_data('journey.signs', lang)

        if event_type == "dino_left":
            dino_name = event.get("dino_name", "Динозавр")
            text = t("journey.dino_left", lang, dino=dino_name, default="🦖 {dino} покинул маршрут и вернулся домой.").format(dino=dino_name)
            depth = event.get("depth", 0)
            if depth > 0:
                indent = "  " * depth
                text = f"{indent}↳ {text}"
            return text

        if event_type in ["choice", "autofeed", "battle"]:
            story_template = ""
        elif event_type == "choice_resolution":
            choice_key = event.get("choice_key", event.get("key", ""))
            choice_lbl = t("journey_menu.choice_label", lang, default="Выбор")
            if not choice_key:
                return f"❓ <b>{choice_lbl}:</b> [Событие выбора]"
            success = event.get("success", True)
            expired = event.get("expired", False)
            option_idx = event.get("option_idx", 0)
            
            options_list = get_data(f"journey_choices.{choice_key}.options", lang) or []
            outcomes_list = get_data(f"journey_choices.{choice_key}.outcomes", lang) or []
            
            opt_text = options_list[option_idx] if option_idx < len(options_list) else ""
            outcome_texts = outcomes_list[option_idx] if option_idx < len(outcomes_list) else {}
            if isinstance(outcome_texts, str):
                outcome_text = outcome_texts
            elif isinstance(outcome_texts, dict):
                outcome_text = outcome_texts.get("success" if success else "fail", "")
            else:
                outcome_text = ""
            
            if expired:
                story_template = t("journey_menu.choice_timeout", lang) + f"\n👉 {outcome_text}"
            else:
                story_template = f"❓ <b>{choice_lbl}:</b> {opt_text}\n{outcome_text}"
        else:
            # Retrieve story template
            from random import choice
            story_key = event.get("story_key", "success")
            story_data = get_data(f"journey_events.{event_type}.{story_key}", lang)
            if "no_text_key" in str(story_data):
                story_data = get_data(f"journey_events.{event_type}", lang)
            if "no_text_key" in str(story_data):
                story_data = get_data(f"journey.{event_type}", lang)

            if isinstance(story_data, list) and story_data:
                if 'replic' not in event:
                    story_template = choice(story_data)
                    event['replic'] = story_data.index(story_template)
                else:
                    idx = event['replic']
                    if idx < len(story_data):
                        story_template = story_data[idx]
                    else:
                        story_template = story_data[0]
            elif isinstance(story_data, str):
                story_template = story_data
            else:
                story_template = f"Событие {event_type} ({story_key})"
        
        # Pending/waiting_choice event — show the question text
        if event_type == "choice":
            choice_key = event.get("choice_key", event.get("key", ""))
            choice_text = t(f"journey_choices.{choice_key}.text", lang) or ""
            choice_name = t(f"journey_choices.{choice_key}.name", lang) or choice_key
            choice_lbl = t("journey_menu.choice_label", lang, default="Выбор")
            return f"❓ <b>{choice_lbl}: {choice_name}</b>\n{choice_text}"

        if event_type == "autofeed":
            food_id = event.get("food_id") or event.get("item_id", "")
            food_name = get_name(food_id, lang) if food_id else "?"
            text = t("journey.autofeed", lang, dino_name=event.get('dino_name', ''), food_name=food_name, feed_value=event.get('feed_value', 0))
            if event.get("sub_location"):
                text = f"   ↳ {text}"
            return text

        if event_type == "battle":
            winner = event.get("winner", "?")
            hp_info = event.get("dinos_status", "")
            mobs_raw = event.get("mobs", "?")
            
            # Localize mob names and append emojis
            mobs_list = []
            if isinstance(mobs_raw, str):
                parts = [p.strip() for p in mobs_raw.split(",")]
            elif isinstance(mobs_raw, list):
                parts = mobs_raw
            else:
                parts = []
            
            for part in parts:
                mob_id = part.lower().replace(" ", "_")
                trans = t(f"mobs.{mob_id}.name", lang)
                if "mobs." in trans:
                    mobs_list.append(part)
                else:
                    emoji = t(f"mobs.{mob_id}.emoji", lang)
                    emoji_str = emoji if "mobs." not in emoji else ""
                    mobs_list.append(f"{emoji_str} {trans}".strip())
            mobs_str = ", ".join(mobs_list) if mobs_list else str(mobs_raw)

            if winner == "Динозавры":
                winner_translated = t("journey_menu.dinosaurs", lang, default="Динозавры")
            elif winner == "Противники":
                winner_translated = t("journey_menu.opponents", lang, default="Противники")
            elif winner == "Ничья":
                winner_translated = t("journey_menu.draw", lang, default="Ничья")
            else:
                winner_translated = winner

            loot = event.get("loot", [])
            loot_parts = []
            if loot:
                for it in loot:
                    if isinstance(it, dict):
                        it_id = it.get("item_id")
                        it_cnt = it.get("count", 1)
                        if it.get("lost_no_space"):
                            lost_lbl = t("journey_menu.lost_no_space", lang, default="потерян, нет места")
                            loot_parts.append(f"+{it_cnt} {get_name(it_id, lang)} ({lost_lbl})")
                        else:
                            loot_parts.append(f"+{it_cnt} {get_name(it_id, lang)}")
                    else:
                        loot_parts.append(f"+1 {get_name(it, lang)}")
            loot_str = f" ({', '.join(loot_parts)})" if loot_parts else ""

            winner_lbl = t("journey_menu.winner_label", lang)
            hp_lbl = t("journey_menu.hp_label", lang)
            battle_lbl = t("journey_menu.battle_label", lang)

            brief = f"⚔️ <b>{battle_lbl}</b> {mobs_str}\n{winner_lbl}: {winner_translated}\n{hp_lbl}: {hp_info}{loot_str}"
            if event.get("sub_location"):
                brief = f"   ↳ {brief}"
            return brief

        # Retrieve journey dinos names
        journey_doc = await cls.find_one(cls.id == journey_id)
        dinos_names_list = []
        if journey_doc:
            for d_id in journey_doc.dino_ids:
                d = await Dino.find_one(Dino.id == d_id)
                if d:
                    dinos_names_list.append(d.name)
        else:
            # Fallback to Redis cache for completed journeys
            from bot.redismanager import redis_get
            import json
            try:
                res_val = await redis_get(f"journey_details:{journey_id}")
                if res_val:
                    if isinstance(res_val, dict):
                        dinos_names_list = res_val.get("dino_names_list", [])
                        if not dinos_names_list and "dinos" in res_val:
                            dinos_names_list = [n.strip() for n in res_val["dinos"].split(",") if n.strip()]
                    elif isinstance(res_val, str):
                        data = json.loads(res_val)
                        dinos_names_list = data.get("dino_names_list", [])
                        if not dinos_names_list and "dinos" in data:
                            dinos_names_list = [n.strip() for n in data["dinos"].split(",") if n.strip()]
            except Exception:
                pass
        dinos_str = ", ".join(dinos_names_list)

        # Retrieve affected dino name
        affected_dino_name = "динозавр"
        aff_id = event.get("affected_dino_id")
        if aff_id:
            aff_dino = await Dino.find_one(Dino.id == ObjectId(aff_id))
            if aff_dino:
                affected_dino_name = aff_dino.name
        
        # Fallback to deterministic selection from participants if affected_dino_id is missing or not found
        if affected_dino_name == "динозавр" and dinos_names_list:
            h_val = event.get("tick_index", 0) + event.get("trigger_time", 0)
            if not h_val:
                h_val = sum(ord(c) for c in event.get("type", ""))
            affected_dino_name = dinos_names_list[h_val % len(dinos_names_list)]

        # Resolve location / sub-location name declensions safely
        sub_loc = event.get("sub_location")
        event_type_raw = event.get("type", "")
        if event_type_raw == "enter_main_location":
            loc_data = get_data(f"journey_start.locations.{location}", lang)
            if isinstance(loc_data, dict):
                loc_name = loc_data.get("name", location)
                loc_prep = loc_data.get("prepositional", loc_name)
                loc_gen = loc_data.get("genitive", loc_name)
                loc_acc = loc_data.get("accusative", loc_name)
            else:
                loc_name = loc_prep = loc_gen = loc_acc = location
        elif event_type_raw.startswith("enter_") or event_type_raw.startswith("exit_"):
            inferred_sub = event_type_raw.split("_", 1)[1]
            loc_data = get_data(f"journey_start.sub_locations.{inferred_sub}", lang)
            if isinstance(loc_data, dict):
                loc_name = loc_data.get("name", inferred_sub)
                loc_prep = loc_data.get("prepositional", loc_name)
                loc_gen = loc_data.get("genitive", loc_name)
                loc_acc = loc_data.get("accusative", loc_name)
            else:
                loc_data = get_data(f"journey_start.locations.{location}", lang)
                if isinstance(loc_data, dict):
                    loc_name = loc_data.get("name", location)
                    loc_prep = loc_data.get("prepositional", loc_name)
                    loc_gen = loc_data.get("genitive", loc_name)
                    loc_acc = loc_data.get("accusative", loc_name)
                else:
                    loc_name = loc_prep = loc_gen = loc_acc = location
        elif sub_loc:
            loc_data = get_data(f"journey_start.sub_locations.{sub_loc}", lang)
            if isinstance(loc_data, dict):
                loc_name = loc_data.get("name", sub_loc)
                loc_prep = loc_data.get("prepositional", loc_name)
                loc_gen = loc_data.get("genitive", loc_name)
                loc_acc = loc_data.get("accusative", loc_name)
            else:
                loc_name = loc_prep = loc_gen = loc_acc = sub_loc
        else:
            loc_data = get_data(f"journey_start.locations.{location}", lang)
            if isinstance(loc_data, dict):
                loc_name = loc_data.get("name", location)
                loc_prep = loc_data.get("prepositional", loc_name)
                loc_gen = loc_data.get("genitive", loc_name)
                loc_acc = loc_data.get("accusative", loc_name)
            else:
                loc_name = loc_prep = loc_gen = loc_acc = location

        # Build dynamic effect string
        effect_parts = []
        dino_edit = event.get("dino_edit", {})
        for stat, val in dino_edit.items():
            if val != 0:
                sign = "+" if val > 0 else ""
                stat_emoji = signs.get(stat, "")
                effect_parts.append(f"{sign}{val}{stat_emoji}")

        coins = event.get("coins", 0)
        if coins != 0:
            sign = "+" if coins > 0 else ""
            effect_parts.append(f"{sign}{coins}🪙")

        def wrap_text_in_code(p: str) -> str:
            import re
            prefix_parts = []
            rest = p
            while True:
                m_custom = re.match(r'^(!\[.*?\]\(tg://emoji\?id=\d+\)\s*)', rest)
                if m_custom:
                    prefix_parts.append(m_custom.group(1))
                    rest = rest[len(m_custom.group(1)):]
                    continue
                m_std = re.match(r'^([\u2600-\u27BF\U0001f300-\U0001f64F\U0001f680-\U0001f6FF\U0001f900-\U0001f9FF\U0001f1e0-\U0001f1ff]\s*)', rest)
                if m_std:
                    prefix_parts.append(m_std.group(1))
                    rest = rest[len(m_std.group(1)):]
                    continue
                m_sym = re.match(r'^([↳🔹⛺🐊🏛️❓🪨📍⏱🦖🪙🎒⏱]\s*)', rest)
                if m_sym:
                    prefix_parts.append(m_sym.group(1))
                    rest = rest[len(m_sym.group(1)):]
                    continue
                break
            prefix = "".join(prefix_parts)
            return f"{prefix}<code>{rest}</code>" if rest else prefix

        for it in event.get("items_add", []):
            if isinstance(it, dict):
                it_id = it.get("item_id")
                it_cnt = it.get("count", 1)
                if it.get("lost_no_space"):
                    lost_lbl = t("journey_menu.lost_no_space", lang, default="потерян, нет места")
                    effect_parts.append(f"+{it_cnt} {wrap_text_in_code(get_name(it_id, lang))} ({lost_lbl})")
                else:
                    effect_parts.append(f"+{it_cnt} {wrap_text_in_code(get_name(it_id, lang))}")
            else:
                effect_parts.append(f"+1 {wrap_text_in_code(get_name(it, lang))}")

        for it in event.get("remove_items", []):
            effect_parts.append(f"-1 {wrap_text_in_code(get_name(it, lang))}")

        effect_str = ", ".join(effect_parts) if effect_parts else ""



        try:
            text = story_template.format(
                location=loc_name,
                location_prep=loc_prep,
                location_gen=loc_gen,
                location_acc=loc_acc,
                dino=affected_dino_name,
                dinos=dinos_str,
                effect=effect_str,
                friend_owner=event.get("friend_owner_name", ""),
                friend_dino=event.get("friend_dino_name", "")
            )
        except Exception:
            text = story_template

        if encode:
            text = encoder_text(text, 3)

        if effect_str:
            if effect_str not in text:
                text += f"\n{effect_str}"

        # Convert markdown to HTML in text
        import re
        text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', text)
        text = re.sub(r'_([^_]+)_', r'<i>\1</i>', text)

        if "change_location" in event:
            new_loc_key = event["change_location"]
            new_loc_data = get_data(f"journey_start.locations.{new_loc_key}", lang)
            new_loc_name = new_loc_data.get("name", new_loc_key)
            new_loc_lbl = t("journey_menu.location_changed", lang, formating=False, default="🧭 Группа изменила направление и перешла к локации: {location}!")
            text += "\n" + new_loc_lbl.format(location=new_loc_name)

        depth = event.get("depth", 1 if sub_loc else 0)
        if depth > 0:
            indent = "  " * depth
            lines = text.split("\n")
            text = "\n".join(f"{indent}↳ {line}" if i == 0 else f"{indent}  {line}" for i, line in enumerate(lines))

        return text

    @classmethod
    async def all_log(cls, logs: list, lang: str, journey_id: ObjectId) -> List[str]:
        from bot.modules.logs import log
        text, n, n_message = '', 0, 0
        messages = ['']

        for event in logs:
            try:
                m = await cls.generate_event_message(event, lang, journey_id)
                if m.strip().startswith("↳"):
                    text = f"{m}\n\n"
                else:
                    n += 1
                    text = f"🔹 <b>{n}.</b> {m}\n\n"
            except Exception as E:
                text = f'error generation - {event}\n{E}'
                log(text, 2, 'log generation')

            if len(messages[n_message]) >= 1700:
                messages.append('')
                n_message += 1
            messages[n_message] += text

        return messages
