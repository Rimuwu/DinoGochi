from typing import Dict, Any, List, Optional
from random import randint, random
from bson import ObjectId
import time

from bot.config import conf
from bot.modules.data_format import transform
from bot.models.items import Item
from bot.models.dinosaur import Dino, DinoMood
from bot.models.activity import CollectingActivity
from bot.modules.items.item import counts_items
from bot.modules.items.item_tools import rare_random
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang
from bot.modules.quests import quest_process
from bot.models.user import User
from bot.models.other import Event
from bot.modules.logs import log
from bot.modules.task_queue import task_handler

REPEAT_MINUTS = 2
ENERGY_DOWN = 0.1 * REPEAT_MINUTS
LVL_CHANCE = 0.125 * REPEAT_MINUTS

advanced_rank_for_items = {
    "mystical": ["ink", "skin", "fish_oil", "twigs_tree", "feather", "wool"],
}

@task_handler("stop_collect")
async def stop_collect_task(data: dict):
    dino_id = data.get("dino_id")
    if dino_id:
        dino_oid = ObjectId(dino_id)
        # Calling end() will process all pre-simulated ticks up to current time
        await CollectingActivity.end(dino_oid, send_notif=True)

async def presimulate_collecting(dino, owner_id: int, coll_type: str, max_count: int, start_time: int):
    # 1. accessory check (without decrementing yet!)
    tooling = await Item.check_accessory(dino.id, 'tooling')
    rod = None
    net = None
    torch = None
    
    if coll_type == 'fishing':
        rod = await Item.check_accessory(dino.id, 'fishing-rod')
    elif coll_type == 'hunt':
        net = await Item.check_accessory(dino.id, 'net')
    elif coll_type == 'collecting':
        torch = await Item.check_accessory(dino.id, 'torch')
        
    # 2. check inspiration
    res = await DinoMood.check_inspiration(dino.id, 'collecting')
    is_inspired_collecting = bool(res)
    
    res_exp = await DinoMood.check_inspiration(dino.id, 'exp_boost')
    is_inspired_exp = bool(res_exp)
    
    # 3. compute base chance
    base_chance = 0.9 if is_inspired_collecting else 0.45
    if tooling:
        base_chance += 0.25 + tooling.get_level() * 0.05
        
    # 4. compute chances_add
    chances_add = {'common': 0, 'uncommon': 0, 'rare': 0, 'mystical': 0, 'legendary': 0}
    if coll_type == 'fishing' and rod:
        level = rod.get_level()
        chances_add['rare'] += 10 + level * 2
        chances_add['mystical'] += 5 + level * 1
        chances_add['legendary'] += 2 + level * 0.5
    elif coll_type == 'hunt' and net:
        level = net.get_level()
        chances_add['rare'] += 10 + level * 2
        chances_add['mystical'] += 5 + level * 1
        chances_add['legendary'] += 2 + level * 0.5
        
    char = 0
    if coll_type == 'collecting':
        char = dino.stats['intelligence']
    elif coll_type == 'fishing':
        char = dino.stats['dexterity']
    elif coll_type == 'hunt':
        char = dino.stats['power']
    elif coll_type == 'all':
        char = dino.stats['charisma']
        
    chances_add['rare'] += transform(char, 20, 22)
    chances_add['mystical'] += transform(char, 20, 13)
    chances_add['legendary'] += transform(char, 20, 2)
    
    # 5. compute items pools
    items_pool = []
    if coll_type == 'all':
        for i in ['collecting', 'hunt', 'fishing']:
            items_pool += get_group(f'{i}-activity')
        items_pool += get_group('all-activity')
    else:
        items_pool = get_group(f'{coll_type}-activity')
        
    # 6. event items
    event = await Event.get_event(f'add_{coll_type}')
    special_chance = {}
    if event:
        items_pool += event['data'].get('items', [])
        if 'special_chance' in event['data']:
            special_chance.update(event['data']['special_chance'])
            
    if coll_type == 'collecting' and torch:
        special_chance['gourmet_herbs'] = 15 + torch.get_level() * 3
        
    # 7. simulate ticks
    ticks = []
    now_count = 0
    tick_index = 0
    
    while now_count < max_count:
        tick_index += 1
        energy_lost = 0
        xp_gained = 0
        items_gained = {}
        downgrades = []
        
        # energy check
        if random() <= ENERGY_DOWN:
            energy_lost = 1
            
        # xp check
        if random() <= LVL_CHANCE:
            if is_inspired_exp:
                xp_gained = randint(1, 6)
            else:
                xp_gained = randint(1, 3)
        if randint(1, 100) + transform(dino.stats['charisma'], 20, 30) >= 90:
            xp_gained += randint(1, 5)
            
        # items check
        if random() <= base_chance:
            downgrades.append(('tooling', 'tooling'))
            if coll_type == 'fishing' and rod:
                downgrades.append(('fishing-rod', 'fishing-rod'))
            elif coll_type == 'hunt' and net:
                downgrades.append(('net', 'net'))
            elif coll_type == 'collecting' and torch:
                downgrades.append(('torch', 'torch'))
                
            count = randint(1, 3)
            if now_count + count > max_count:
                count = max_count - now_count
            now_count += count
            
            rand_items = rare_random(items_pool, count, chances_add, special_chance, None, advanced_rank_for_items)
            for it in rand_items:
                items_gained[it] = items_gained.get(it, 0) + 1
                
        ticks.append({
            "tick_index": tick_index,
            "trigger_time": start_time + tick_index * 120,
            "items": items_gained,
            "xp": xp_gained,
            "energy_lost": energy_lost,
            "count": now_count,
            "downgrades": downgrades
        })
        
    return ticks, start_time + tick_index * 120