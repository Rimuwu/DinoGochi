import os
import json
import random

# Backgrounds list
BGS = ["blue_bg", "green_bg", "green_bg_2", "grey_bg", "orange_bg", "pink_bg", "red_bg", "violet_bg"]

def migrate():
    # 1. Load ru.json to extract emojis
    ru_path = "bot/localization/ru.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru_data = json.load(f)
    
    loc_items_names = ru_data.get("ru", {}).get("items_names", {})
    if not loc_items_names:
        print("Error: loc_items_names under 'ru' not found!")
        return
    
    # 2. Iterate through all items json files and update them
    items_dir = "bot/json/items"
    json_files = [f for f in os.listdir(items_dir) if f.endswith(".json")]
    
    for filename in json_files:
        filepath = os.path.join(items_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        modified = False
        for item_id, item_val in data.items():
            if not isinstance(item_val, dict):
                continue
                
            # Restructure image
            original_image = item_val.get("image")
            if isinstance(original_image, dict) and "background" in original_image:
                # Select a random background anyway to shuffle if requested, or keep it.
                # Since the user requested "для всех предметов установи как элемент square, а фоны раскидай в случайном порядке"
                # we will overwrite/update background to a random one, element to "square".
                icon_val = original_image.get("icon", "null")
                random_bg = random.choice(BGS)
                item_val["image"] = {
                    "background": random_bg,
                    "frame": "elipse",
                    "icon": icon_val
                }
                modified = True
            else:
                icon_val = original_image if (isinstance(original_image, str) and original_image) else "null"
                random_bg = random.choice(BGS)
                item_val["image"] = {
                    "background": random_bg,
                    "frame": "elipse",
                    "icon": icon_val
                }
                modified = True
                
            # Restructure emoji
            # We look up emoji from ru.json
            loc_entry = loc_items_names.get(item_id, {})
            standard_emoji = ""
            if isinstance(loc_entry, dict):
                standard_emoji = loc_entry.get("emoji", "")
            
            # Default fallback if empty
            if not standard_emoji:
                standard_emoji = "🪵"
                
            item_val["emoji"] = standard_emoji
            modified = True
                
        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Migrated item JSON file: {filename}")

    # 3. Remove "emoji" key from all localization files
    loc_dir = "bot/localization"
    loc_files = [f for f in os.listdir(loc_dir) if f.endswith(".json")]
    for filename in loc_files:
        lang_code = os.path.splitext(filename)[0]
        filepath = os.path.join(loc_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        modified = False
        items_names = data.get(lang_code, {}).get("items_names", {})
        for item_id, item_val in items_names.items():
            if isinstance(item_val, dict) and "emoji" in item_val:
                del item_val["emoji"]
                modified = True
                
        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Cleaned up emojis in localization file: {filename}")

if __name__ == "__main__":
    migrate()
