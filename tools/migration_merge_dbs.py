import sys
import os
from pymongo import MongoClient

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.config import conf

def migrate():
    print("Подключение к MongoDB...")
    client = MongoClient(conf.mongo_url)
    
    # Целевая база данных
    target_db = client["dinogochi"]
    print(f"Целевая база данных: {target_db.name}")

    # Исходная структура баз данных и коллекций
    collections_structure = {
        "user": ["users", "lang", "referals", "friends", "subscriptions", "ads", "dino_collection", "achievements"],
        "dinosaur": ["dinosaurs", "dead_dinos", "incubation", "dino_owners", "dino_mood", "state"],
        "dino_activity": ["kd_activity", "long_activity", "kindergarten"],
        "market": ["products", "sellers", "preferential", "puhs"],
        "items": ["items", "farm", "item_craft"],
        "tavern": ["quests", "tavern", "daily_award", "inside_shop"],
        "other": ["management", "statistic", "events", "promo", "dead_users", "companies", "message_log", "states", "boosters", "onetime_rewards"],
        "minigame": ["online"],
        "lottery": ["lottery", "members"],
        "tracking": ["links", "members"],
        "group": ["groups", "messages", "users"],
        "dungeon": ["lobby"]
    }

    # Маппинг переименования для избежания конфликтов имен в единой БД
    rename_mapping = {
        ("group", "users"): "group_users",
        ("lottery", "members"): "lottery_members",
        ("tracking", "members"): "tracking_members"
    }

    for source_db_name, cols in collections_structure.items():
        source_db = client[source_db_name]
        existing_cols = source_db.list_collection_names()
        
        for col_name in cols:
            if col_name not in existing_cols:
                # Коллекция не существует в исходной БД, пропускаем
                continue

            # Определяем имя коллекции в целевой БД
            target_col_name = rename_mapping.get((source_db_name, col_name), col_name)
            
            source_col = source_db[col_name]
            target_col = target_db[target_col_name]

            doc_count = source_col.count_documents({})
            if doc_count == 0:
                print(f"[-] Пропуск пустой коллекции: {source_db_name}.{col_name}")
                continue

            print(f"[+] Копирование {doc_count} документов из {source_db_name}.{col_name} -> {target_db.name}.{target_col_name}...")
            
            # Постраничное копирование для экономии памяти
            batch_size = 1000
            copied = 0
            cursor = source_col.find({})
            batch = []
            
            for doc in cursor:
                batch.append(doc)
                if len(batch) >= batch_size:
                    # Вставляем документы, игнорируя дубликаты
                    for item in batch:
                        if not target_col.find_one({"_id": item["_id"]}):
                            target_col.insert_one(item)
                            copied += 1
                    batch = []
            
            if batch:
                for item in batch:
                    if not target_col.find_one({"_id": item["_id"]}):
                        target_col.insert_one(item)
                        copied += 1

            print(f"[✓] Успешно перенесено {copied} новых документов.")

    # Миграция активных аксессуаров динозавров в коллекцию items
    print("\nМиграция активных аксессуаров динозавров в коллекцию items...")
    dinogochi_db = client["dinogochi"]
    if "dinosaurs" in dinogochi_db.list_collection_names() and "items" in dinogochi_db.list_collection_names():
        dinosaurs_col = dinogochi_db["dinosaurs"]
        items_col = dinogochi_db["items"]
        
        dinos_with_accessories = list(dinosaurs_col.find({"activ_items": {"$exists": True, "$not": {"$size": 0}}}))
        if dinos_with_accessories:
            print(f"[+] Найдено {len(dinos_with_accessories)} динозавров с активными аксессуарами.")
            for dino in dinos_with_accessories:
                dino_id = str(dino["_id"])
                dino_name = dino.get("name", "Unknown")
                activ_items = dino.get("activ_items", [])
                
                print(f"  [-] Перенос аксессуаров для динозавра '{dino_name}' ({dino_id})...")
                for item_dict in activ_items:
                    if not item_dict or "item_id" not in item_dict:
                        continue
                        
                    item_id = item_dict["item_id"]
                    
                    # Проверяем, существует ли уже этот аксессуар в items для данного динозавра
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
                        print(f"    [✓] Аксессуар '{item_id}' добавлен в коллекцию 'items'")
                    else:
                        print(f"    [-] Аксессуар '{item_id}' уже существует в 'items', пропуск")
                        
                # Очищаем массив activ_items на документе динозавра
                dinosaurs_col.update_one(
                    {"_id": dino["_id"]},
                    {"$set": {"activ_items": []}}
                )
                print(f"  [✓] Очищено 'activ_items' для динозавра '{dino_name}'")

    # Миграция из dinogochi.deleted_dungeon_lobby в dinogochi.lobby
    print("\nМиграция dungeon lobby из deleted_dungeon_lobby...")
    dinogochi_db = client["dinogochi"]
    if "deleted_dungeon_lobby" in dinogochi_db.list_collection_names():
        deleted_lobby_col = dinogochi_db["deleted_dungeon_lobby"]
        target_lobby_col = dinogochi_db["lobby"]
        deleted_count = deleted_lobby_col.count_documents({})
        if deleted_count > 0:
            print(f"[+] Перенос {deleted_count} документов из dinogochi.deleted_dungeon_lobby -> dinogochi.lobby...")
            copied = 0
            for doc in deleted_lobby_col.find({}):
                if not target_lobby_col.find_one({"_id": doc["_id"]}):
                    target_lobby_col.insert_one(doc)
                    copied += 1
            print(f"[✓] Успешно перенесено {copied} документов.")

    # Удаление базы dungeon по запросу пользователя
    print("\nПроверка и удаление базы данных dungeon...")
    dungeon_db = client["dungeon"]
    try:
        dungeon_cols = dungeon_db.list_collection_names()
        if dungeon_cols:
            print(f"[!] База dungeon содержит коллекции: {dungeon_cols}. Удаляем...")
            client.drop_database("dungeon")
            print("[✓] База dungeon успешно удалена.")
        else:
            print("[-] База dungeon отсутствует или уже пуста.")
    except Exception as e:
        print(f"[-] Ошибка при удалении dungeon: {e}")

    print("\n[✓] Миграция успешно завершена!")
    print("Старые базы данных можно удалить вручную после проверки работоспособности новой схемы:")
    print("Используйте client.drop_database('user'), client.drop_database('dinosaur'), и т.д.")

if __name__ == '__main__':
    migrate()
