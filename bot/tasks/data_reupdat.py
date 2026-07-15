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
        user_amounts[entry['userid']] += entry['amount']
    return sorted(
        [{'userid': uid, 'amount': amount} for uid, amount in user_amounts.items()],
        key=lambda x: x['amount'],
        reverse=True
    )

async def rayting_check():
    collection = User.get_settings().pymongo_collection

    # 1. Рейтинг по монетам (топ-1000)
    coins_cursor = collection.find(
        {}, 
        {'userid': 1, 'coins': 1}, 
        comment='rayting_check_coins_opt'
    ).sort([('coins', -1)]).limit(1000)
    coins_list = await coins_cursor.to_list(length=1000)
    coins_ids = [user['userid'] for user in coins_list]

    # 2. Рейтинг по уровням (топ-1000)
    lvl_cursor = collection.find(
        {}, 
        {'userid': 1, 'lvl': 1, 'xp': 1}, 
        comment='rayting_check_lvl_opt'
    ).sort([('lvl', -1), ('xp', -1)]).limit(1000)
    lvl_list = await lvl_cursor.to_list(length=1000)
    lvl_ids = [user['userid'] for user in lvl_list]

    # 3. Рейтинг по супер-монетам (топ-1000)
    super_cursor = collection.find(
        {}, 
        {'userid': 1, 'super_coins': 1}, 
        comment='rayting_check_super_opt'
    ).sort([('super_coins', -1)]).limit(1000)
    super_list = await super_cursor.to_list(length=1000)
    super_ids = [user['userid'] for user in super_list]
    
    await redis_set('rayting:coins', {'data': coins_list, 'ids': coins_ids})
    await redis_set('rayting:lvl', {'data': lvl_list, 'ids': lvl_ids})
    await redis_set('rayting:super', {'data': super_list, 'ids': super_ids})

    # Обновление рейтинга донатов 
    history_all = await get_history()
    history_30 = await get_history(30)

    donat_all_list = calculate_donations(history_all)[:1000]
    donat_30_list = calculate_donations(history_30)[:1000]

    donat_all_ids = [i['userid'] for i in donat_all_list]
    donat_30_ids = [i['userid'] for i in donat_30_list]

    await redis_set('rayting:dontaion_all', {'data': donat_all_list, 'ids': donat_all_ids})
    await redis_set('rayting:dontaion_30d', {'data': donat_30_list, 'ids': donat_30_ids})

    # Генерация новых изображений рейтинга в фоне и сброс кеша file_id
    from bot.modules.images_creators.rayting_image import generate_rayting_image
    from bot.redismanager import redis_del
    try:
        await generate_rayting_image('coins', coins_list[:3])
        await redis_del('rayting:file_id:coins')
    except Exception as e:
        log(f"Error generating coins rating image: {e}", 2)

    try:
        await generate_rayting_image('lvl', lvl_list[:3])
        await redis_del('rayting:file_id:lvl')
    except Exception as e:
        log(f"Error generating lvl rating image: {e}", 2)

    try:
        await generate_rayting_image('super', super_list[:3])
        await redis_del('rayting:file_id:super')
    except Exception as e:
        log(f"Error generating super rating image: {e}", 2)

    try:
        await generate_rayting_image('dontaion_all', donat_all_list[:3])
        await redis_del('rayting:file_id:dontaion_all')
    except Exception as e:
        log(f"Error generating donation_all rating image: {e}", 2)

    try:
        await generate_rayting_image('dontaion_30d', donat_30_list[:3])
        await redis_del('rayting:file_id:dontaion_30d')
    except Exception as e:
        log(f"Error generating donation_30d rating image: {e}", 2)

    from bot.modules.user.achievements import update_floating_ranking
    if coins_ids:
        await update_floating_ranking("top_coins", coins_ids[0])
    if lvl_ids:
        await update_floating_ranking("top_lvl", lvl_ids[0])
    if super_ids:
        await update_floating_ranking("top_super_coins", super_ids[0])
    if donat_all_ids:
        await update_floating_ranking("top_support", donat_all_ids[0])

    # Update new floating achievements
    try:
        from bot.models.dinosaur import DinoOwners
        from bot.models.user import Friend, Referral

        # 1. top_dino_count
        dino_counts = await DinoOwners.get_settings().pymongo_collection.aggregate([
            {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]).to_list(length=1)
        if dino_counts and dino_counts[0].get("_id"):
            await update_floating_ranking("top_dino_count", dino_counts[0]["_id"])

        # 2. top_market_count
        market_count_users = await User.get_settings().pymongo_collection.find(
            {"settings.market_sell_count": {"$exists": True}}
        ).sort("settings.market_sell_count", -1).limit(1).to_list(length=1)
        if market_count_users:
            await update_floating_ranking("top_market_count", market_count_users[0]["userid"])

        # 3. top_market_coins
        market_coins_users = await User.get_settings().pymongo_collection.find(
            {"settings.market_sell_total": {"$exists": True}}
        ).sort("settings.market_sell_total", -1).limit(1).to_list(length=1)
        if market_coins_users:
            await update_floating_ranking("top_market_coins", market_coins_users[0]["userid"])

        # 4. top_friends_count
        friend_counts = await Friend.get_settings().pymongo_collection.aggregate([
            {"$group": {"_id": "$userid", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]).to_list(length=1)
        if friend_counts and friend_counts[0].get("_id"):
            await update_floating_ranking("top_friends_count", friend_counts[0]["_id"])

        # 5. top_invite_count
        invite_counts = await Referral.get_settings().pymongo_collection.aggregate([
            {"$group": {"_id": "$referrer_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]).to_list(length=1)
        if invite_counts and invite_counts[0].get("_id"):
            await update_floating_ranking("top_invite_count", invite_counts[0]["_id"])

        # 6. top_single_item_count
        from bot.models.items import Item
        item_counts = await Item.get_settings().pymongo_collection.aggregate([
            {"$match": {"owner": {"$type": "number"}}},
            {"$group": {"_id": {"owner": "$owner", "item_id": "$items_data.item_id"}, "total_count": {"$sum": "$count"}}},
            {"$sort": {"total_count": -1}},
            {"$limit": 1}
        ]).to_list(length=1)
        if item_counts and item_counts[0].get("_id"):
            leader_id = item_counts[0]["_id"]["owner"]
            await update_floating_ranking("top_single_item_count", leader_id)
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
                        value = user_doc.settings.get("market_sell_count", 0) if user_doc.settings else 0
                    elif ach_id == "top_market_coins":
                        value = user_doc.settings.get("market_sell_total", 0) if user_doc.settings else 0
                    elif ach_id == "top_friends_count":
                        from bot.models.user import Friend
                        value = await Friend.find(Friend.userid == userid).count()
                    elif ach_id == "top_invite_count":
                        from bot.models.user import Referral
                        value = await Referral.find(Referral.referrer_id == userid).count()
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
        await redis_set('rayting:achievements', {'data': ach_data})
    except Exception as e:
        from bot.modules.logs import log
        log(f"Error updating new floating rankings: {e}", 4)

    await redis_set('rayting:update_time', {'time': int(time())})



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
    upd_data = {}
    dinos = list(await dinosaurs.find({}, 
                    {'data_id': 1}, 
                    comment='dino_statistic_dinosaurs'
                    ))

    for i in dinos:
        data_id = i['data_id']
        upd_data[str(data_id)] = upd_data.get(str(data_id), 0) + 1

    await redis_set('dino:statistic', {'data': upd_data, 'all_count': len(dinos)})


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(rayting_check, 3600, 15.0)
        add_task(statistic_check, 3600, 30.0)
        add_task(dino_kindergarten, 1800, 15.0)
        add_task(kindergarten_update, 43200, 30.0)
        add_task(dino_statistic, 7200, 60.0)