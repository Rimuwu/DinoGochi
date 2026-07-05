import os
import json
import asyncio
import io
import re
from PIL import Image
from aiogram import Bot
from aiogram.types import FSInputFile, InputSticker, BufferedInputFile
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest

MAPPING_FILE = "bot/data/created_emojis.json"

def extract_id(filename: str) -> str:
    match = re.search(r'\d+', filename)
    return match.group() if match else filename

async def safe_save_mappings(mappings: dict, lock: asyncio.Lock):
    async with lock:
        for retry in range(10):
            try:
                os.makedirs(os.path.dirname(MAPPING_FILE), exist_ok=True)
                temp_file = MAPPING_FILE + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as out:
                    json.dump(mappings, out, ensure_ascii=False, indent=4)
                os.replace(temp_file, MAPPING_FILE)
                return True
            except PermissionError:
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error saving JSON: {e}")
                return False
        print(f"Warning: Failed to save mappings to {MAPPING_FILE} after 10 retries due to file lock.")
        return False

async def upload_worker(bot: Bot, user_id: int, categories_list: list, mappings: dict, lock: asyncio.Lock, status_callback=None):
    bot_user = await bot.get_me()
    bot_username = bot_user.username
    
    categories = {
        "dino-com": ("🦕", "Dino Common"),
        "dino-leg": ("🦕", "Dino Legendary"),
        "dino-mys": ("🦕", "Dino Mystery"),
        "dino-rar": ("🦕", "Dino Rare"),
        "dino-unc": ("🦕", "Dino Uncommon"),
        "egg": ("🥚", "Dino Egg")
    }
    
    for cat_name in categories_list:
        if cat_name not in categories:
            continue
        emoji, title_prefix = categories[cat_name]
        
        cat_dir = os.path.join("images", cat_name)
        if not os.path.exists(cat_dir):
            continue
            
        async with lock:
            if cat_name not in mappings:
                mappings[cat_name] = {}
        
        # Get list of files
        files = sorted([f for f in os.listdir(cat_dir) if f.lower().endswith(".png")])
        if not files:
            continue
            
        # Filter files that are not uploaded yet (based on ID)
        to_upload = []
        for f in files:
            dino_id = extract_id(f)
            async with lock:
                is_uploaded = dino_id in mappings[cat_name] or f in mappings[cat_name]
            if not is_uploaded:
                to_upload.append(f)
                
        if not to_upload:
            msg = f"Category [{cat_name}] is already fully uploaded."
            print(msg)
            if status_callback:
                await status_callback(msg)
            continue
            
        msg = f"Starting category [{cat_name}]: {len(to_upload)} files to upload."
        print(msg)
        if status_callback:
            await status_callback(msg)
            
        pack_limit = 120
        
        for f in to_upload:
            full_index = files.index(f)
            pack_num = (full_index // pack_limit) + 1
            
            clean_cat = cat_name.replace("-", "_")
            # Using dnpack1_ prefix instead of dn{user_id}_
            pack_name = f"dnpack_v1_{clean_cat}_{pack_num}_by_{bot_username}"
            pack_title = f"{title_prefix} Set {pack_num}"
            pack_link = f"t.me/addemoji/{pack_name}"
            
            file_path = os.path.join(cat_dir, f)
            try:
                with Image.open(file_path) as img:
                    w, h = img.size
                    
                    # Egg has 10% crop from the top; dino has 0% (no crop)
                    if cat_name == "egg":
                        crop_size = int(0.9 * min(w, h))
                        left = (w - crop_size) // 2
                        top = int(0.1 * h)
                        right = left + crop_size
                        bottom = top + crop_size
                        
                        if bottom > h:
                            diff = bottom - h
                            top -= diff
                            bottom -= diff
                            
                        img = img.crop((left, top, right, bottom))
                    
                    if img.size != (100, 100):
                        img = img.resize((100, 100), Image.Resampling.LANCZOS)
                        
                    out_buf = io.BytesIO()
                    img.save(out_buf, format="PNG")
                    img_bytes = out_buf.getvalue()
                    
                sticker_input = BufferedInputFile(img_bytes, filename=f)
            except Exception as img_err:
                msg = f"Failed to process image {f} with PIL: {img_err}"
                print(msg)
                if status_callback:
                    await status_callback(msg)
                continue
                
            sticker_obj = InputSticker(
                sticker=sticker_input,
                format="static",
                emoji_list=[emoji]
            )
            
            success = False
            while not success:
                try:
                    set_exists = False
                    try:
                        await bot.get_sticker_set(pack_name)
                        set_exists = True
                    except TelegramBadRequest as e:
                        if "STICKERSET_INVALID" in str(e):
                            set_exists = False
                        else:
                            raise e
                            
                    if not set_exists:
                        msg = f"[{cat_name}]: Creating new sticker set: {pack_title}"
                        print(msg)
                        if status_callback:
                            await status_callback(msg)
                        await bot.create_new_sticker_set(
                            user_id=user_id,
                            name=pack_name,
                            title=pack_title,
                            stickers=[sticker_obj],
                            sticker_type="custom_emoji"
                        )
                        msg_link = f"🆕 🎉 Создан новый пак: *{pack_title}* — {pack_link}"
                        print(msg_link)
                        if status_callback:
                            await status_callback(msg_link)
                    else:
                        await bot.add_sticker_to_set(
                            user_id=user_id,
                            name=pack_name,
                            sticker=sticker_obj
                        )
                    
                    # Update pack link in report file
                    async with lock:
                        if "packs" not in mappings:
                            mappings["packs"] = {}
                        mappings["packs"][pack_name] = pack_link
                    
                    await safe_save_mappings(mappings, lock)
                        
                    success = True
                    await asyncio.sleep(1.0)
                    
                except TelegramRetryAfter as e:
                    msg = f"[{cat_name}]: Flood Wait: Sleeping for {e.retry_after} seconds..."
                    print(msg)
                    if status_callback:
                        await status_callback(msg)
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    msg = f"[{cat_name}]: Error uploading {f}: {str(e)}"
                    print(msg)
                    if status_callback:
                        await status_callback(msg)
                    await asyncio.sleep(5.0)
            
            # Retrieve the custom_emoji_id
            id_retrieved = False
            while not id_retrieved:
                try:
                    sticker_set = await bot.get_sticker_set(pack_name)
                    if sticker_set.stickers:
                        latest_sticker = sticker_set.stickers[-1]
                        dino_id = extract_id(f)
                        
                        async with lock:
                            mappings[cat_name][dino_id] = latest_sticker.custom_emoji_id
                            
                        await safe_save_mappings(mappings, lock)
                            
                    id_retrieved = True
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    print(f"Error fetching sticker ID for {f}: {str(e)}")
                    await asyncio.sleep(2.0)
                    
            async with lock:
                progress_count = len(mappings[cat_name])
            if progress_count % 10 == 0:
                msg = f"Progress in [{cat_name}]: {progress_count}/{len(files)} uploaded."
                print(msg)
                if status_callback:
                    await status_callback(msg)

async def upload_all(bot: Bot, user_id: int, status_callback=None):
    # 1. Load existing mappings
    mappings = {}
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                mappings = json.load(f)
        except Exception:
            pass
            
    # Migrate any legacy filename-based keys to pure numeric ID keys (ignoring the "packs" field)
    migrated = False
    for cat in list(mappings.keys()):
        if cat == "packs":
            continue
        cat_mappings = mappings[cat]
        new_cat_mappings = {}
        for key, val in cat_mappings.items():
            if key.endswith(".png"):
                new_key = extract_id(key)
                new_cat_mappings[new_key] = val
                migrated = True
            else:
                new_cat_mappings[key] = val
        mappings[cat] = new_cat_mappings
        
    lock = asyncio.Lock()
    if migrated:
        await safe_save_mappings(mappings, lock)
        
    # 4 concurrent groups for parallel upload workers
    worker_tasks_groups = [
        ["egg"],
        ["dino-com"],
        ["dino-unc"],
        ["dino-rar", "dino-leg", "dino-mys"]
    ]
    
    tasks = []
    for group in worker_tasks_groups:
        tasks.append(upload_worker(bot, user_id, group, mappings, lock, status_callback))
        
    await asyncio.gather(*tasks)
    
    if status_callback:
        await status_callback("🎉 Finished uploading all assets!")
