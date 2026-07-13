"""
Модуль управления кастомными пакетами эмодзи.

Позволяет создавать и обновлять стикерпаки через Telegram Bot API,
сохранять полученные custom_emoji_id обратно в custom_emojis.json.
"""
import json
import os
from collections import defaultdict
from typing import Optional
import asyncio
from aiogram.exceptions import TelegramRetryAfter

from aiogram.types import InputSticker, BufferedInputFile

from bot.modules.logs import log


CUSTOM_EMOJIS_PATH = 'bot/json/custom_emojis.json'


async def retry_api_call(func, *args, **kwargs):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except TelegramRetryAfter as e:
            wait_sec = e.retry_after
            log(f"Sticker Set API Rate Limit: sleeping {wait_sec}s before retry...", 2)
            await asyncio.sleep(wait_sec)
        except Exception as e:
            err_msg = str(e).lower()
            if "retry after" in err_msg or "flood control" in err_msg:
                import re
                match = re.search(r'retry after (\d+)', err_msg)
                wait_sec = int(match.group(1)) if match else 30
                log(f"Sticker Set API Rate Limit (parsed): sleeping {wait_sec}s before retry...", 2)
                await asyncio.sleep(wait_sec)
            else:
                raise e
    return await func(*args, **kwargs)


def _load_raw(path: str = CUSTOM_EMOJIS_PATH) -> dict:
    """Читает JSON-файл эмодзи напрямую с диска, инициализирует ID для управляемых и объединяет его с ID из папки data/."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        
        # Initialize empty id/rare_id keys for managed custom emojis so they exist
        for k in data:
            if 'manage' in data[k] or 'master' in data[k]:
                if 'id' not in data[k]:
                    data[k]['id'] = ""
            if 'rare_manage' in data[k] or 'master' in data[k]:
                if 'rare_id' not in data[k]:
                    data[k]['rare_id'] = ""

        filename = os.path.basename(path)
        ids_path = os.path.join("data", filename)
        if os.path.exists(ids_path):
            with open(ids_path, encoding='utf-8') as f:
                saved_ids = json.load(f)
            for k, val in saved_ids.items():
                if k in data:
                    if isinstance(val, dict):
                        if 'id' in val:
                            data[k]['id'] = val['id']
                        if 'rare_id' in val:
                            data[k]['rare_id'] = val['rare_id']
                    else:
                        data[k]['id'] = str(val)
        return data
    except Exception as e:
        log(f'emoji_packs: Не удалось прочитать {path}: {e}', 3)
        return {}


def _save_raw(data: dict, path: str = CUSTOM_EMOJIS_PATH) -> None:
    """Извлекает ID только для управляемых эмодзи и записывает их в соответствующий JSON-файл в папке data/."""
    filename = os.path.basename(path)
    target_dir = "data"
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, filename)

    id_mapping = {}
    for k, entry in data.items():
        if 'manage' in entry or 'rare_manage' in entry or 'master' in entry:
            mapping = {}
            if 'id' in entry:
                mapping['id'] = entry['id']
            if 'rare_id' in entry:
                mapping['rare_id'] = entry['rare_id']
            if mapping:
                id_mapping[k] = mapping

    try:
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(id_mapping, f, ensure_ascii=False, indent=4)
        log(f'emoji_packs: IDs saved to {target_path}.', 1)
    except Exception as e:
        log(f'emoji_packs: Не удалось записать IDs в {target_path}: {e}', 4)


async def sync_emoji_packs(user_id: int, custom_emojis_path: str = CUSTOM_EMOJIS_PATH) -> list[str]:
    """
    Создаёт/обновляет все стикерпаки, описанные в указанном JSON-файле через ключ `manage`.

    Args:
        user_id: Telegram user_id от имени которого создаются паки (обычно первый bot_dev).
        custom_emojis_path: Путь к JSON-файлу с описанием эмодзи.

    Returns:
        Список строк-отчётов о проделанной работе.
    """
    from bot.exec import bot

    data = _load_raw(custom_emojis_path)
    if not data:
        return [f'❌ Не удалось загрузить {custom_emojis_path}.']

    # Получаем username бота для формирования имени пака
    try:
        bot_info = await bot.get_me()
        bot_username = bot_info.username.lower()
    except Exception as e:
        return [f'❌ Не удалось получить username бота: {e}']

    # Группируем managed-эмодзи по pack_name
    packs: dict[str, list[tuple[str, dict, str]]] = defaultdict(list)
    for emoji_key, emoji_data in data.items():
        manage = emoji_data.get('manage')
        if manage and isinstance(manage, dict):
            pack_name = manage.get('pack_name')
            if pack_name:
                if pack_name == "dinogochi_ui":
                    pack_name = "dinogochi_ui_arrows" if manage.get('needs_repainting', False) else "dinogochi_ui_solid"
                packs[pack_name].append((emoji_key, emoji_data, 'regular'))
                
        rare_manage = emoji_data.get('rare_manage')
        if rare_manage and isinstance(rare_manage, dict):
            pack_name = rare_manage.get('pack_name')
            if pack_name:
                if pack_name == "dinogochi_ui":
                    pack_name = "dinogochi_ui_arrows" if rare_manage.get('needs_repainting', False) else "dinogochi_ui_solid"
                packs[pack_name].append((emoji_key, emoji_data, 'rare'))

    if not packs:
        return ['ℹ️ Нет эмодзи с ключом manage — нечего синхронизировать.']

    report = []
    any_data_changed = False

    for pack_name, emoji_entries in packs.items():
        pack_data_changed = False
        full_pack_name = f'{pack_name}_by_{bot_username}'
        needs_repainting = any(
            e[1].get('rare_manage' if e[2] == 'rare' else 'manage', {}).get('needs_repainting', False)
            for e in emoji_entries
        )

        # Проверяем, существует ли пак
        existing_stickers_count = 0
        pack_exists = False
        try:
            existing_set = await retry_api_call(bot.get_sticker_set, full_pack_name)
            pack_exists = True
            existing_stickers_count = len(existing_set.stickers)
            existing_emoji_ids = {
                getattr(st, 'custom_emoji_id', None)
                for st in existing_set.stickers
            }
            
            # Recover missing IDs from existing sticker set on Telegram
            for idx, (emoji_key, emoji_data, type_key) in enumerate(emoji_entries):
                current_id = emoji_data.get('rare_id') if type_key == 'rare' else emoji_data.get('id')
                if not current_id and idx < len(existing_set.stickers):
                    st = existing_set.stickers[idx]
                    alternatives = emoji_data.get('alternatives', [])
                    emoji_char = alternatives[0] if alternatives else '⭐'
                    if getattr(st, 'emoji', '') == emoji_char:
                        found_id = getattr(st, 'custom_emoji_id', None)
                        if found_id:
                            if type_key == 'rare':
                                emoji_data['rare_id'] = found_id
                            else:
                                emoji_data['id'] = found_id
                            pack_data_changed = True
        except Exception as get_err:
            existing_emoji_ids = set()
            # STICKERSET_INVALID means the pack exists but is broken — free the name
            if 'STICKERSET_INVALID' in str(get_err):
                pack_report_pre = [f'📦 <b>Пак</b>: <code>{full_pack_name}</code>',
                                   '  ⚠️ Пак повреждён (STICKERSET_INVALID). Попытка очистки...']
                try:
                    # Try to get stickers without retry to clean them
                    try:
                        broken_set = await bot.get_sticker_set(full_pack_name)
                        for st in broken_set.stickers:
                            try:
                                await retry_api_call(bot.delete_sticker_from_set, st.file_id)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # Try to delete the set itself (needs to be empty first)
                    try:
                        await retry_api_call(bot.delete_sticker_set, full_pack_name)
                        pack_report_pre.append('  🗑️ Сломанный пак удалён, пересоздаём...')
                    except Exception as del_err:
                        pack_report_pre.append(f'  ⚠️ Не удалось удалить сломанный пак: {del_err}')
                except Exception:
                    pass
                report.extend(pack_report_pre)

        pack_report = [f'📦 <b>Пак</b>: <code>{full_pack_name}</code>']
        stickers_to_upload = []
        emoji_keys_to_upload = []

        for emoji_key, emoji_data, type_key in emoji_entries:
            current_id = emoji_data.get('rare_id') if type_key == 'rare' else emoji_data.get('id')
            if current_id and str(current_id) in (str(x) for x in existing_emoji_ids if x):
                suffix = ' (rare)' if type_key == 'rare' else ''
                pack_report.append(f'  ✅ <code>{emoji_key}{suffix}</code> — уже в паке (id: <code>{current_id}</code>)')
                continue

            manage = emoji_data.get('rare_manage', {}) if type_key == 'rare' else emoji_data.get('manage', {})
            image_path = manage.get('image')
            alternatives = emoji_data.get('alternatives', [])
            emoji_char = alternatives[0] if alternatives else '⭐'

            # Если это редкий предмет и картинка отсутствует, попробуем сгенерировать её на лету
            if type_key == 'rare' and image_path and not os.path.exists(image_path):
                try:
                    from bot.modules.items.collect_items import get_all_items
                    from bot.modules.items.image_generator import generate_rare_icon_image
                    
                    ITEMS = get_all_items()
                    if emoji_key in ITEMS:
                        item_data = ITEMS[emoji_key]
                        # Разрешим путь к оригинальной иконке
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
                            
                        rank = item_data.get("rank", "common")
                        generate_rare_icon_image(icon_path, rank, emoji_key)
                except Exception as gen_err:
                    log(f"emoji_packs: Не удалось сгенерировать редкую иконку на лету для {emoji_key}: {gen_err}", 3)

            if not image_path or not os.path.exists(image_path):
                suffix = ' (rare)' if type_key == 'rare' else ''
                pack_report.append(f'  ⚠️ <code>{emoji_key}{suffix}</code> — файл не найден: {image_path}')
                continue

            try:
                from PIL import Image
                import io

                with Image.open(image_path) as img:
                    img = img.convert("RGBA")
                    # Resize to exactly 100x100 for Telegram custom emoji
                    if img.width != 100 or img.height != 100:
                        img = img.resize((100, 100), Image.Resampling.LANCZOS)
                    
                    out_buf = io.BytesIO()
                    img.save(out_buf, format="PNG")
                    img_bytes = out_buf.getvalue()

                sticker = InputSticker(
                    sticker=BufferedInputFile(img_bytes, filename=f'{emoji_key}_{type_key}.png'),
                    format='static',
                    emoji_list=[emoji_char]
                )
                stickers_to_upload.append(sticker)
                emoji_keys_to_upload.append((emoji_key, type_key))
            except Exception as e:
                suffix = ' (rare)' if type_key == 'rare' else ''
                pack_report.append(f'  ❌ <code>{emoji_key}{suffix}</code> — ошибка обработки файла: {e}')

        if not stickers_to_upload and pack_exists:
            pack_report.append('  ℹ️ Новых эмодзи нет.')
            report.extend(pack_report)
            # Still need to save if IDs were recovered from existing pack
            if not pack_data_changed:
                continue

        if not stickers_to_upload and not pack_data_changed:
            report.extend(pack_report)
            continue

        pack_exists_before = pack_exists

        # Создаём или добавляем стикеры
        if not pack_exists:
            try:
                await retry_api_call(
                    bot.create_new_sticker_set,
                    user_id=user_id,
                    name=full_pack_name,
                    title=pack_name.replace('_', ' ').title(),
                    sticker_type='custom_emoji',
                    stickers=[stickers_to_upload[0]],
                    needs_repainting=needs_repainting
                )
                pack_report.append(f'  🆕 Пак создан.')
                pack_exists = True
                await asyncio.sleep(5)

                for sticker, (ekey, tk) in zip(stickers_to_upload[1:], emoji_keys_to_upload[1:]):
                    try:
                        await retry_api_call(
                            bot.add_sticker_to_set,
                            user_id=user_id,
                            name=full_pack_name,
                            sticker=sticker
                        )
                        pack_report.append(f'  ➕ <code>{ekey} ({"rare" if tk == "rare" else "reg"})</code> добавлен в пак.')
                    except Exception as e:
                        pack_report.append(f'  ❌ <code>{ekey} ({"rare" if tk == "rare" else "reg"})</code> — ошибка добавления: {e}')
            except Exception as e:
                err_str = str(e)
                pack_report.append(f'  ❌ Ошибка создания пака: {e}')
                # Handle "name already occupied" — the pack exists but is empty/invisible
                if 'already occupied' in err_str.lower() or 'STICKERSET_INVALID' in err_str:
                    pack_report.append('  🔄 Имя занято — попытка удалить и пересоздать...')
                    try:
                        await retry_api_call(bot.delete_sticker_set, full_pack_name)
                        await asyncio.sleep(3)
                        await retry_api_call(
                            bot.create_new_sticker_set,
                            user_id=user_id,
                            name=full_pack_name,
                            title=pack_name.replace('_', ' ').title(),
                            sticker_type='custom_emoji',
                            stickers=[stickers_to_upload[0]],
                            needs_repainting=needs_repainting
                        )
                        pack_report.append('  🆕 Пак пересоздан после очистки.')
                        pack_exists = True
                        await asyncio.sleep(5)
                        for sticker, (ekey, tk) in zip(stickers_to_upload[1:], emoji_keys_to_upload[1:]):
                            try:
                                await retry_api_call(bot.add_sticker_to_set, user_id=user_id, name=full_pack_name, sticker=sticker)
                                pack_report.append(f'  ➕ <code>{ekey} ({"rare" if tk == "rare" else "reg"})</code> добавлен.')
                            except Exception as add_e:
                                pack_report.append(f'  ❌ <code>{ekey}</code> — ошибка: {add_e}')
                    except Exception as retry_e:
                        pack_report.append(f'  ❌ Не удалось пересоздать пак: {retry_e}')
                        report.extend(pack_report)
                        continue
                else:
                    report.extend(pack_report)
                    continue
        else:
            sticker_invalid_detected = False
            for sticker, (ekey, tk) in zip(stickers_to_upload, emoji_keys_to_upload):
                try:
                    await retry_api_call(
                        bot.add_sticker_to_set,
                        user_id=user_id,
                        name=full_pack_name,
                        sticker=sticker
                    )
                    pack_report.append(f'  ➕ <code>{ekey} ({"rare" if tk == "rare" else "reg"})</code> добавлен в пак.')
                except Exception as e:
                    err_str = str(e)
                    if 'STICKERSET_INVALID' in err_str:
                        sticker_invalid_detected = True
                        pack_report.append(f'  ⚠️ Пак повреждён (STICKERSET_INVALID). Пересоздаём...')
                        break
                    pack_report.append(f'  ❌ <code>{ekey} ({"rare" if tk == "rare" else "reg"})</code> — ошибка добавления: {e}')

            if sticker_invalid_detected:
                # Delete broken pack and recreate with ALL stickers for this pack
                try:
                    broken_set = await retry_api_call(bot.get_sticker_set, full_pack_name)
                    for st in broken_set.stickers:
                        try:
                            await retry_api_call(bot.delete_sticker_from_set, st.file_id)
                        except Exception:
                            pass
                    try:
                        await retry_api_call(bot.delete_sticker_set, full_pack_name)
                    except Exception:
                        pass
                except Exception:
                    pass

                # Rebuild stickers_to_upload with ALL entries for this pack (including previously ✅)
                all_stickers_for_pack = []
                all_keys_for_pack = []
                for ek, ed, tk in emoji_entries:
                    manage = ed.get('rare_manage', {}) if tk == 'rare' else ed.get('manage', {})
                    img_path = manage.get('image')
                    alts = ed.get('alternatives', [])
                    ec = alts[0] if alts else '⭐'
                    if not img_path or not os.path.exists(img_path):
                        continue
                    try:
                        from PIL import Image
                        import io
                        with Image.open(img_path) as img:
                            img = img.convert("RGBA")
                            if img.width != 100 or img.height != 100:
                                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            stk = InputSticker(
                                sticker=BufferedInputFile(buf.getvalue(), filename=f'{ek}_{tk}.png'),
                                format='static',
                                emoji_list=[ec]
                            )
                            all_stickers_for_pack.append(stk)
                            all_keys_for_pack.append((ek, tk))
                    except Exception:
                        pass

                if all_stickers_for_pack:
                    try:
                        await retry_api_call(
                            bot.create_new_sticker_set,
                            user_id=user_id,
                            name=full_pack_name,
                            title=pack_name.replace('_', ' ').title(),
                            sticker_type='custom_emoji',
                            stickers=[all_stickers_for_pack[0]],
                            needs_repainting=needs_repainting
                        )
                        pack_report.append(f'  🔄 Пак пересоздан.')
                        await asyncio.sleep(5)

                        for sticker, (ek, tk) in zip(all_stickers_for_pack[1:], all_keys_for_pack[1:]):
                            try:
                                await retry_api_call(
                                    bot.add_sticker_to_set,
                                    user_id=user_id,
                                    name=full_pack_name,
                                    sticker=sticker
                                )
                            except Exception as e:
                                pack_report.append(f'  ❌ <code>{ek} ({"rare" if tk == "rare" else "reg"})</code> — ошибка добавления при пересоздании: {e}')

                        pack_exists = True
                        # Override upload list so IDs are read correctly below
                        stickers_to_upload = all_stickers_for_pack
                        emoji_keys_to_upload = all_keys_for_pack
                        existing_stickers_count = 0
                        pack_exists_before = False
                    except Exception as e2:
                        pack_report.append(f'  ❌ Ошибка пересоздания пака: {e2}')
                        report.extend(pack_report)
                        continue


        # Получаем актуальные ID из пака
        try:
            updated_set = await retry_api_call(bot.get_sticker_set, full_pack_name)
            base_idx = existing_stickers_count if pack_exists_before else 0
            
            for i, (emoji_key, type_key) in enumerate(emoji_keys_to_upload):
                idx = base_idx + i
                found_id = None
                if idx < len(updated_set.stickers):
                    st = updated_set.stickers[idx]
                    found_id = getattr(st, 'custom_emoji_id', None)
                
                # Резервный поиск по символу эмодзи на случай расхождений
                if not found_id:
                    alternatives = data[emoji_key].get('alternatives', [])
                    emoji_char = alternatives[0] if alternatives else ''
                    for st in updated_set.stickers:
                        if getattr(st, 'emoji', '') == emoji_char:
                            found_id = getattr(st, 'custom_emoji_id', None)
                            break
                            
                if found_id:
                    if type_key == 'rare':
                        data[emoji_key]['rare_id'] = found_id
                    else:
                        data[emoji_key]['id'] = found_id
                    pack_data_changed = True
                    suffix = ' (rare)' if type_key == 'rare' else ''
                    pack_report.append(f'  💾 <code>{emoji_key}{suffix}</code> → ID: <code>{found_id}</code>')
                else:
                    suffix = ' (rare)' if type_key == 'rare' else ''
                    pack_report.append(f'  ⚠️ <code>{emoji_key}{suffix}</code> — не удалось определить ID.')
        except Exception as e:
            pack_report.append(f'  ❌ Ошибка обновления ID: {e}')

        report.extend(pack_report)

        # ✅ Инкрементальное сохранение: сразу после каждого пака, не ждём конца
        if pack_data_changed:
            any_data_changed = True
            # Copy master IDs to clones before saving
            for key, entry in data.items():
                master_key = entry.get("master")
                if master_key and master_key in data:
                    entry["id"] = data[master_key].get("id", "")
                    entry["rare_id"] = data[master_key].get("rare_id", "")
            _save_raw(data, custom_emojis_path)

    # Reload const once after all packs processed
    if any_data_changed:
        try:
            from bot.const import reload_const
            reload_const()
        except Exception as e:
            log(f'emoji_packs: Не удалось перезагрузить const: {e}', 3)

    return report


async def delete_all_emoji_packs(user_id: int) -> list[str]:
    """
    Удаляет все стикерпаки (custom emoji), описанные в custom_emojis.json и items_custom_emojis.json.
    Возвращает список строк-отчётов.
    """
    from bot.exec import bot

    try:
        bot_info = await bot.get_me()
        bot_username = bot_info.username.lower()
    except Exception as e:
        return [f'❌ Не удалось получить username бота: {e}']

    report = []
    paths = [CUSTOM_EMOJIS_PATH, 'bot/json/items_custom_emojis.json']

    pack_names_seen = set()
    for path in paths:
        data = _load_raw(path)
        for emoji_key, emoji_data in data.items():
            manage = emoji_data.get('manage')
            if manage and isinstance(manage, dict):
                pack_name = manage.get('pack_name')
                if pack_name:
                    if pack_name == "dinogochi_ui":
                        pack_name = "dinogochi_ui_arrows" if manage.get('needs_repainting', False) else "dinogochi_ui_solid"
                    pack_names_seen.add(pack_name)
            
            rare_manage = emoji_data.get('rare_manage')
            if rare_manage and isinstance(rare_manage, dict):
                pack_name = rare_manage.get('pack_name')
                if pack_name:
                    if pack_name == "dinogochi_ui":
                        pack_name = "dinogochi_ui_arrows" if rare_manage.get('needs_repainting', False) else "dinogochi_ui_solid"
                    pack_names_seen.add(pack_name)
    
    pack_names_seen.add("dinogochi_ui")
    pack_names_seen.add("dinogochi_ui_color")
    pack_names_seen.add("dinogochi_ui_paint")
    pack_names_seen.add("dinogochi_ui_arrows")
    pack_names_seen.add("dinogochi_ui_solid")

    for pack_name in sorted(pack_names_seen):
        full_pack_name = f'{pack_name}_by_{bot_username}'
        try:
            pack = await retry_api_call(bot.get_sticker_set, full_pack_name)
            # Delete each sticker individually first, then the set
            for st in pack.stickers:
                try:
                    await retry_api_call(bot.delete_sticker_from_set, st.file_id)
                except Exception:
                    pass
            try:
                await retry_api_call(bot.delete_sticker_set, full_pack_name)
                report.append(f'🗑️ Пак <code>{full_pack_name}</code> удалён.')
            except Exception as e:
                report.append(f'⚠️ Пак <code>{full_pack_name}</code> — не удалось удалить сам пак: {e}')
        except Exception:
            report.append(f'ℹ️ Пак <code>{full_pack_name}</code> не найден (уже удалён или не создавался).')

    return report if report else ['ℹ️ Нет паков для удаления.']
