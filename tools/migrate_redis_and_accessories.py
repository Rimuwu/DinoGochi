import sys
import os
import json
from pymongo import MongoClient
import redis

# Add root directory to sys.path to import conf
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import conf

def migrate():
    print("Connecting to MongoDB...")
    mongo_client = MongoClient(conf.mongo_url)
    db = mongo_client["dinogochi"]
    print(f"MongoDB connected: {db.name}")

    print("Connecting to Redis...")
    # Parse redis url
    try:
        redis_client = redis.Redis.from_url(conf.redis_url, decode_responses=True)
        redis_client.ping()
        print("Redis connected successfully.")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return

    # 1. Migrate management cache to Redis
    print("\n--- Phase 1: Migrating Management Cache ---")
    management_col = db["management"]
    
    mapping = {
        "rayting_coins": ("rayting:coins", ["data", "ids"]),
        "rayting_lvl": ("rayting:lvl", ["data", "ids"]),
        "rayting_super": ("rayting:super", ["data", "ids"]),
        "rayting_dontaion_all": ("rayting:dontaion_all", ["data", "ids"]),
        "rayting_dontaion_30d": ("rayting:dontaion_30d", ["data", "ids"]),
        "rayt_update": ("rayting:update_time", ["time"]),
        "dino_statistic": ("dino:statistic", ["data", "all_count"])
    }

    for mongo_id, (redis_key, fields) in mapping.items():
        doc = management_col.find_one({"_id": mongo_id})
        if doc:
            data_to_store = {f: doc.get(f) for f in fields}
            redis_client.set(redis_key, json.dumps(data_to_store, default=str))
            print(f"[✓] Migrated MongoDB document '{mongo_id}' to Redis key '{redis_key}'")
        else:
            print(f"[-] MongoDB document '{mongo_id}' not found, skipping cache migration for it.")

    # 2. Migrate dino accessories
    print("\n--- Phase 2: Migrating Dinosaur Accessories ---")
    dinosaurs_col = db["dinosaurs"]
    items_col = db["items"]
    
    dinos_with_accessories = list(dinosaurs_col.find({"activ_items": {"$exists": True, "$not": {"$size": 0}}}))
    print(f"Found {len(dinos_with_accessories)} dinosaur(s) with active accessories.")

    for dino in dinos_with_accessories:
        dino_id = str(dino["_id"])
        dino_name = dino.get("name", "Unknown")
        activ_items = dino.get("activ_items", [])
        
        print(f"Migrating accessories for dino '{dino_name}' ({dino_id})...")
        
        migrated_any = False
        for item_dict in activ_items:
            if not item_dict or "item_id" not in item_dict:
                continue
                
            item_id = item_dict["item_id"]
            
            # Check if this accessory is already created for this dino in items collection
            existing = items_col.find_one({
                "owner_id": dino_id,
                "items_data.item_id": item_id
            })
            
            if not existing:
                new_item_doc = {
                    "owner_id": dino_id,
                    "items_data": item_dict,
                    "count": 1
                }
                items_col.insert_one(new_item_doc)
                print(f"  [✓] Accessory '{item_id}' added as a document to 'items'")
                migrated_any = True
            else:
                print(f"  [-] Accessory '{item_id}' already exists in 'items', skipping insert")
        
        # Clear activ_items array on dino document
        dinosaurs_col.update_one(
            {"_id": dino["_id"]},
            {"$set": {"activ_items": []}}
        )
        print(f"  [✓] Cleared 'activ_items' for dino '{dino_name}' in MongoDB")

    print("\n[✓] Migration successfully completed!")

if __name__ == '__main__':
    migrate()
