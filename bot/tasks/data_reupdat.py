from bot.modules.overwriting.DataCalsses import LazyCollection, RawLazyCollection
from bot.models.dinosaur import Dino
from bot.models.user import User
from bot.models.items import Item
from bot.models.group import Group
from bot.models.other import Statistic
from bot.models.activity import Kindergarten
# Чеки, обновляющие информацию о рейтинге или количестве объектов в базе
# Дабы не собирать информацию каждый раз при запросе пользователя
from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.donation import get_history
from bot.taskmanager import add_task
from datetime import datetime
from bot.modules.user.user import max_lvl_xp
from time import time
from bot.modules.notifications import user_notification
from bot.models.dinosaur import Dino
from bot.redismanager import redis_set
from bot.modules.logs import log


from collections import defaultdict
dinosaurs = LazyCollection(Dino)
users = LazyCollection(User)
items = LazyCollection(Item)
groups = LazyCollection(Group)
statistic = LazyCollection(Statistic)
kindergarten = LazyCollection(Kindergarten)

# Чек статистики, запускать раз в час
async def statistic_check():
    items_len = await items.count_documents({}, comment='statistic_check_items_len')
    users_len = await users.count_documents({}, comment='statistic_check_users_len')
    dinosaurs_len = await dinosaurs.count_documents({}, comment='statistic_check_dinosaurs_len')
    groups_len = await groups.count_documents({}, comment='statistic_check_groups_len')

    data = {
        'date': str(datetime.now().date()),
        'dinosaurs': dinosaurs_len,
        'users': users_len,
        'items': items_len,
        'groups': groups_len
    }
    if res := await statistic.find_one({'date': data['date']}, comment='statistic_check_res'):
        await statistic.delete_one({'_id': res['_id']}, comment='statistic_check_2')

    await statistic.insert_one(data, comment='statistic_check_1')

def calculate_donations(history):
    user_amounts = defaultdict(int)
    for entry in history:
        provider = entry.get('provider', 'stars')
        raw_amount = entry.get('amount', 0)
        try:
            amount = float(raw_amount or 0)
        except (ValueError, TypeError):
            amount = 0.0

        if provider == 'cryptobot':
            # Amount is stored in cents of USDT (e.g. 0.50 USDT = 50 cents).
            # 1 cent of USDT corresponds to 1 Star (XTR) in shop pricing ($0.50 = 50 Stars).
            if 0 < amount < 5:
                amount = amount * 100
            stars = int(amount)
        else:
            # stars payment: amount is directly in Stars (XTR)
            stars = int(amount)
        user_amounts[entry['userid']] += stars

    return sorted(
        [{'userid': uid, 'stars': stars, 'amount': stars} for uid, stars in user_amounts.items()],
        key=lambda x: x['stars'],
        reverse=True
    )

async def rating_check():
    collection = User.get_settings().pymongo_collection

    # 1. Рейтинг по монетам (топ-1000)
    coins_cursor = collection.find(
        {}, 
        {'userid': 1, 'coins': 1}, 
        comment='rating_check_coins_opt'
    ).sort([('coins', -1)]).limit(1000)
    coins_list = await coins_cursor.to_list(length=1000)
    coins_ids = [user['userid'] for user in coins_list]

    # 2. Рейтинг по уровням (топ-1000)
    lvl_cursor = collection.find(
        {}, 
        {'userid': 1, 'lvl': 1, 'xp': 1}, 
        comment='rating_check_lvl_opt'
    ).sort([('lvl', -1), ('xp', -1)]).limit(1000)
    lvl_list = await lvl_cursor.to_list(length=1000)
    lvl_ids = [user['userid'] for user in lvl_list]

    # 3. Рейтинг по супер-монетам (топ-1000)
    super_cursor = collection.find(
        {}, 
        {'userid': 1, 'super_coins': 1}, 
        comment='rating_check_super_opt'
    ).sort([('super_coins', -1)]).limit(1000)
    super_list = await super_cursor.to_list(length=1000)
    super_ids = [user['userid'] for user in super_list]
    
    await redis_set('rating:coins', {'data': coins_list, 'ids': coins_ids})
    await redis_set('rating:lvl', {'data': lvl_list, 'ids': lvl_ids})
    await redis_set('rating:super', {'data': super_list, 'ids': super_ids})

    # Arena ratings
    from bot.models.arena import ArenaPlayerModel
    solo_players = await ArenaPlayerModel.find(
        ArenaPlayerModel.elo_solo > 1000).sort([('elo_solo', -1)]).limit(1000).to_list()
    solo_list = [{'userid': p.userid, 'elo_solo': p.elo_solo} for p in solo_players]
    solo_ids = [p.userid for p in solo_players]
    await redis_set('rating:arena_solo', {'data': solo_list, 'ids': solo_ids})

    group_players = await ArenaPlayerModel.find(
        ArenaPlayerModel.elo_group > 1000).sort([('elo_group', -1)]).limit(1000).to_list()
    group_list = [{'userid': p.userid, 'elo_group': p.elo_group} for p in group_players]
    group_ids = [p.userid for p in group_players]
    await redis_set('rating:arena_group', {'data': group_list, 'ids': group_ids})

    # Обновление рейтинга донатов 
    history_all = await get_history()
    history_30 = await get_history(30)

    donat_all_list = calculate_donations(history_all)[:1000]
    donat_30_list = calculate_donations(history_30)[:1000]

    donat_all_ids = [i['userid'] for i in donat_all_list]
    donat_30_ids = [i['userid'] for i in donat_30_list]

    await redis_set('rating:dontaion_all', {'data': donat_all_list, 'ids': donat_all_ids})
    await redis_set('rating:dontaion_30d', {'data': donat_30_list, 'ids': donat_30_ids})

    # Генерация новых изображений рейтинга в фоне и сброс кеша file_id
    from bot.modules.images_creators.rating_image import generate_rating_image
    from bot.redismanager import redis_del
    try:
        await generate_rating_image('coins', coins_list[:3])
        await redis_del('rating:file_id:coins')
    except Exception as e:
        log(f"Error generating coins rating image: {e}", 2)

    try:
        await generate_rating_image('lvl', lvl_list[:3])
        await redis_del('rating:file_id:lvl')
    except Exception as e:
        log(f"Error generating lvl rating image: {e}", 2)

    try:
        await generate_rating_image('super', super_list[:3])
        await redis_del('rating:file_id:super')
    except Exception as e:
        log(f"Error generating super rating image: {e}", 2)

    try:
        await generate_rating_image('dontaion_all', donat_all_list[:3])
        await redis_del('rating:file_id:dontaion_all')
    except Exception as e:
        log(f"Error generating donation_all rating image: {e}", 2)

    try:
        await generate_rating_image('dontaion_30d', donat_30_list[:3])
        await redis_del('rating:file_id:dontaion_30d')
    except Exception as e:
        log(f"Error generating donation_30d rating image: {e}", 2)

    try:
        await generate_rating_image('arena_solo', solo_list[:3])
        await redis_del('rating:file_id:arena_solo')
    except Exception as e:
        log(f"Error generating arena_solo rating image: {e}", 2)

    try:
        await generate_rating_image('arena_group', group_list[:3])
        await redis_del('rating:file_id:arena_group')
    except Exception as e:
        log(f"Error generating arena_group rating image: {e}", 2)

    from bot.modules.user.achievements import update_floating_ranking
    if coins_list:
        max_coins = coins_list[0]['coins']
        if max_coins > 0:
            coins_candidates = [u['userid'] for u in coins_list if u['coins'] == max_coins]
            await update_floating_ranking("top_coins", coins_candidates)
        
    if lvl_list:
        max_lvl = lvl_list[0]['lvl']
        max_xp = lvl_list[0]['xp']
        if max_lvl > 0:
            lvl_candidates = [u['userid'] for u in lvl_list if u['lvl'] == max_lvl and u['xp'] == max_xp]
            await update_floating_ranking("top_lvl", lvl_candidates)
        
    if super_list:
        max_super = super_list[0]['super_coins']
        if max_super > 0:
            super_candidates = [u['userid'] for u in super_list if u['super_coins'] == max_super]
            await update_floating_ranking("top_super_coins", super_candidates)
        
    if donat_all_list:
        max_stars = donat_all_list[0]['stars']
        if max_stars > 0:
            donat_candidates = [u['userid'] for u in donat_all_list if u['stars'] == max_stars]
            await update_floating_ranking("top_support", donat_candidates)

    # Update new floating achievements
    try:
        from bot.models.dinosaur import DinoOwners
        from bot.models.user import Friend, Referral

        # 1. top_dino_count
        dino_counts = await DinoOwners.get_settings().pymongo_collection.aggregate([
            {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 100}
        ]).to_list(length=100)
        if dino_counts and dino_counts[0].get("_id"):
            max_dinos = dino_counts[0]["count"]
            if max_dinos > 0:
                dino_candidates = [d["_id"] for d in dino_counts if d["count"] == max_dinos]
                await update_floating_ranking("top_dino_count", dino_candidates)

        # 2. top_market_count
        from bot.models.market import Seller
        sellers_count = await Seller.get_settings().pymongo_collection.find(
            {"conducted": {"$gt": 0}}
        ).sort("conducted", -1).limit(100).to_list(length=100)
        if sellers_count:
            max_market_count = sellers_count[0].get('conducted', 0)
            if max_market_count > 0:
                market_count_candidates = [s["owner_id"] for s in sellers_count if s.get('conducted', 0) == max_market_count]
                await update_floating_ranking("top_market_count", market_count_candidates)

        # 3. top_market_coins
        sellers_coins = await Seller.get_settings().pymongo_collection.find(
            {"earned": {"$gt": 0}}
        ).sort("earned", -1).limit(100).to_list(length=100)
        if sellers_coins:
            max_market_total = sellers_coins[0].get('earned', 0)
            if max_market_total > 0:
                market_coins_candidates = [s["owner_id"] for s in sellers_coins if s.get('earned', 0) == max_market_total]
                await update_floating_ranking("top_market_coins", market_coins_candidates)

        # 4. top_friends_count
        friend_counts = await Friend.get_settings().pymongo_collection.aggregate([
            {"$group": {"_id": "$userid", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 100}
        ]).to_list(length=100)
        if friend_counts and friend_counts[0].get("_id"):
            max_friends = friend_counts[0]["count"]
            if max_friends > 0:
                friends_candidates = [f["_id"] for f in friend_counts if f["count"] == max_friends]
                await update_floating_ranking("top_friends_count", friends_candidates)

        # 5. top_invite_count
        invite_counts = await Referral.get_settings().pymongo_collection.aggregate([
            {"$match": {"type": "sub"}},
            {"$group": {"_id": "$code", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 100}
        ]).to_list(length=100)
        if invite_counts:
            max_invites = invite_counts[0]["count"]
            if max_invites > 0:
                top_codes = [i["_id"] for i in invite_counts if i["count"] == max_invites]
                gen_docs = await Referral.find({"code": {"$in": top_codes}, "type": "general"}).to_list()
                invite_candidates = [g.userid for g in gen_docs if g.userid]
                if invite_candidates:
                    await update_floating_ranking("top_invite_count", invite_candidates)

        # 6. top_single_item_count
        from bot.models.items import Item
        item_counts = await Item.get_settings().pymongo_collection.aggregate([
            {"$match": {"owner": {"$type": "number"}}},
            {"$group": {"_id": {"owner": "$owner", "item_id": "$items_data.item_id"}, 
            "total_count": {"$sum": "$count"}}},
            {"$sort": {"total_count": -1}},
            {"$limit": 100}
        ]).to_list(length=100)
        if item_counts and item_counts[0].get("_id"):
            max_items = item_counts[0]["total_count"]
            if max_items > 0:
                item_candidates = [i["_id"]["owner"] for i in item_counts if i["total_count"] == max_items]
                await update_floating_ranking("top_single_item_count", item_candidates)
        # Cache achievements top list
        from bot.models.user import Achievement
        from bot.const import ACHIEVEMENTS
        
        floating_ach_ids = [
            k for k, v in ACHIEVEMENTS.get('achievements', {}).items()
            if v.get('type') == 'floating'
        ]
        
        ach_data = []
        for ach_id in floating_ach_ids:
            ach_doc = await Achievement.find_one(
                Achievement.achievement_id == ach_id,
                Achievement.unlocked_time > 0
            )
            userid = None
            username = "—"
            value = 0
            item_id = None
            if ach_doc:
                userid = ach_doc.userid
                user_doc = await User.find_one(User.userid == userid)
                if user_doc:
                    username = await User.get_user_name(userid)
                    if username == 'NoName_NoUser':
                        username = str(userid)
                    
                    # Calculate metric value dynamically
                    if ach_id == "top_lvl":
                        value = user_doc.lvl
                    elif ach_id == "top_coins":
                        value = user_doc.coins
                    elif ach_id == "top_super_coins":
                        value = user_doc.super_coins
                    elif ach_id == "top_support":
                        value = next((item['amount'] for item in donat_all_list if item['userid'] == userid), 0)
                    elif ach_id == "top_dino_count":
                        from bot.models.dinosaur import DinoOwners
                        value = await DinoOwners.find(DinoOwners.owner_id == userid).count()
                    elif ach_id == "top_market_count":
                        from bot.models.market import Seller
                        seller_doc = await Seller.find_one(Seller.owner_id == userid)
                        seller_val = seller_doc.conducted if seller_doc else 0
                        user_val = user_doc.settings.get("market_sell_count", 0) if user_doc and user_doc.settings else 0
                        value = max(seller_val, user_val)
                    elif ach_id == "top_market_coins":
                        from bot.models.market import Seller
                        seller_doc = await Seller.find_one(Seller.owner_id == userid)
                        seller_val = seller_doc.earned if seller_doc else 0
                        user_val = user_doc.settings.get("market_sell_total", 0) if user_doc and user_doc.settings else 0
                        value = max(seller_val, user_val)
                    elif ach_id == "top_friends_count":
                        from bot.models.user import Friend
                        value = await Friend.find(Friend.userid == userid).count()
                    elif ach_id == "top_invite_count":
                        from bot.models.user import Referral
                        gen_doc = await Referral.find_one(Referral.userid == userid, Referral.type == "general")
                        if gen_doc and gen_doc.code:
                            value = await Referral.find(Referral.code == gen_doc.code, Referral.type == "sub").count()
                        else:
                            value = 0
                    elif ach_id == "top_single_item_count":
                        from bot.models.items import Item
                        user_items = await Item.get_settings().pymongo_collection.aggregate([
                            {"$match": {"owner": userid}},
                            {"$group": {"_id": "$items_data.item_id", "total_count": {"$sum": "$count"}}},
                            {"$sort": {"total_count": -1}},
                            {"$limit": 1}
                        ]).to_list(length=1)
                        value = user_items[0]["total_count"] if user_items else 0
                        item_id = user_items[0]["_id"] if user_items else None
            
            item_entry = {
                "ach_id": ach_id,
                "userid": userid,
                "username": username,
                "value": value
            }
            if item_id:
                item_entry["item_id"] = item_id
            ach_data.append(item_entry)
        await redis_set('rating:achievements', {'data': ach_data})
    except Exception as e:
        log(f"Error updating new floating rankings: {e}", 4)

    await redis_set('rating:update_time', {'time': int(time())})



async def kindergarten_update():
    data = list(await kindergarten.find({'type': 'save',
                                   'end': {'$lte': int(time())}}, comment='kindergarten_update')
                ).copy()

    for i in data: await kindergarten.delete_one({'_id': i['_id']}, comment='kindergarten_update_1')

async def dino_kindergarten():
    data = await Kindergarten.find(
        Kindergarten.type == 'dino',
        Kindergarten.end <= int(time())
    ).to_list()

    for i in data: 
        from bot.models.enums import DinoStatus
        if i.dino:
            dino_id = i.dino.ref.id
            await Dino.set_status(dino_id, DinoStatus.PASS)
            await i.delete()

            dino = await Dino.find_one(Dino.id == dino_id)
            if dino:
                owner = await Dino.get_owner_by_id(dino_id)
                if owner:
                    lang = await Dino.get_language(dino_id)
                    await user_notification(owner.owner_id, 'kindergarten', lang, 
                                    dino_name=dino.name, 
                                    dino_alt_id_markup=dino.alt_id)

async def dino_statistic():
    try:
        col = dinosaurs.pymongo_collection
        pipeline = [
            {"$group": {"_id": "$data_id", "count": {"$sum": 1}}}
        ]
        cursor = col.aggregate(pipeline, comment='dino_statistic_aggregate')
        results = await cursor.to_list(length=None)
        upd_data = {str(item["_id"]): item["count"] for item in results if item["_id"] is not None}
        all_count = sum(upd_data.values())
        await redis_set('dino:statistic', {'data': upd_data, 'all_count': all_count})
    except Exception as e:
        log(f"dino_statistic error: {e}", lvl=3)


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(rating_check, 3600, 15.0)
        add_task(statistic_check, 3600, 30.0)
        add_task(dino_kindergarten, 1800, 15.0)
        add_task(kindergarten_update, 43200, 30.0)
        add_task(dino_statistic, 7200, 60.0)