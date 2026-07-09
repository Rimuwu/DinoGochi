import asyncio
from bson import ObjectId, DBRef
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

mongo_url = "mongodb://bot:mk34lkjnKJhkb983480kjr5KJLKlk34@95.85.245.1:27017/?directConnection=true"

async def migrate_prod():
    print(f"Connecting to Prod MongoDB: {mongo_url}")
    client = AsyncIOMotorClient(mongo_url)
    db = client["dinogochi"]

    # 1. Rename user_id -> userid (integer) using fast $rename
    # Collections: boosters, onetime_rewards, dino_collection, group_users
    user_id_collections = ["boosters", "onetime_rewards", "dino_collection", "group_users"]
    for col_name in user_id_collections:
        print(f"Migrating '{col_name}' (user_id -> userid via $rename)...")
        result = await db[col_name].update_many(
            {"user_id": {"$exists": True}},
            {"$rename": {"user_id": "userid"}}
        )
        print(f"Finished '{col_name}': renamed {result.modified_count} documents.")

    # 2. Rename owner_id -> owner in items using fast $rename
    print("Migrating 'items' collection (owner_id -> owner via $rename)...")
    result = await db["items"].update_many(
        {"owner_id": {"$exists": True}},
        {"$rename": {"owner_id": "owner"}}
    )
    print(f"Finished 'items' collection: renamed {result.modified_count} documents.")

    # 3. Convert dino_id -> dino (DBRef to dinosaurs) using fast bulk_write
    # Collections: dino_owners, dino_mood, state, kd_activity, long_activity, item_craft
    dino_id_collections = ["dino_owners", "dino_mood", "state", "kd_activity", "long_activity", "item_craft"]
    for col_name in dino_id_collections:
        # Drop old indexes containing dino_id to prevent E11000 duplicate key error when unsetting
        try:
            indexes = await db[col_name].list_indexes().to_list()
            for index in indexes:
                if "dino_id" in index["key"]:
                    index_name = index["name"]
                    if index_name != "_id_":
                        await db[col_name].drop_index(index_name)
                        print(f"Dropped index '{index_name}' in '{col_name}'")
        except Exception as e:
            print(f"Could not drop index in {col_name}: {e}")

        print(f"Migrating '{col_name}' (dino_id -> dino DBRef)...")
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
                        UpdateOne(
                            {"_id": doc["_id"]},
                            {
                                "$set": {"dino": dino_ref},
                                "$unset": {"dino_id": ""}
                            }
                        )
                    )
                except Exception as e:
                    print(f"Error preparing doc {doc['_id']} in {col_name}: {e}")
        
        if requests:
            result = await db[col_name].bulk_write(requests, ordered=False)
            print(f"Finished '{col_name}': bulk updated {result.modified_count} documents.")
        else:
            print(f"Finished '{col_name}': no documents to update.")

    # 4. Convert product_id -> product in preferential (DBRef to products) using bulk_write
    try:
        indexes = await db["preferential"].list_indexes().to_list()
        for index in indexes:
            if "product_id" in index["key"]:
                index_name = index["name"]
                if index_name != "_id_":
                    await db["preferential"].drop_index(index_name)
                    print(f"Dropped index '{index_name}' in 'preferential'")
    except Exception as e:
        print(f"Could not drop index in preferential: {e}")

    print("Migrating 'preferential' collection (product_id -> product DBRef)...")
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
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {
                            "$set": {"product": product_ref},
                            "$unset": {"product_id": ""}
                        }
                    )
                )
            except Exception as e:
                print(f"Error preparing doc {doc['_id']} in preferential: {e}")
    
    if requests:
        result = await db["preferential"].bulk_write(requests, ordered=False)
        print(f"Finished 'preferential' collection: bulk updated {result.modified_count} documents.")
    else:
        print("Finished 'preferential' collection: no documents to update.")

    print("All production collections migrated successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_prod())
