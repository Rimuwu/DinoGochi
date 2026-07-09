import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import DBRef, ObjectId
import sys
import os

# Add root folder to sys.path so we can import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import conf

async def migrate():
    mongo_url = conf.mongo_url
    if "mongo:27017" in mongo_url:
        mongo_url = mongo_url.replace("mongo:27017", "localhost:27017")
    print(f"Connecting to MongoDB: {mongo_url}")
    client = AsyncIOMotorClient(mongo_url)
    db = client["dinogochi"]

    # 1. Drop unused collections
    print("Dropping unused collections...")
    for col in ["lobby", "states"]:
        await db[col].drop()
        print(f"Dropped collection: {col}")

    # 2. Cleanup Group Collection
    print("Migrating 'groups' collection...")
    # Drop old indexes on group
    try:
        await db["groups"].drop_indexes()
        print("Dropped all indexes on 'groups' to avoid conflicts")
    except Exception as e:
        print(f"No indexes dropped on groups: {e}")

    # Remove title, username, settings
    groups_cursor = db["groups"].find({})
    async for group in groups_cursor:
        gid = group["_id"]
        # Keep only required fields
        group_id = group.get("group_id")
        topic_link = group.get("topic_link", 0)
        topic_incorrect_message = group.get("topic_incorrect_message", True)
        delete_message = group.get("delete_message", 0)

        cleaned_group = {
            "group_id": group_id,
            "topic_link": topic_link,
            "topic_incorrect_message": topic_incorrect_message,
            "delete_message": delete_message
        }
        await db["groups"].replace_one({"_id": gid}, cleaned_group)
    print("Finished groups migration.")

    # Cache users mapping (userid -> _id)
    print("Caching users mapping...")
    user_map = {}
    user_obj_map = {} # _id -> _id
    async for user in db["users"].find({}):
        user_map[user["userid"]] = user["_id"]
        user_obj_map[user["_id"]] = user["_id"]

    async def get_user_ref(raw_val):
        """Converts raw_val (userid or _id or DBRef) to DBRef("users", user_oid)"""
        if raw_val is None:
            return None
        
        # If it is already a DBRef
        if isinstance(raw_val, DBRef):
            return raw_val
        
        # If it is a dict representing a DBRef or Beanie Link
        if isinstance(raw_val, dict) and "$id" in raw_val:
            oid = raw_val["$id"]
            if isinstance(oid, str):
                oid = ObjectId(oid)
            return DBRef("users", oid)

        # If it is an integer Telegram ID
        if isinstance(raw_val, int):
            if raw_val in user_map:
                return DBRef("users", user_map[raw_val])
            else:
                # Create a placeholder user document to satisfy reference
                res = await db["users"].insert_one({"userid": raw_val, "coins": 100, "lvl": 0, "xp": 0, "name": f"Migrated User {raw_val}"})
                user_map[raw_val] = res.inserted_id
                user_obj_map[res.inserted_id] = res.inserted_id
                return DBRef("users", res.inserted_id)

        # If it is a string / ObjectId representation
        if isinstance(raw_val, str):
            try:
                oid = ObjectId(raw_val)
                if oid in user_obj_map:
                    return DBRef("users", oid)
            except Exception:
                pass
            # Try parsing as integer Telegram ID
            try:
                val_int = int(raw_val)
                if val_int in user_map:
                    return DBRef("users", user_map[val_int])
            except Exception:
                pass

        if isinstance(raw_val, ObjectId):
            if raw_val in user_obj_map:
                return DBRef("users", raw_val)

        return None

    # 3. Cleanup GroupUser Collection
    print("Migrating 'group_users' collection...")
    try:
        await db["group_users"].drop_indexes()
        print("Dropped indexes on 'group_users'")
    except Exception as e:
        print(f"No indexes dropped on group_users: {e}")

    async for gu in db["group_users"].find({}):
        gid = gu["_id"]
        
        # Determine user link from old user_id or user
        old_user_ref = gu.get("user") or gu.get("user_id")
        user_ref = await get_user_ref(old_user_ref)

        cleaned_gu = {
            "user": user_ref,
            "group_id": gu.get("group_id"),
            "games_count": gu.get("games_count", 0)
        }
        await db["group_users"].replace_one({"_id": gid}, cleaned_gu)
    print("Finished group_users migration.")

    # 4. Migrate Subscriptions
    print("Migrating 'subscriptions' collection...")
    try:
        await db["subscriptions"].drop_indexes()
        print("Dropped indexes on 'subscriptions'")
    except Exception as e:
        print(f"No indexes dropped on subscriptions: {e}")

    async for sub in db["subscriptions"].find({}):
        gid = sub["_id"]
        
        old_user_ref = sub.get("user") or sub.get("userid")
        user_ref = await get_user_ref(old_user_ref)

        cleaned_sub = {
            "user": user_ref,
            "sub_start": sub.get("sub_start", 0),
            "sub_end": sub.get("sub_end", 0),
            "end_notif": sub.get("end_notif", False)
        }
        await db["subscriptions"].replace_one({"_id": gid}, cleaned_sub)
    print("Finished subscriptions migration.")

    # 5. Migrate DinoCollection
    print("Migrating 'dino_collection' collection...")
    try:
        await db["dino_collection"].drop_indexes()
        print("Dropped indexes on 'dino_collection'")
    except Exception as e:
        print(f"No indexes dropped on dino_collection: {e}")

    async for dc in db["dino_collection"].find({}):
        gid = dc["_id"]
        
        old_user_ref = dc.get("user") or dc.get("user_id")
        user_ref = await get_user_ref(old_user_ref)

        # Map fields to match new model
        # Old doc had: user_id, data_id, familie, date
        cleaned_dc = {
            "user": user_ref,
            "data_id": int(dc.get("data_id") or dc.get("dino_id") or 0),
            "familie": dc.get("familie", ""),
            "date": int(dc.get("date") or dc.get("added_time") or 0)
        }
        await db["dino_collection"].replace_one({"_id": gid}, cleaned_dc)
    print("Finished dino_collection migration.")

    print("DB Migration successfully completed!")

if __name__ == "__main__":
    asyncio.run(migrate())
