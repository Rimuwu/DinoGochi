import asyncio
import os
import sys

# Add project root to sys.path so we can import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.dbmanager import mongo_client, check_db

async def main():
    print("Initializing database connection...")
    await check_db(mongo_client)
    
    db = mongo_client.dinogochi
    print("Database connected. Starting migration...")
    
    # 1. For documents that have 'sended' but not 'userid', copy 'sended' value to 'userid'
    print("Copying 'sended' to 'userid' where 'userid' is missing...")
    res_copy = await db.long_activity.update_many(
        {
            "_class_id": "Activity.JourneyActivity", 
            "userid": {"$exists": False}, 
            "sended": {"$exists": True}
        },
        [{"$set": {"userid": "$sended"}}],
        comment="migrate_journey_sended_to_userid_copy"
    )
    print(f"Copied 'sended' to 'userid' for {res_copy.modified_count} documents.")
    
    # 2. Remove 'sended' field from all JourneyActivity documents
    print("Removing 'sended' field from JourneyActivity documents...")
    res_unset = await db.long_activity.update_many(
        {
            "_class_id": "Activity.JourneyActivity", 
            "sended": {"$exists": True}
        },
        {"$unset": {"sended": ""}},
        comment="migrate_journey_sended_to_userid_unset"
    )
    print(f"Removed 'sended' field from {res_unset.modified_count} documents.")
    
    print("Migration finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
