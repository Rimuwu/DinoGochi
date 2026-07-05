import sys
import os
import json
import asyncio
from pymongo import MongoClient
import redis
from pymongo.errors import DuplicateKeyError, BulkWriteError
from concurrent.futures import ThreadPoolExecutor
import time

# Reconfigure stdout/stderr to support utf-8 characters on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Добавляем корневую директорию проекта в sys.path для импорта config и dbmanager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.config import conf

# Заменяем docker хосты на localhost для запуска скрипта локально
if sys.platform == 'win32':
    conf.mongo_url = conf.mongo_url.replace("mongo:27017", "localhost:27017")
    conf.redis_url = conf.redis_url.replace("redis:6379", "localhost:6379")

# Переопределяем клиенты в dbmanager на localhost, чтобы Beanie использовала правильный хост
import bot.dbmanager
import motor.motor_asyncio
bot.dbmanager.real_mongo_client = motor.motor_asyncio.AsyncIOMotorClient(conf.mongo_url)
bot.dbmanager.mongo_client = bot.dbmanager.UnifiedMongoClientWrapper(bot.dbmanager.real_mongo_client)

# Загружаем предметы для определения класса в миграции
try:
    from bot.modules.items.collect_items import get_all_items
    ITEMS_DATA = get_all_items()
except Exception as e:
    print(f"Предупреждение: не удалось импортировать предметы: {e}")
    ITEMS_DATA = {}


# Глобальный список для сбора пропущенных документов
skipped_documents_report = []

# Попытка импортировать tqdm для прогресс-бара, иначе используем простой fallback
try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, total=None, desc=""):
            self.total = total
            self.desc = desc
            self.n = 0
            print(f"{self.desc}...")

        def update(self, n=1):
            self.n += n
            if self.total:
                pct = int((self.n / self.total) * 100)
                sys.stdout.write(f"\r{self.desc}: {pct}% ({self.n}/{self.total})")
                sys.stdout.flush()

        def close(self):
            print()

def insert_batch_safely(target_col, batch, source_db_name, col_name):
    global skipped_documents_report
    try:
        target_col.insert_many(batch, ordered=False)
        return len(batch)
    except (BulkWriteError, DuplicateKeyError, Exception) as e:
        inserted = 0
        for doc in batch:
            try:
                target_col.insert_one(doc)
                inserted += 1
            except Exception as doc_exc:
                err_msg = str(doc_exc)
                serializable_doc = json.loads(json.dumps(doc, default=str))
                skipped_documents_report.append({
                    "database": source_db_name,
                    "collection": col_name,
                    "document": serializable_doc,
                    "error": err_msg
                })
        return inserted

def migrate_collection(client_url, source_db_name, col_name, target_col_name):
    client = MongoClient(client_url)
    source_db = client[source_db_name]
    target_db = client["dinogochi"]
    
    source_col = source_db[col_name]
    target_col = target_db[target_col_name]
    
    doc_count = source_col.count_documents({})
    if doc_count == 0:
        return f"[-] {source_db_name}.{col_name} -> пуста, пропуск."

    # Извлекаем уже существующие _id в целевой коллекции
    existing_ids = set(doc["_id"] for doc in target_col.find({}, {"_id": 1}))
    
    pbar = tqdm(total=doc_count, desc=f"Копирование {source_db_name}.{col_name}")
    
    batch_size = 5000
    cursor = source_col.find({})
    batch = []
    copied = 0
    
    for doc in cursor:
        pbar.update(1)
        
        # Особая фильтрация для long_activity
        if col_name == "long_activity":
            act_type = doc.get("activity_type")
            if act_type not in ["inactive", "sleep"]:
                continue
            if act_type == "sleep":
                doc["_class_id"] = "SleepActivity"
                sleep_start = doc.pop("sleep_start", None)
                sleep_end = doc.pop("sleep_end", None)
                if sleep_start is not None:
                    doc["start_time"] = sleep_start
                if sleep_end is not None:
                    doc["end_time"] = sleep_end
                else:
                    doc["end_time"] = (sleep_start if sleep_start is not None else int(time.time())) + 86400 * 365
            elif act_type == "inactive":
                doc["_class_id"] = "Activity"

        # Особая фильтрация для items и добавление _class_id
        if col_name == "items":
            item_id = doc.get("items_data", {}).get("item_id")
            item_type = None
            if item_id and item_id in ITEMS_DATA:
                item_type = ITEMS_DATA[item_id].get("type")
            
            if item_type == "eat":
                doc["_class_id"] = "Item.EatItem"
            elif item_type in ["game", "journey", "collecting", "sleep", "weapon", "armor", "backpack"]:
                doc["_class_id"] = "Item.AccessoryItem"
            elif item_type == "recipe":
                doc["_class_id"] = "Item.RecipeItem"
            elif item_type == "case":
                doc["_class_id"] = "Item.CaseItem"
            elif item_type == "egg":
                doc["_class_id"] = "Item.EggItem"
            elif item_type == "special":
                doc["_class_id"] = "Item.SpecialItem"
            else:
                doc["_class_id"] = "Item"

        # Добавляем в батч только новые документы по ID
        if doc["_id"] not in existing_ids:
            batch.append(doc)
            
        if len(batch) >= batch_size:
            copied += insert_batch_safely(target_col, batch, source_db_name, col_name)
            batch = []
            
    if batch:
        copied += insert_batch_safely(target_col, batch, source_db_name, col_name)
        
    pbar.close()
    return f"[✓] Успешно перенесено {copied} новых документов в {target_col_name}."

def migrate_sync():
    print("Подключение к MongoDB...")
    client = MongoClient(conf.mongo_url)
    
    print("Очистка целевой базы данных dinogochi перед миграцией...")
    client.drop_database("dinogochi")
    print("[✓] База данных dinogochi успешно очищена.")
    
    target_db = client["dinogochi"]
    print(f"Целевая база данных: {target_db.name}")

    # Исходная структура баз данных и коллекций
    collections_structure = {
        "user": ["users", "lang", "referals", "friends", "subscriptions", "ads", "dino_collection", "achievements"],
        "dinosaur": ["dinosaurs", "dead_dinos", "incubation", "dino_owners", "dino_mood", "state"],
        "dino_activity": ["long_activity", "kindergarten"],
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

    # Маппинг переименования
    rename_mapping = {
        ("group", "users"): "group_users",
        ("lottery", "members"): "lottery_members",
        ("tracking", "members"): "tracking_members",
        ("dungeon", "lobby"): "lobby"
    }

    # Подготовка задач для пула потоков
    tasks = []
    for source_db_name, cols in collections_structure.items():
        source_db = client[source_db_name]
        existing_cols = source_db.list_collection_names()
        
        for col_name in cols:
            if col_name not in existing_cols:
                continue
            target_col_name = rename_mapping.get((source_db_name, col_name), col_name)
            tasks.append((source_db_name, col_name, target_col_name))

    print(f"\nЗапуск параллельного копирования коллекций ({len(tasks)} задач)...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(migrate_collection, conf.mongo_url, src_db, col, tgt_col)
            for src_db, col, tgt_col in tasks
        ]
        for fut in futures:
            try:
                res = fut.result()
                print(res)
            except Exception as e:
                print(f"[!] Ошибка при параллельном копировании: {e}")

    # Миграция из dinogochi.deleted_dungeon_lobby в dinogochi.lobby (при наличии)
    print("\nМиграция dungeon lobby из deleted_dungeon_lobby...")
    if "deleted_dungeon_lobby" in target_db.list_collection_names():
        deleted_lobby_col = target_db["deleted_dungeon_lobby"]
        target_lobby_col = target_db["lobby"]
        deleted_count = deleted_lobby_col.count_documents({})
        if deleted_count > 0:
            existing_lobby_ids = set(doc["_id"] for doc in target_lobby_col.find({}, {"_id": 1}))
            batch = []
            for doc in deleted_lobby_col.find({}):
                if doc["_id"] not in existing_lobby_ids:
                    batch.append(doc)
            if batch:
                insert_batch_safely(target_lobby_col, batch, "dinogochi", "deleted_dungeon_lobby")
            print(f"[✓] Успешно обработана миграция deleted_dungeon_lobby.")
            deleted_lobby_col.drop()

    # 2. Языковая нормализация
    print("\nНормализация языковых настроек (lang)...")
    lang_col = target_db["lang"]
    allowed_langs = ["ru", "en", "es", "id"]
    non_standard_count = lang_col.count_documents({"lang": {"$nin": allowed_langs}})
    if non_standard_count > 0:
        print(f"[+] Найдено {non_standard_count} записей с нестандартными языками. Сброс на 'en'...")
        result = lang_col.update_many(
            {"lang": {"$nin": allowed_langs}},
            {"$set": {"lang": "en"}}
        )
        print(f"[✓] Обновлено {result.modified_count} записей.")
    else:
        print("[-] Все языковые записи соответствуют ru/en/es/id.")

    # 3. Миграция активных аксессуаров динозавров в коллекцию items
    print("\nМиграция активных аксессуаров динозавров в коллекцию items...")
    if "dinosaurs" in target_db.list_collection_names() and "items" in target_db.list_collection_names():
        dinosaurs_col = target_db["dinosaurs"]
        items_col = target_db["items"]
        
        dinos_with_accessories = list(dinosaurs_col.find({"activ_items": {"$exists": True, "$not": {"$size": 0}}}))
        if dinos_with_accessories:
            print(f"[+] Найдено {len(dinos_with_accessories)} динозавров с активными аксессуарами.")
            existing_items = set(
                (doc["owner_id"], doc["items_data"]["item_id"])
                for doc in items_col.find({"items_data.item_id": {"$exists": True}}, {"owner_id": 1, "items_data.item_id": 1})
            )
            
            new_items_batch = []
            dino_updates = []
            
            for dino in dinos_with_accessories:
                dino_id = str(dino["_id"])
                activ_items = dino.get("activ_items", [])
                
                for item_dict in activ_items:
                    if not item_dict or "item_id" not in item_dict:
                        continue
                    item_id = item_dict["item_id"]
                    
                    if (dino_id, item_id) not in existing_items:
                        item_type = None
                        if item_id in ITEMS_DATA:
                            item_type = ITEMS_DATA[item_id].get("type")
                        
                        if item_type == "eat":
                            class_id = "Item.EatItem"
                        elif item_type in ["game", "journey", "collecting", "sleep", "weapon", "armor", "backpack"]:
                            class_id = "Item.AccessoryItem"
                        elif item_type == "recipe":
                            class_id = "Item.RecipeItem"
                        elif item_type == "case":
                            class_id = "Item.CaseItem"
                        elif item_type == "egg":
                            class_id = "Item.EggItem"
                        elif item_type == "special":
                            class_id = "Item.SpecialItem"
                        else:
                            class_id = "Item"

                        new_items_batch.append({
                            "owner_id": dino_id,
                            "items_data": item_dict,
                            "count": 1,
                            "_class_id": class_id
                        })
                        existing_items.add((dino_id, item_id))
                
                dino_updates.append(dino["_id"])
            
            if new_items_batch:
                insert_batch_safely(items_col, new_items_batch, "dinogochi", "dinosaurs_accessories")
                print(f"[✓] Перенесено аксессуаров в коллекцию 'items'.")
            
            if dino_updates:
                dinosaurs_col.update_many(
                    {"_id": {"$in": dino_updates}},
                    {"$set": {"activ_items": []}}
                )
                print(f"[✓] Очищен массив activ_items у {len(dino_updates)} динозавров.")
        else:
            print("[-] Динозавров с активными аксессуарами не найдено.")

    # 4. Перенос кэша в Redis
    print("\nПодключение к Redis...")
    try:
        redis_client = redis.Redis.from_url(conf.redis_url, decode_responses=True)
        redis_client.ping()
        print("[✓] Успешное подключение к Redis.")
        
        print("\nМиграция кэша управления в Redis...")
        management_col = target_db["management"]
        
        redis_mapping = {
            "rayting_coins": ("rayting:coins", ["data", "ids"]),
            "rayting_lvl": ("rayting:lvl", ["data", "ids"]),
            "rayting_super": ("rayting:super", ["data", "ids"]),
            "rayting_dontaion_all": ("rayting:dontaion_all", ["data", "ids"]),
            "rayting_dontaion_30d": ("rayting:dontaion_30d", ["data", "ids"]),
            "rayt_update": ("rayting:update_time", ["time"]),
            "dino_statistic": ("dino:statistic", ["data", "all_count"])
        }

        for mongo_id, (redis_key, fields) in redis_mapping.items():
            doc = management_col.find_one({"_id": mongo_id})
            if doc:
                data_to_store = {f: doc.get(f) for f in fields}
                redis_client.set(redis_key, json.dumps(data_to_store, default=str))
                print(f"[✓] Перенесен документ '{mongo_id}' -> Redis ключ '{redis_key}'")
            else:
                print(f"[-] Документ '{mongo_id}' не найден в MongoDB, пропуск.")
    except Exception as e:
        print(f"[!] Ошибка подключения/работы с Redis: {e}")

    # 5. Проверка и удаление базы dungeon
    print("\nПроверка и удаление базы данных dungeon...")
    try:
        dungeon_db = client["dungeon"]
        dungeon_cols = dungeon_db.list_collection_names()
        if dungeon_cols:
            print(f"[!] База dungeon содержит коллекции: {dungeon_cols}. Удаляем...")
            client.drop_database("dungeon")
            print("[✓] База dungeon успешно удалена.")
        else:
            print("[-] База dungeon отсутствует или уже пуста.")
    except Exception as e:
        print(f"[-] Ошибка при удалении dungeon: {e}")

    # 6. Запись отчета по пропущенным документам в JSON
    report_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "skipped_documents.json"))
    if skipped_documents_report:
        print(f"\n[!] Зафиксировано {len(skipped_documents_report)} пропущенных документов из-за конфликтов индексов.")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(skipped_documents_report, f, indent=4, ensure_ascii=False)
        print(f"[✓] Отчет успешно сохранен в файл: skipped_documents.json")
    else:
        # Очистим файл, если ошибок нет
        if os.path.exists(report_file):
            os.remove(report_file)
        print("\n[✓] Конфликтов индексов/дубликатов не обнаружено.")

async def apply_beanie_indexes():
    print("\nИнициализация Beanie ODM для автоматического применения индексов...")
    from bot.dbmanager import init_beanie_odm, real_mongo_client
    await init_beanie_odm(real_mongo_client)
    print("[✓] Beanie ODM успешно инициализирован.")
    
    print("\nПроверка созданных индексов:")
    target_db = real_mongo_client["dinogochi"]
    collections = await target_db.list_collection_names()
    for col_name in sorted(collections):
        col = target_db[col_name]
        indexes = await col.index_information()
        print(f"Коллекция: {col_name}")
        for idx_name, idx_info in indexes.items():
            print(f"  - Индекс: {idx_name} -> {idx_info.get('key')}")

if __name__ == '__main__':
    migrate_sync()
    asyncio.run(apply_beanie_indexes())
    print("\n[✓] Миграция успешно завершена!")
