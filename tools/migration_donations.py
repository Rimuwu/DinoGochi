import sys
import os
import json
from pymongo import MongoClient

# Reconfigure stdout/stderr to support utf-8 characters on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.config import conf

# Replace docker hosts with localhost for local script running
mongo_url = conf.mongo_url.replace("mongo:27017", "localhost:27017")

def migrate_donations():
    donations_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot', 'data', 'donations.json'))
    
    if not os.path.exists(donations_json_path):
        print(f"[-] Файл {donations_json_path} не найден. Миграция не требуется.")
        return

    try:
        with open(donations_json_path, encoding='utf-8') as f:
            donations_data = json.load(f)
    except Exception as e:
        print(f"[x] Ошибка чтения {donations_json_path}: {e}")
        return

    if not donations_data:
        print("[-] Файл donations.json пуст. Миграция не требуется.")
        return

    print(f"[+] Подключение к MongoDB по адресу: {mongo_url}")
    client = MongoClient(mongo_url)
    db = client["dinogochi"]
    collection = db["donations"]

    print(f"[+] Найдено {len(donations_data)} записей для переноса в MongoDB.")
    migrated_count = 0

    for code, data in donations_data.items():
        # Подготовка документа
        doc = {
            "code": code,
            "userid": data.get("userid"),
            "user_first_name": data.get("user_first_name"),
            "amount": data.get("amount"),
            "product": data.get("product"),
            "issued_reward": data.get("issued_reward", False),
            "send_notification": data.get("send_notification", False),
            "time": data.get("time"),
            "col": data.get("col"),
            "donation_id": data.get("donation_id"),
            "status": data.get("status", "done")
        }
        
        # Upsert по полю code
        collection.replace_one({"code": code}, doc, upsert=True)
        migrated_count += 1

    print(f"[✓] Успешно перенесено {migrated_count} записей о донатах в базу данных.")

    # Безопасное удаление / переименование donations.json
    try:
        os.remove(donations_json_path)
        print("[✓] Файл donations.json успешно удален.")
    except Exception as e:
        print(f"[-] Предупреждение при удалении donations.json: {e}")

if __name__ == "__main__":
    migrate_donations()
