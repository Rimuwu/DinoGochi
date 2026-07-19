import asyncio
import datetime
import time
import json
from bson import ObjectId
from aiogram.types import InputRichMessage

from bot.config import conf
from bot.exec import bot
from bot.taskmanager import add_task
from bot.modules.logs import log
from bot.modules.localization import t

from bot.models.items import Item
from bot.models.arena import ArenaBattleModel
from bot.models.dinosaur import Dino, DeadDino, DinoOwners
from bot.models.user import User
from bot.modules.items.item import get_data, get_name

def get_seconds_to_next_midnight():
    now = datetime.datetime.now()
    next_midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((next_midnight - now).total_seconds())

async def generate_stats_report(lang: str, clear_logs: bool = False) -> list[dict]:
    now_ts = int(time.time())
    start_of_today = now_ts - 24 * 3600
    
    msg_list = []
    
    # Table headers translation helpers
    h_level = t("stats_report.table_header_level", lang, default="Level")
    h_count = t("stats_report.item_table_header_count", lang, default="Count")
    h_hour = t("stats_report.table_header_hour", lang, default="Hour")
    h_location = t("stats_report.table_header_location", lang, default="Location")
    h_enemy = t("stats_report.table_header_enemy", lang, default="Enemy")
    h_name = t("stats_report.item_table_header_name", lang, default="Item")
    
    # --- 1. LEVEL OF ITEMS ---
    col = Item.get_settings().pymongo_collection
    pipeline = [
        {
            "$match": {
                "items_data.abilities.lvl": {"$exists": True, "$ne": None, "$gte": 1, "$lte": 10}
            }
        },
        {
            "$group": {
                "_id": "$items_data.abilities.lvl",
                "total_count": {"$sum": "$count"}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    cursor = col.aggregate(pipeline)
    lvl_results = await cursor.to_list(length=100)
    
    items_by_level_title = t("stats_report.items_by_level", lang)
    
    if lvl_results:
        table_rows = [f"<tr><th><b>{h_level}</b></th><th><b>{h_count}</b></th></tr>"]
        for r in lvl_results:
            table_rows.append(f"<tr><td>+{r['_id']}</td><td>{r['total_count']}</td></tr>")
        lvl_table = f'<table border="1">{"".join(table_rows)}</table>'
        html_msg = f"{items_by_level_title}<br/>{lvl_table}"
    else:
        html_msg = f"{items_by_level_title}<br/>{t('stats_report.no_leveled_items', lang)}"
    msg_list.append({"title": items_by_level_title, "html": html_msg})
    
    # --- 2. ARENA BATTLES ---
    battles = await ArenaBattleModel.find(ArenaBattleModel.battle_time >= start_of_today).to_list()
    total_battles = len(battles)
    
    arena_battles_title = t("stats_report.arena_battles", lang)
    if total_battles > 0:
        hours_count = {}
        for b in battles:
            h = datetime.datetime.fromtimestamp(b.battle_time).hour
            hours_count[h] = hours_count.get(h, 0) + 1
        sorted_hours = sorted(hours_count.items(), key=lambda x: x[1], reverse=True)
        
        table_rows = [f"<tr><th><b>{h_hour}</b></th><th><b>{h_count}</b></th></tr>"]
        for h, cnt in sorted_hours[:3]:
            table_rows.append(f"<tr><td>{h:02d}:00-{h+1:02d}:00</td><td>{cnt}</td></tr>")
        peaks_table = f'<table border="1">{"".join(table_rows)}</table>'
        
        arena_text = t("stats_report.arena_count", lang, count=total_battles) + "<br/><br/>" + peaks_table
    else:
        arena_text = t("stats_report.no_arena_battles", lang)
        
    msg_list.append({"title": arena_battles_title, "html": f"{arena_battles_title}<br/>{arena_text}"})
    
    # --- 3. JOURNEYS ---
    from bot.redismanager import get_redis
    redis = get_redis()
    
    if clear_logs:
        pipe = redis.pipeline()
        pipe.lrange("global_journeys_today", 0, -1)
        pipe.delete("global_journeys_today")
        results = await pipe.execute()
        raw_journeys = results[0]
    else:
        raw_journeys = await redis.lrange("global_journeys_today", 0, -1)
        
    journeys = []
    for rj in raw_journeys:
        try:
            journeys.append(json.loads(rj))
        except Exception:
            pass
            
    total_journeys = len(journeys)
    journeys_title = t("stats_report.journeys", lang)
    
    if total_journeys > 0:
        loc_counts = {}
        for j in journeys:
            loc = j.get("location", "unknown")
            loc_counts[loc] = loc_counts.get(loc, 0) + 1
        sorted_locs = sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)
        
        table_rows = [f"<tr><th><b>{h_location}</b></th><th><b>{h_count}</b></th></tr>"]
        for loc, cnt in sorted_locs:
            loc_name_key = f"journey_start.locations.{loc}.name"
            loc_name = t(loc_name_key, lang)
            if "no_text_key" in loc_name or loc_name == loc_name_key:
                loc_name = loc.capitalize()
            table_rows.append(f"<tr><td>{loc_name}</td><td>{cnt}</td></tr>")
        locs_table = f'<table border="1">{"".join(table_rows)}</table>'
        
        journey_text = t("stats_report.journey_count", lang, count=total_journeys) + "<br/><br/>" + locs_table
    else:
        journey_text = t("stats_report.no_journeys", lang)
        
    msg_list.append({"title": journeys_title, "html": f"{journeys_title}<br/>{journey_text}"})
    
    # --- 4. DEFEATED ENEMIES ---
    if clear_logs:
        pipe = redis.pipeline()
        pipe.lrange("global_defeated_mobs_today", 0, -1)
        pipe.delete("global_defeated_mobs_today")
        results = await pipe.execute()
        raw_mobs = results[0]
    else:
        raw_mobs = await redis.lrange("global_defeated_mobs_today", 0, -1)
        
    mobs = []
    for rm in raw_mobs:
        if isinstance(rm, bytes):
            mobs.append(rm.decode('utf-8'))
        else:
            mobs.append(str(rm))
            
    total_mobs = len(mobs)
    defeated_title = t("stats_report.defeated_mobs", lang)
    
    if total_mobs > 0:
        mob_counts = {}
        for m_id in mobs:
            mob_counts[m_id] = mob_counts.get(m_id, 0) + 1
        sorted_mobs = sorted(mob_counts.items(), key=lambda x: x[1], reverse=True)
        
        table_rows = [f"<tr><th><b>{h_enemy}</b></th><th><b>{h_count}</b></th></tr>"]
        for m_id, cnt in sorted_mobs:
            trans = t(f"mobs.{m_id}.name", lang)
            if "mobs." in trans:
                trans = m_id.capitalize()
            emoji = t(f"mobs.{m_id}.emoji", lang)
            emoji_str = emoji if "mobs." not in emoji else "👾"
            table_rows.append(f"<tr><td>{emoji_str} {trans}</td><td>{cnt}</td></tr>")
        mobs_table = f'<table border="1">{"".join(table_rows)}</table>'
        
        defeated_text = t("stats_report.defeated_mobs_count", lang, count=total_mobs) + "<br/><br/>" + mobs_table
    else:
        defeated_text = t("stats_report.no_defeated_mobs", lang)
        
    msg_list.append({"title": defeated_title, "html": f"{defeated_title}<br/>{defeated_text}"})
    
    # --- 4.1. MARKET SALES ---
    if clear_logs:
        pipe = redis.pipeline()
        pipe.lrange("global_market_sales_today", 0, -1)
        pipe.delete("global_market_sales_today")
        results = await pipe.execute()
        raw_sales = results[0]
    else:
        raw_sales = await redis.lrange("global_market_sales_today", 0, -1)

    sales = []
    for rs in raw_sales:
        try:
            sales.append(json.loads(rs))
        except Exception:
            pass

    total_sales_count = len(sales)
    market_sales_title = t("stats_report.market_sales", lang)

    if total_sales_count > 0:
        grouped_sales = {}
        for s in sales:
            item_id = s.get("item_id")
            if item_id:
                if item_id not in grouped_sales:
                    grouped_sales[item_id] = {"count": 0, "total_price": 0.0}
                grouped_sales[item_id]["count"] += s.get("count", 0)
                grouped_sales[item_id]["total_price"] += s.get("price", 0.0)

        total_sold_items = sum(g["count"] for g in grouped_sales.values())
        h_avg_price = t("stats_report.table_header_avg_price", lang, default="Avg Price")

        table_rows = [f"<tr><th><b>{h_name}</b></th><th><b>{h_count}</b></th><th><b>{h_avg_price}</b></th></tr>"]
        sorted_sales = sorted(grouped_sales.items(), key=lambda x: x[1]["count"], reverse=True)
        for item_id, data in sorted_sales:
            item_name = get_name(item_id, lang, html=True)
            if not item_name:
                item_name = t("stats_report.unknown_item", lang, item_id=item_id)
            avg_price = data["total_price"] / data["count"] if data["count"] > 0 else 0.0
            avg_price_str = f"{avg_price:.1f}" if avg_price % 1 != 0 else f"{int(avg_price)}"
            table_rows.append(f"<tr><td>{item_name}</td><td>{data['count']}</td><td>{avg_price_str} 🪙</td></tr>")
        sales_table = f'<table border="1">{"".join(table_rows)}</table>'

        market_text = t("stats_report.market_total_count", lang, count=total_sold_items) + "<br/><br/>" + sales_table
    else:
        market_text = t("stats_report.no_market_sales", lang)

    msg_list.append({"title": market_sales_title, "html": f"{market_sales_title}<br/>{market_text}"})

    # --- 5 & 6. DINO BIRTHS & DEATHS & SKILLS BREAKDOWN ---
    start_id = ObjectId.from_datetime(datetime.datetime.fromtimestamp(start_of_today, tz=datetime.timezone.utc))
    born_count = await Dino.find({"_id": {"$gte": start_id}}).count()
    dead_count = await DeadDino.find({"_id": {"$gte": start_id}}).count()
    
    dino_text = t("stats_report.dino_stats", lang, born=born_count, dead=dead_count)
    dino_title = dino_text.split('</h3>')[0] + '</h3>' if '</h3>' in dino_text else dino_text
    
    col_dino = Dino.get_settings().pymongo_collection
    pipeline_skills = [
        {
            "$project": {
                "power_val": {"$ifNull": ["$stats.power", 0]},
                "dexterity_val": {"$ifNull": ["$stats.dexterity", 0]},
                "intelligence_val": {"$ifNull": ["$stats.intelligence", 0]},
                "charisma_val": {"$ifNull": ["$stats.charisma", 0]}
            }
        },
        {
            "$project": {
                "power_group": {
                    "$cond": [
                        {"$eq": ["$power_val", 0]}, "0",
                        {"$cond": [{"$lte": ["$power_val", 5]}, "1-5",
                        {"$cond": [{"$lte": ["$power_val", 10]}, "6-10",
                        {"$cond": [{"$lte": ["$power_val", 15]}, "11-15",
                        {"$cond": [{"$lte": ["$power_val", 20]}, "16-20", "21+"]}]}]}]}]
                },
                "dexterity_group": {
                    "$cond": [
                        {"$eq": ["$dexterity_val", 0]}, "0",
                        {"$cond": [{"$lte": ["$dexterity_val", 5]}, "1-5",
                        {"$cond": [{"$lte": ["$dexterity_val", 10]}, "6-10",
                        {"$cond": [{"$lte": ["$dexterity_val", 15]}, "11-15",
                        {"$cond": [{"$lte": ["$dexterity_val", 20]}, "16-20", "21+"]}]}]}]}]
                },
                "intelligence_group": {
                    "$cond": [
                        {"$eq": ["$intelligence_val", 0]}, "0",
                        {"$cond": [{"$lte": ["$intelligence_val", 5]}, "1-5",
                        {"$cond": [{"$lte": ["$intelligence_val", 10]}, "6-10",
                        {"$cond": [{"$lte": ["$intelligence_val", 15]}, "11-15",
                        {"$cond": [{"$lte": ["$intelligence_val", 20]}, "16-20", "21+"]}]}]}]}]
                },
                "charisma_group": {
                    "$cond": [
                        {"$eq": ["$charisma_val", 0]}, "0",
                        {"$cond": [{"$lte": ["$charisma_val", 5]}, "1-5",
                        {"$cond": [{"$lte": ["$charisma_val", 10]}, "6-10",
                        {"$cond": [{"$lte": ["$charisma_val", 15]}, "11-15",
                        {"$cond": [{"$lte": ["$charisma_val", 20]}, "16-20", "21+"]}]}]}]}]
                }
            }
        },
        {
            "$facet": {
                "power": [{"$group": {"_id": "$power_group", "count": {"$sum": 1}}}],
                "dexterity": [{"$group": {"_id": "$dexterity_group", "count": {"$sum": 1}}}],
                "intelligence": [{"$group": {"_id": "$intelligence_group", "count": {"$sum": 1}}}],
                "charisma": [{"$group": {"_id": "$charisma_group", "count": {"$sum": 1}}}]
            }
        }
    ]
    cursor_skills = col_dino.aggregate(pipeline_skills)
    skills_results = await cursor_skills.to_list(length=1)
    
    stats_data = {
        "power": {},
        "dexterity": {},
        "intelligence": {},
        "charisma": {}
    }
    if skills_results:
        result_doc = skills_results[0]
        for attr in ["power", "dexterity", "intelligence", "charisma"]:
            for group in result_doc.get(attr, []):
                g_id = group.get("_id")
                if g_id:
                    stats_data[attr][g_id] = group.get("count", 0)
                    
    h_range = t("stats_report.table_header_range", lang, default="Range")
    h_power = t("stats_report.stat_power", lang, default="Power")
    h_dexterity = t("stats_report.stat_dexterity", lang, default="Dexterity")
    h_intelligence = t("stats_report.stat_intelligence", lang, default="Intelligence")
    h_charisma = t("stats_report.stat_charisma", lang, default="Charisma")
    
    ranges_list = ["0", "1-5", "6-10", "11-15", "16-20"]
    skills_table_rows = [f"<tr><th><b>{h_range}</b></th><th><b>{h_power}</b></th><th><b>{h_dexterity}</b></th><th><b>{h_intelligence}</b></th><th><b>{h_charisma}</b></th></tr>"]
    for r in ranges_list:
        p_cnt = stats_data["power"].get(r, 0)
        d_cnt = stats_data["dexterity"].get(r, 0)
        i_cnt = stats_data["intelligence"].get(r, 0)
        c_cnt = stats_data["charisma"].get(r, 0)
        skills_table_rows.append(f"<tr><td>{r}</td><td>{p_cnt}</td><td>{d_cnt}</td><td>{i_cnt}</td><td>{c_cnt}</td></tr>")
        
    skills_table_html = f'<table border="1">{"".join(skills_table_rows)}</table>'
    skills_title = t("stats_report.dino_skills_title", lang, default="Dinosaur Skills Breakdown")
    msg_list.append({"title": dino_title, "html": f"{dino_text}{skills_title}<br/><br/>{skills_table_html}"})
    
    # --- 7. RARITY TABLES (5 messages) ---
    all_items = await Item.find_all().to_list()
    item_counts = {}
    for item in all_items:
        item_id = item.item_id
        item_counts[item_id] = item_counts.get(item_id, 0) + item.count
        
    rarity_groups = {
        'mystical': [],
        'legendary': [],
        'rare': [],
        'uncommon': [],
        'common': []
    }
    for item_id, count in item_counts.items():
        data = get_data(item_id)
        rank = data.get('rank', 'common')
        if rank not in rarity_groups:
            rarity_groups[rank] = []
        rarity_groups[rank].append((item_id, count))
        
    ranks_order = ['mystical', 'legendary', 'rare', 'uncommon', 'common']
    for rank in ranks_order:
        items_list = rarity_groups.get(rank, [])
        rank_name = t(f"stats_report.rarity.{rank}", lang)
        table_title = t("stats_report.item_count_title", lang, rarity_name=rank_name)
        
        if items_list:
            items_list.sort(key=lambda x: x[1], reverse=True)
            table_rows = [f"<tr><th><b>{h_name}</b></th><th><b>{h_count}</b></th></tr>"]
            for item_id, count in items_list:
                item_name = get_name(item_id, lang, html=True)
                if not item_name:
                    item_name = t("stats_report.unknown_item", lang, item_id=item_id)
                table_rows.append(f"<tr><td>{item_name}</td><td>{count}</td></tr>")
            table_html = f'<table border="1">{"".join(table_rows)}</table>'
            msg = f"{table_title}<br/><br/>{table_html}"
        else:
            msg = f"{table_title}<br/><br/><i>{t('stats_report.no_items_of_rarity', lang, default='No items of this rarity.')}</i>"
        
        msg_list.append({"title": table_title, "html": msg})

    # --- 8. USER STATISTICS ---
    users_stats_title = t("stats_report.users_stats_title", lang, default="👥 User Statistics")
    h_metric = t("stats_report.table_header_metric", lang, default="Metric")
    h_users = t("stats_report.table_header_users", lang, default="Users")
    
    m_level = t("stats_report.metric_level", lang, default="Level")
    m_coins = t("stats_report.metric_coins", lang, default="Coins")
    m_super_coins = t("stats_report.metric_super_coins", lang, default="Super Coins")
    m_dinosaurs = t("stats_report.metric_dinosaurs", lang, default="Dinosaurs per player")
    
    col_users = User.get_settings().pymongo_collection
    
    # 8.1. Level Distribution (from 0 to 200+)
    lvl_pipeline = [
        {
            "$project": {
                "lvl_group": {
                    "$cond": [
                        {"$eq": ["$lvl", 0]}, "0",
                        {"$cond": [{"$lte": ["$lvl", 10]}, "1-10",
                        {"$cond": [{"$lte": ["$lvl", 30]}, "11-30",
                        {"$cond": [{"$lte": ["$lvl", 50]}, "31-50",
                        {"$cond": [{"$lte": ["$lvl", 80]}, "51-80",
                        {"$cond": [{"$lte": ["$lvl", 100]}, "81-100",
                        {"$cond": [{"$lte": ["$lvl", 150]}, "101-150",
                        {"$cond": [{"$lte": ["$lvl", 200]}, "151-200", "201+"]}]}]}]}]}]}]}]
                }
            }
        },
        {
            "$group": {
                "_id": "$lvl_group",
                "count": {"$sum": 1}
            }
        }
    ]
    lvl_cursor = col_users.aggregate(lvl_pipeline)
    lvl_dist_res = await lvl_cursor.to_list(length=100)
    lvl_dist = {r["_id"]: r["count"] for r in lvl_dist_res}

    # 8.2. Coins Distribution (up to 200m)
    coins_pipeline = [
        {
            "$project": {
                "coins_group": {
                    "$cond": [
                        {"$lte": ["$coins", 999]}, "0-999",
                        {"$cond": [{"$lte": ["$coins", 9999]}, "1 000-9 999",
                        {"$cond": [{"$lte": ["$coins", 99999]}, "10 000-99 999",
                        {"$cond": [{"$lte": ["$coins", 999999]}, "100 000-999 999",
                        {"$cond": [{"$lte": ["$coins", 9999999]}, "1 000 000-9 999 999",
                        {"$cond": [{"$lte": ["$coins", 49999999]}, "10 000 000-49 999 999",
                        {"$cond": [{"$lte": ["$coins", 99999999]}, "50 000 000-99 999 999",
                        {"$cond": [{"$lte": ["$coins", 199999999]}, "100 000 000-199 999 999", "200 000 000+"]}]}]}]}]}]}]}]
                }
            }
        },
        {
            "$group": {
                "_id": "$coins_group",
                "count": {"$sum": 1}
            }
        }
    ]
    coins_cursor = col_users.aggregate(coins_pipeline)
    coins_dist_res = await coins_cursor.to_list(length=100)
    coins_dist = {r["_id"]: r["count"] for r in coins_dist_res}

    # 8.3. Super Coins Distribution (<100, and up to 50k)
    sc_pipeline = [
        {
            "$project": {
                "sc_group": {
                    "$cond": [
                        {"$lt": ["$super_coins", 100]}, "< 100",
                        {"$cond": [{"$lte": ["$super_coins", 499]}, "100-499",
                        {"$cond": [{"$lte": ["$super_coins", 999]}, "500-999",
                        {"$cond": [{"$lte": ["$super_coins", 4999]}, "1 000-4 999",
                        {"$cond": [{"$lte": ["$super_coins", 9999]}, "5 000-9 999",
                        {"$cond": [{"$lte": ["$super_coins", 49999]}, "10 000-49 999", "50 000+"]}]}]}]}]}]
                }
            }
        },
        {
            "$group": {
                "_id": "$sc_group",
                "count": {"$sum": 1}
            }
        }
    ]
    sc_cursor = col_users.aggregate(sc_pipeline)
    sc_dist_res = await sc_cursor.to_list(length=100)
    sc_dist = {r["_id"]: r["count"] for r in sc_dist_res}

    # 8.4. Dinosaurs per User Distribution (up to 30)
    col_owners = DinoOwners.get_settings().pymongo_collection
    dino_pipeline = [
        {
            "$match": {
                "type": "owner"
            }
        },
        {
            "$group": {
                "_id": "$owner_id",
                "dino_count": {"$sum": 1}
            }
        }
    ]
    dino_cursor = col_owners.aggregate(dino_pipeline)
    dino_dist_res = await dino_cursor.to_list(length=1000000)
    
    dino_counts_by_qty = {str(i): 0 for i in range(1, 30)}
    dino_counts_by_qty["30+"] = 0
    
    for r in dino_dist_res:
        qty = r["dino_count"]
        if qty >= 30:
            dino_counts_by_qty["30+"] += 1
        else:
            dino_counts_by_qty[str(qty)] += 1
            
    total_users_count = await User.find_all().count()
    users_with_dinos = await col_owners.distinct("owner_id", {"type": "owner"})
    users_with_0_dinos = max(0, total_users_count - len(users_with_dinos))

    # Format tables
    lvl_rows = [f"<tr><th><b>{m_level}</b></th><th><b>{h_users}</b></th></tr>"]
    for r in ["0", "1-10", "11-30", "31-50", "51-80", "81-100", "101-150", "151-200", "201+"]:
        lvl_rows.append(f"<tr><td>{r}</td><td>{lvl_dist.get(r, 0)}</td></tr>")
    lvl_table = f'<table border="1">{"".join(lvl_rows)}</table>'
    
    coins_rows = [f"<tr><th><b>{m_coins}</b></th><th><b>{h_users}</b></th></tr>"]
    for r in [
        "0-999", "1 000-9 999", "10 000-99 999", "100 000-999 999",
        "1 000 000-9 999 999", "10 000-49 999 999", "50 000 000-99 999 999",
        "100 000 000-199 999 999", "200 000 000+"
    ]:
        coins_rows.append(f"<tr><td>{r}</td><td>{coins_dist.get(r, 0)}</td></tr>")
    coins_table = f'<table border="1">{"".join(coins_rows)}</table>'
    
    sc_rows = [f"<tr><th><b>{m_super_coins}</b></th><th><b>{h_users}</b></th></tr>"]
    for r in ["< 100", "100-499", "500-999", "1 000-4 999", "5 000-9 999", "10 000-49 999", "50 000+"]:
        sc_rows.append(f"<tr><td>{r}</td><td>{sc_dist.get(r, 0)}</td></tr>")
    sc_table = f'<table border="1">{"".join(sc_rows)}</table>'
    
    dino_rows = [f"<tr><th><b>{m_dinosaurs}</b></th><th><b>{h_users}</b></th></tr>"]
    dino_rows.append(f"<tr><td>0</td><td>{users_with_0_dinos}</td></tr>")
    for r in range(1, 30):
        dino_rows.append(f"<tr><td>{r}</td><td>{dino_counts_by_qty[str(r)]}</td></tr>")
    dino_rows.append(f"<tr><td>30+</td><td>{dino_counts_by_qty['30+']}</td></tr>")
    dino_table = f'<table border="1">{"".join(dino_rows)}</table>'
    
    user_stats_html = (
        f"{users_stats_title}<br/><br/>"
        f"<b>📊 Level Distribution</b><br/>{lvl_table}<br/>"
        f"<b>💰 Coins Distribution</b><br/>{coins_table}<br/>"
        f"<b>💎 Super Coins Distribution</b><br/>{sc_table}<br/>"
        f"<b>🦕 Dinosaurs per Player</b><br/>{dino_table}"
    )
    msg_list.append({"title": users_stats_title, "html": user_stats_html})
        
    return msg_list

def make_message_link(chat_id: int | str, message_id: int) -> str:
    chat_str = str(chat_id)
    if '_' in chat_str:
        base_chat = chat_str.split('_')[0]
    else:
        base_chat = chat_str

    if base_chat.startswith('-100'):
        stripped = base_chat[4:]
        return f"https://t.me/c/{stripped}/{message_id}"
    elif base_chat.startswith('-'):
        stripped = base_chat[1:]
        return f"https://t.me/c/{stripped}/{message_id}"
    else:
        return f"https://t.me/c/{base_chat}/{message_id}"

async def send_rich_reports(chat_id: int | str, html_contents: list[dict], lang: str = 'en'):
    import re
    import datetime
    sent_messages = []
    for r in html_contents:
        html_content = r["html"]
        if isinstance(chat_id, str) and '_' in chat_id:
            channel_id, topic_id = chat_id.split('_', 2)
            msg = await bot.send_rich_message(
                chat_id=channel_id,
                rich_message=InputRichMessage(html=html_content),
                message_thread_id=int(topic_id)
            )
        else:
            msg = await bot.send_rich_message(
                chat_id=chat_id,
                rich_message=InputRichMessage(html=html_content)
            )
        if msg:
            sent_messages.append((r["title"], msg.message_id))
        await asyncio.sleep(0.5)

    if sent_messages:
        links_rows = []
        for title, msg_id in sent_messages:
            link = make_message_link(chat_id, msg_id)
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            links_rows.append(f'<tr><td><b>{clean_title}</b></td><td><a href="{link}">🔗 Go</a></td></tr>')
        
        final_title = t("stats_report.final_navigation_title", lang, default="Navigation Map")
        final_table = f'<table border="1">{"".join(links_rows)}</table>'
        
        time_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        gen_time_text = t("stats_report.generation_time", lang, time=time_str)
        
        final_html = f"📍 <b>{final_title}</b><br/><br/>{final_table}<br/><i>{gen_time_text}</i>"

        if isinstance(chat_id, str) and '_' in chat_id:
            channel_id, topic_id = chat_id.split('_', 2)
            await bot.send_rich_message(
                chat_id=channel_id,
                rich_message=InputRichMessage(html=final_html),
                message_thread_id=int(topic_id)
            )
        else:
            await bot.send_rich_message(
                chat_id=chat_id,
                rich_message=InputRichMessage(html=final_html)
            )

async def send_daily_stats():
    lang = getattr(conf, 'alert_lang', 'en')
    channel_id = getattr(conf, 'alert_channel_id', -1002440560821)
    
    log("Gathering daily statistics...", lvl=1)
    try:
        html_reports = await generate_stats_report(lang, clear_logs=True)
        log("Sending daily statistics reports...", lvl=1)
        await send_rich_reports(channel_id, html_reports, lang)
        log("Daily statistics reports successfully sent.", lvl=1)
    except Exception as e:
        log(f"Error in send_daily_stats: {e}", lvl=4)

if __name__ != '__main__':
    if conf.active_tasks:
        delay = get_seconds_to_next_midnight()
        log(f"Daily statistics task scheduled. Runs daily at 00:00. Time until next run: {delay} seconds.", lvl=1)
        add_task(send_daily_stats, 24 * 3600, delay)
