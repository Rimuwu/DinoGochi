import asyncio
import os
import sys
from bson import ObjectId, DBRef
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

# Add current working directory to path
sys.path.insert(0, os.getcwd())

from bot.config import conf

# Override host to localhost for running outside Docker container
mongo_url = conf.mongo_url
if "mongo:27017" in mongo_url:
    mongo_url = mongo_url.replace("mongo:27017", "localhost:27017")

def resolve_userid(val, user_oid_to_userid):
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    if isinstance(val, DBRef):
        return user_oid_to_userid.get(val.id, 0)
    if isinstance(val, dict):
        if "$id" in val:
            oid = val["$id"]
            if isinstance(oid, str):
                try:
                    oid = ObjectId(oid)
                except:
                    pass
            return user_oid_to_userid.get(oid, 0)
        if "id" in val:
            oid = val["id"]
            if isinstance(oid, str):
                try:
                    oid = ObjectId(oid)
                except:
                    pass
            return user_oid_to_userid.get(oid, 0)
        if "_id" in val:
            oid = val["_id"]
            if isinstance(oid, str):
                try:
                    oid = ObjectId(oid)
                except:
                    pass
            return user_oid_to_userid.get(oid, 0)
    if isinstance(val, ObjectId):
        return user_oid_to_userid.get(val, 0)
    if isinstance(val, str):
        try:
            return user_oid_to_userid.get(ObjectId(val), 0)
        except:
            pass
        try:
            return int(val)
        except:
            pass
    return 0

async def migrate():
    print(f"Connecting to MongoDB: {mongo_url}")
    client = AsyncIOMotorClient(mongo_url)
    db = client["dinogochi"]

    print("Fetching users to build user cache...")
    user_oid_to_userid = {}
    async for user in db["users"].find({}):
        if "userid" in user and user["userid"]:
            user_oid_to_userid[user["_id"]] = int(user["userid"])

    print(f"Loaded {len(user_oid_to_userid)} users in cache.")

    # 1. Bulk renames of user_id -> userid and owner_id -> owner using fast $rename
    print("Performing fast field renames ($rename)...")
    renames = {
        "boosters": ("user_id", "userid"),
        "onetime_rewards": ("user_id", "userid"),
        "dino_collection": ("user_id", "userid"),
        "group_users": ("user_id", "userid"),
        "items": ("owner_id", "owner")
    }
    for col_name, (old_f, new_f) in renames.items():
        res = await db[col_name].update_many({old_f: {"$exists": True}}, {"$rename": {old_f: new_f}})
        if res.modified_count > 0:
            print(f"Renamed {old_f} -> {new_f} in '{col_name}': {res.modified_count} docs.")

    # 2. Standard user -> userid (integer) migrations using bulk_write
    collections_user_to_userid = [
        "referals", "subscriptions", "ads", "dino_collection", "achievements",
        "lottery_members", "dead_users", "boosters", "onetime_rewards", "donations",
        "preferential", "tracking_members", "item_craft", "lang", "message_log",
        "long_activity", "kindergarten", "group_users"
    ]
    for col_name in collections_user_to_userid:
        print(f"Migrating '{col_name}' (user -> userid)...")
        cursor = db[col_name].find({"user": {"$exists": True}})
        requests = []
        async for doc in cursor:
            old_user = doc["user"]
            userid = resolve_userid(old_user, user_oid_to_userid)
            requests.append(
                UpdateOne({"_id": doc["_id"]}, {"$set": {"userid": userid}, "$unset": {"user": ""}})
            )
        if requests:
            res = await db[col_name].bulk_write(requests, ordered=False)
            print(f"Updated '{col_name}': {res.modified_count} docs.")
        else:
            print(f"Finished '{col_name}': 0 docs updated.")

    # 3. Standard owner -> owner_id (integer) migrations using bulk_write
    collections_owner_to_ownerid = [
        "incubation", "dead_dinos", "dino_owners", "quests", "daily_award",
        "inside_shop", "sellers", "puhs", "farm"
    ]
    for col_name in collections_owner_to_ownerid:
        print(f"Migrating '{col_name}' (owner -> owner_id)...")
        cursor = db[col_name].find({"owner": {"$exists": True}})
        requests = []
        async for doc in cursor:
            old_owner = doc["owner"]
            owner_id = resolve_userid(old_owner, user_oid_to_userid)
            requests.append(
                UpdateOne({"_id": doc["_id"]}, {"$set": {"owner_id": owner_id}, "$unset": {"owner": ""}})
            )
        if requests:
            res = await db[col_name].bulk_write(requests, ordered=False)
            print(f"Updated '{col_name}': {res.modified_count} docs.")
        else:
            print(f"Finished '{col_name}': 0 docs updated.")

    # 4. Friends collection (user -> userid, friend -> friendid)
    print("Migrating 'friends' collection...")
    cursor = db["friends"].find({"$or": [{"user": {"$exists": True}}, {"friend": {"$exists": True}}]})
    requests = []
    async for doc in cursor:
        updates = {}
        unsets = {}
        if "user" in doc:
            updates["userid"] = resolve_userid(doc["user"], user_oid_to_userid)
            unsets["user"] = ""
        if "friend" in doc:
            updates["friendid"] = resolve_userid(doc["friend"], user_oid_to_userid)
            unsets["friend"] = ""
        if updates:
            op = {"$set": updates}
            if unsets:
                op["$unset"] = unsets
            requests.append(UpdateOne({"_id": doc["_id"]}, op))
    if requests:
        res = await db["friends"].bulk_write(requests, ordered=False)
        print(f"Updated 'friends' collection: {res.modified_count} docs.")
    else:
        print("Finished 'friends' collection: 0 docs updated.")

    # 5. Products collection (owner -> owner_id)
    print("Migrating 'products' collection...")
    cursor = db["products"].find({"$or": [{"owner": {"$exists": True}}, {"seller_id": {"$exists": True}}]})
    requests = []
    async for doc in cursor:
        updates = {}
        unsets = {}
        if "owner" in doc:
            updates["owner_id"] = resolve_userid(doc["owner"], user_oid_to_userid)
            unsets["owner"] = ""
        if "seller_id" in doc:
            unsets["seller_id"] = ""
        if updates or unsets:
            op = {}
            if updates:
                op["$set"] = updates
            if unsets:
                op["$unset"] = unsets
            requests.append(UpdateOne({"_id": doc["_id"]}, op))
    if requests:
        res = await db["products"].bulk_write(requests, ordered=False)
        print(f"Updated 'products' collection: {res.modified_count} docs.")
    else:
        print("Finished 'products' collection: 0 docs updated.")

    # 6. Companies & items: convert owner (DBRef/ObjectId -> int)
    print("Migrating 'companies' collection (owner -> int)...")
    cursor = db["companies"].find({"owner": {"$not": {"$type": "int"}}})
    requests = []
    async for doc in cursor:
        if "owner" in doc:
            owner = resolve_userid(doc["owner"], user_oid_to_userid)
            requests.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"owner": owner}}))
    if requests:
        res = await db["companies"].bulk_write(requests, ordered=False)
        print(f"Updated 'companies' collection: {res.modified_count} docs.")

    print("Migrating 'items' collection (owner -> int)...")
    cursor = db["items"].find({"owner": {"$not": {"$type": "int"}}})
    requests = []
    async for doc in cursor:
        if "owner" in doc:
            old_owner = doc["owner"]
            if isinstance(old_owner, str) and len(old_owner) == 24:
                try:
                    old_owner = ObjectId(old_owner)
                except:
                    pass
            owner = resolve_userid(old_owner, user_oid_to_userid)
            requests.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"owner": owner}}))
    if requests:
        res = await db["items"].bulk_write(requests, ordered=False)
        print(f"Updated 'items' collection: {res.modified_count} docs.")

    # 7. Convert dino_id -> dino (DBRef to dinosaurs) using bulk_write
    dino_id_collections = ["dino_owners", "dino_mood", "state", "kd_activity", "long_activity", "item_craft"]
    for col_name in dino_id_collections:
        # Drop old indexes containing dino_id/dino to prevent duplicate key errors during migration/unset
        try:
            indexes = await db[col_name].list_indexes().to_list()
            for index in indexes:
                if any(k in index["key"] for k in ["dino", "dino_id"]):
                    index_name = index["name"]
                    if index_name != "_id_":
                        await db[col_name].drop_index(index_name)
                        print(f"Dropped index '{index_name}' in '{col_name}'")
        except Exception as e:
            print(f"Could not drop index in {col_name}: {e}")

        # Remove orphaned long_activity documents
        if col_name == "long_activity":
            try:
                del_res = await db["long_activity"].delete_many({
                    "$or": [
                        {"dino_id": None},
                        {"dino_id": {"$exists": False}}
                    ]
                })
                print(f"Deleted {del_res.deleted_count} orphaned documents from 'long_activity'")
            except Exception as e:
                print(f"Could not clean up long_activity: {e}")

        cursor = db[col_name].find({"dino_id": {"$exists": True}})
        requests = []
        async for doc in cursor:
            old_dino = doc["dino_id"]
            if old_dino:
                try:
                    if isinstance(old_dino, str):
                        oid = ObjectId(old_dino)
                    else:
                        oid = old_dino
                    dino_ref = DBRef("dinosaurs", oid)
                    requests.append(
                        UpdateOne({"_id": doc["_id"]}, {"$set": {"dino": dino_ref}, "$unset": {"dino_id": ""}})
                    )
                except Exception as e:
                    print(f"Error preparing doc {doc['_id']} in {col_name}: {e}")
        if requests:
            res = await db[col_name].bulk_write(requests, ordered=False)
            print(f"Updated '{col_name}' dino links: {res.modified_count} docs.")

    # 8. Convert product_id -> product in preferential (DBRef to products)
    try:
        indexes = await db["preferential"].list_indexes().to_list()
        for index in indexes:
            if any(k in index["key"] for k in ["product", "product_id"]):
                index_name = index["name"]
                if index_name != "_id_":
                    await db["preferential"].drop_index(index_name)
                    print(f"Dropped index '{index_name}' in 'preferential'")
    except Exception as e:
        print(f"Could not drop index in preferential: {e}")

    cursor = db["preferential"].find({"product_id": {"$exists": True}})
    requests = []
    async for doc in cursor:
        old_product = doc["product_id"]
        if old_product:
            try:
                if isinstance(old_product, str):
                    oid = ObjectId(old_product)
                else:
                    oid = old_product
                product_ref = DBRef("products", oid)
                requests.append(
                    UpdateOne({"_id": doc["_id"]}, {"$set": {"product": product_ref}, "$unset": {"product_id": ""}})
                )
            except Exception as e:
                print(f"Error preparing doc {doc['_id']} in preferential: {e}")
    if requests:
        res = await db["preferential"].bulk_write(requests, ordered=False)
        print(f"Updated 'preferential' product links: {res.modified_count} docs.")

    print("All collections migrated successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
