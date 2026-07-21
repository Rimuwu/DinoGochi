import os
import json
from PIL import Image
from bot.modules.logs import log
from bot.modules.items.collect_items import get_all_items

# Backgrounds list
BGS = ["blue_bg", "green_bg", "green_bg_2", "grey_bg", "orange_bg", "pink_bg", "red_bg", "violet_bg"]

def generate_item_image_composite(item_data: dict) -> Image.Image:
    # Defaults
    bg_name = "grey_bg"
    frame_name = "rectagel"
    icon_name = "null"
    
    image_conf = item_data.get("image")
    if isinstance(image_conf, dict):
        bg_name = image_conf.get("background", "grey_bg")
        frame_val = image_conf.get("frame", "square")
        frame_name = "rectagel" if frame_val == "square" else "elipse"
        icon_name = image_conf.get("icon", "null")
    elif isinstance(image_conf, str) and image_conf:
        icon_name = image_conf

    # 1. Open background
    bg_path = f"images/items/elements/{bg_name}.png"
    if not os.path.exists(bg_path):
        bg_path = "images/items/elements/grey_bg.png"
        
    bg = Image.open(bg_path).convert("RGBA") # Size (720, 360)
    
    # 2. Open frame
    frame_path = f"images/items/elements/{frame_name}.png"
    if not os.path.exists(frame_path):
        frame_path = "images/items/elements/rectagel.png"
        
    frame = Image.open(frame_path).convert("RGBA")
    # Resize frame to (200, 200)
    frame = frame.resize((200, 200), Image.Resampling.LANCZOS)
    
    # 3. Open icon
    icon_path = f"images/items/{icon_name}.png"
    if not os.path.exists(icon_path):
        icon_path = f"images/items/{icon_name}"
        
    if not os.path.exists(icon_path) or os.path.isdir(icon_path):
        icon_path = "images/items/null.png"
        
    if os.path.exists(icon_path):
        icon = Image.open(icon_path).convert("RGBA")
    else:
        icon = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        
    # Resize icon to (128, 128)
    icon = icon.resize((128, 128), Image.Resampling.LANCZOS)
    
    # Paste frame: Centered (Width: 720, Height: 360)
    # fx = 360 - 100 = 260, fy = 180 - 100 = 80
    bg.paste(frame, (260, 80), frame)
    
    # Paste icon: Centered (Width: 720, Height: 360)
    # ix = 360 - 64 = 296, iy = 180 - 64 = 116
    bg.paste(icon, (296, 116), icon)
    
    # Убираем прозрачность
    bg = bg.convert("RGB")
    
    return bg

def pregenerate_item_images():
    log("Запуск прегенерации картинок предметов...", lvl=1)
    os.makedirs("images/items/generated", exist_ok=True)
    
    ITEMS = get_all_items()
    total = len(ITEMS)
    count = 0
    for item_id, item_data in ITEMS.items():
        try:
            file_path = f"images/items/generated/{item_id}.png"
            if os.path.exists(file_path):
                count += 1
                if count % 20 == 0 or count == total:
                    log(f"Прогресс прегенерации: {count}/{total} предметов ({int(count/total*100)}%)", lvl=1)
                continue

            img = generate_item_image_composite(item_data)
            img.save(file_path, format="PNG")
            count += 1
            if count % 20 == 0 or count == total:
                log(f"Прогресс прегенерации: {count}/{total} предметов ({int(count/total*100)}%)", lvl=1)
        except Exception as e:
            log(f"Ошибка прегенерации картинки для {item_id}: {e}", lvl=3)
            
    log(f"Прегенерация завершена. Успешно создано изображений: {count}/{total}", lvl=1)

def generate_rare_icon_image(icon_path: str, rank: str, item_id: str) -> str:
    """Генерирует иконку предмета с круглым фоном редкости."""
    target_dir = "images/items/generated"
    os.makedirs(target_dir, exist_ok=True)
    target_path = f"{target_dir}/rare_{item_id}.png"
    
    bg_path = f"images/items/elements/rares/{rank}.png"
    if not os.path.exists(bg_path):
        bg_path = "images/items/elements/rares/common.png"
        
    try:
        from PIL import ImageDraw
        # Создаем круглую маску
        mask = Image.new("L", (100, 100), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 100, 100), fill=255)
        
        # Загружаем и изменяем размер фона
        with Image.open(bg_path) as bg:
            bg = bg.convert("RGBA").resize((100, 100), Image.Resampling.LANCZOS)
            circle_bg = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            circle_bg.paste(bg, (0, 0), mask)
            
        # Загружаем и накладываем иконку по центру
        if os.path.exists(icon_path):
            with Image.open(icon_path) as icon:
                icon = icon.convert("RGBA").resize((68, 68), Image.Resampling.LANCZOS)
                circle_bg.paste(icon, (16, 16), icon)
        else:
            icon = Image.new("RGBA", (68, 68), (0, 0, 0, 0))
            circle_bg.paste(icon, (16, 16), icon)
            
        circle_bg.save(target_path, format="PNG")
        return target_path
    except Exception as e:
        log(f"Ошибка при создании редкой иконки для {item_id}: {e}", lvl=3)
        return icon_path

def auto_generate_items_emojis_json():
    log("Запуск генерации items_custom_emojis.json...", lvl=1)
    ITEMS = get_all_items()
    
    path = "bot/json/items_custom_emojis.json"
    existing = {}
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                existing = json.load(f)
            
            # Merge with IDs from data/items_custom_emojis.json
            ids_path = "data/items_custom_emojis.json"
            if os.path.exists(ids_path):
                with open(ids_path, encoding='utf-8') as f:
                    saved_ids = json.load(f)
                for k, val in saved_ids.items():
                    if k in existing:
                        if isinstance(val, dict):
                            if 'id' in val:
                                existing[k]['id'] = val['id']
                            if 'rare_id' in val:
                                existing[k]['rare_id'] = val['rare_id']
                        else:
                            existing[k]['id'] = str(val)
        except Exception:
            existing = {}
            
    sorted_item_keys = sorted(list(ITEMS.keys()))
    
    # 1. Map visual keys to their first item (the master)
    visual_key_to_master = {}
    item_to_master = {}
    
    for item_id in sorted_item_keys:
        item_data = ITEMS[item_id]
        image_conf = item_data.get("image")
        
        bg_name = "grey_bg"
        frame_name = "rectagel"
        icon_name = "null"
        
        if isinstance(image_conf, dict):
            bg_name = image_conf.get("background", "grey_bg")
            frame_val = image_conf.get("frame", "square")
            frame_name = "rectagel" if frame_val == "square" else "elipse"
            icon_name = image_conf.get("icon", "null")
        elif isinstance(image_conf, str) and image_conf:
            icon_name = image_conf
            
        rank = str(item_data.get("rank", "common")).lower()
        v_key = (icon_name, rank)
        if v_key not in visual_key_to_master:
            visual_key_to_master[v_key] = item_id
        else:
            item_to_master[item_id] = visual_key_to_master[v_key]
 
    # Resolve icon path per item (for manage.image)
    def _resolve_icon_path(item_data: dict) -> str:
        image_conf = item_data.get("image")
        icon_name = "null"
        if isinstance(image_conf, dict):
            icon_name = image_conf.get("icon", "null")
        elif isinstance(image_conf, str) and image_conf:
            icon_name = image_conf
        icon_path = f"images/items/{icon_name}.png"
        if not os.path.exists(icon_path):
            icon_path = f"images/items/{icon_name}"
        if not os.path.exists(icon_path) or os.path.isdir(icon_path):
            icon_path = "images/items/null.png"
        return icon_path
 
    # 2. Build updated data (only masters increment pack indices)
    master_keys = sorted(list(visual_key_to_master.values()))
    master_to_pack = {}
    for idx, master_id in enumerate(master_keys):
        pack_num = (idx // 120) + 1
        master_to_pack[master_id] = f"dg_items_{pack_num}"
 
    updated_data = {}
    for item_id in sorted_item_keys:
        item_data = ITEMS[item_id]
        standard_emoji = item_data.get("emoji", "🪵")
        item_entry = existing.get(item_id, {})
        
        if item_id in item_to_master:
            # It's a clone
            master_id = item_to_master[item_id]
            master_existing = existing.get(master_id, {})
            current_id = master_existing.get("id") or item_entry.get("id", "")
            current_rare_id = master_existing.get("rare_id") or item_entry.get("rare_id", "")
            
            updated_data[item_id] = {
                "id": current_id,
                "rare_id": current_rare_id,
                "alternatives": [standard_emoji],
                "master": master_id
            }
        else:
            # It's a master — use raw icon file
            current_id = item_entry.get("id", "")
            current_rare_id = item_entry.get("rare_id", "")
            pack_name = master_to_pack[item_id]
            rare_pack_name = pack_name.replace("dg_items_", "dg_items_rare_")
            icon_path = _resolve_icon_path(item_data)
            
            rank = item_data.get("rank", "common")
            rare_icon_path = generate_rare_icon_image(icon_path, rank, item_id)
            
            updated_data[item_id] = {
                "id": current_id,
                "rare_id": current_rare_id,
                "alternatives": [standard_emoji],
                "manage": {
                    "pack_name": pack_name,
                    "image": icon_path,
                    "needs_repainting": False
                },
                "rare_manage": {
                    "pack_name": rare_pack_name,
                    "image": rare_icon_path,
                    "needs_repainting": False
                }
            }
            
    # Copy master IDs to clones
    for item_id, entry in updated_data.items():
        master_id = entry.get("master")
        if master_id and master_id in updated_data:
            entry["id"] = updated_data[master_id].get("id", "")
            entry["rare_id"] = updated_data[master_id].get("rare_id", "")
            
    # Save only IDs to data/items_custom_emojis.json
    ids_dir = "data"
    os.makedirs(ids_dir, exist_ok=True)
    ids_path = os.path.join(ids_dir, "items_custom_emojis.json")
    id_mapping = {}
    for k, entry in updated_data.items():
        mapping = {}
        if 'id' in entry and entry['id']:
            mapping['id'] = entry['id']
        if 'rare_id' in entry and entry['rare_id']:
            mapping['rare_id'] = entry['rare_id']
        if mapping:
            id_mapping[k] = mapping
            
    try:
        with open(ids_path, 'w', encoding='utf-8') as f:
            json.dump(id_mapping, f, ensure_ascii=False, indent=4)
        log(f"IDs saved to {ids_path}", lvl=1)
    except Exception as e:
        log(f"Failed to save IDs to {ids_path}: {e}", lvl=3)

    # Remove IDs from updated_data before saving to bot/json/items_custom_emojis.json
    for k in updated_data:
        if 'id' in updated_data[k]:
            del updated_data[k]['id']
        if 'rare_id' in updated_data[k]:
            del updated_data[k]['rare_id']

    with open(path, "w", encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
        
    log("Генерация items_custom_emojis.json завершена.", lvl=1)
