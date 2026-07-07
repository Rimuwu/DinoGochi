import asyncio
import os
import sys
from bson import ObjectId, DBRef
from motor.motor_asyncio import AsyncIOMotorClient

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

    # List of collections with 'user' field that needs to become 'userid' (int)
    collections_user_to_userid = [
        "referals",
        "subscriptions",
        "ads",
        "dino_collection",
        "achievements",
        "lottery_members",
        "dead_users",
        "boosters",
        "onetime_rewards",
        "donations",
        "preferential",
        "tracking_members",
        "item_craft"
    ]

    for col_name in collections_user_to_userid:
        print(f"Migrating '{col_name}' (user -> userid)...")
        cursor = db[col_name].find({})
        count = 0
        async for doc in cursor:
            # Check if old field exists
            if "user" in doc:
                old_user = doc["user"]
                userid = resolve_userid(old_user, user_oid_to_userid)
                
                # Update document
                await db[col_name].update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {"userid": userid},
                        "$unset": {"user": ""}
                    }
                )
                count += 1
        print(f"Finished '{col_name}': updated {count} documents.")

    # Collection "long_activity" stores multiple activity types inheriting from Activity
    # It also has "user" field which needs to become "userid"
    print("Migrating 'long_activity' (user -> userid)...")
    cursor = db["long_activity"].find({})
    count = 0
    async for doc in cursor:
        if "user" in doc:
            old_user = doc["user"]
            userid = resolve_userid(old_user, user_oid_to_userid)
            await db["long_activity"].update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"userid": userid},
                    "$unset": {"user": ""}
                }
            )
            count += 1
    print(f"Finished 'long_activity': updated {count} documents.")

    # Kindergarten has user -> userid
    print("Migrating 'kindergarten' (user -> userid)...")
    cursor = db["kindergarten"].find({})
    count = 0
    async for doc in cursor:
        if "user" in doc:
            old_user = doc["user"]
            userid = resolve_userid(old_user, user_oid_to_userid)
            await db["kindergarten"].update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"userid": userid},
                    "$unset": {"user": ""}
                }
            )
            count += 1
    print(f"Finished 'kindergarten': updated {count} documents.")

    # GroupUsers has user -> userid
    print("Migrating 'group_users' (user -> userid)...")
    cursor = db["group_users"].find({})
    count = 0
    async for doc in cursor:
        if "user" in doc:
            old_user = doc["user"]
            userid = resolve_userid(old_user, user_oid_to_userid)
            await db["group_users"].update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"userid": userid},
                    "$unset": {"user": ""}
                }
            )
            count += 1
    print(f"Finished 'group_users': updated {count} documents.")

    # List of collections with 'owner' field that needs to become 'owner_id' (int)
    collections_owner_to_ownerid = [
        "incubation",
        "dead_dinos",
        "dino_owners",
        "quests",
        "daily_award",
        "inside_shop",
        "sellers",
        "puhs",
        "farm"
    ]

    for col_name in collections_owner_to_ownerid:
        print(f"Migrating '{col_name}' (owner -> owner_id)...")
        cursor = db[col_name].find({})
        count = 0
        async for doc in cursor:
            if "owner" in doc:
                old_owner = doc["owner"]
                owner_id = resolve_userid(old_owner, user_oid_to_userid)
                await db[col_name].update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {"owner_id": owner_id},
                        "$unset": {"owner": ""}
                    }
                )
                count += 1
        print(f"Finished '{col_name}': updated {count} documents.")

    # Special logic for Friends collection:
    # user -> userid, friend -> friendid
    print("Migrating 'friends' collection...")
    cursor = db["friends"].find({})
    count = 0
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
            update_op = {"$set": updates}
            if unsets:
                update_op["$unset"] = unsets
            await db["friends"].update_one({"_id": doc["_id"]}, update_op)
            count += 1
    print(f"Finished 'friends' collection: updated {count} documents.")

    # Special logic for Products collection:
    # owner -> owner_id
    print("Migrating 'products' collection...")
    cursor = db["products"].find({})
    count = 0
    async for doc in cursor:
        updates = {}
        unsets = {}
        if "owner" in doc:
            owner_id = resolve_userid(doc["owner"], user_oid_to_userid)
            updates["owner_id"] = owner_id
            unsets["owner"] = ""
        
        # Cleanup/remove seller_id if present
        if "seller_id" in doc:
            unsets["seller_id"] = ""

        if updates or unsets:
            update_op = {}
            if updates:
                update_op["$set"] = updates
            if unsets:
                update_op["$unset"] = unsets
            await db["products"].update_one({"_id": doc["_id"]}, update_op)
            count += 1
    print(f"Finished 'products' collection: updated {count} documents.")

    print("All collections migrated successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
