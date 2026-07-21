from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from bson import ObjectId
import json
import uuid

from bot.exec import main_router, bot
from bot.modules.localization import t, get_lang
from bot.redismanager import redis_get, redis_del, get_redis
from bot.models.user import User
from bot.models.dinosaur import Dino
from bot.modules.combat.auto_combat import AutoCombat
from bot.filters.private import IsPrivateChat
from bot.modules.data_format import format_team_members, md_to_html

@main_router.callback_query(F.data.startswith('combat_log_view') | F.data.startswith('clv'))
async def combat_log_view_call(callback: CallbackQuery):
    chatid = callback.message.chat.id
    lang = await get_lang(callback.from_user.id)
        
    prefix = "clv" if callback.data.startswith("clv") else "combat_log_view"
    data = callback.data.split()
    raw_log_id = data[1]
    log_id = f"combat_log:{raw_log_id}" if prefix == "clv" else raw_log_id
    page_idx = int(data[2]) if len(data) > 2 else 0
    dino_id = data[3] if len(data) > 3 else None
    dino_suffix = f" {dino_id}" if dino_id else ""

    result = await redis_get(log_id)
    if not result:
        await callback.answer(t("combat_log.errors.not_found", lang, default="❌ Лог боя не найден или его срок действия истек."), show_alert=True)
        return

    # Determine perspective team by checking if any of the user's dinos are in team Y
    perspective_team = "X"
    if result:
        user = await User.find_one(User.userid == callback.from_user.id)
        if user:
            dinos = await user.get_dinos()
            dino_names = {d.name for d in dinos}
            in_y = False
            for p in result.get("starting_data", {}).get("Y", []):
                p_name = p["name"]
                for suffix in [" (X)", " (Y)"]:
                    if p_name.endswith(suffix):
                        p_name = p_name[:-len(suffix)]
                if p_name in dino_names:
                    in_y = True
                    break
            if in_y:
                perspective_team = "Y"

    # Convert and group logs into text rounds using AutoCombat static helper
    round_logs = AutoCombat.group_and_format_log(result, lang, perspective_team=perspective_team)

    rounds_list = sorted(round_logs.keys())
    if not rounds_list:
        rounds_list = [1]
        round_logs = {1: []}

    page_idx = max(0, min(page_idx, len(rounds_list) - 1))
    target_round = rounds_list[page_idx]
    round_entries = round_logs.get(target_round, [])

    # Format page content
    log_lines = []
    
    # Translate header
    header = t("combat_log.header", lang, page=page_idx + 1, pages=len(rounds_list))
    log_lines.append(header)

    # Prepend starting team info on page 0
    if page_idx == 0:
        if perspective_team == "Y":
            team_my_str = format_team_members(result["starting_data"]["Y"], lang)
            team_opp_str = format_team_members(result["starting_data"]["X"], lang)
        else:
            team_my_str = format_team_members(result["starting_data"]["X"], lang)
            team_opp_str = format_team_members(result["starting_data"]["Y"], lang)

        try:
            teams_info = t("combat_log.team_info_header", lang, team_x=team_my_str, team_y=team_opp_str)
        except Exception:
            teams_info = f"👥 *Составы команд:*\n🟢 Моя команда:\n{team_my_str}\n🔴 Команда противника:\n{team_opp_str}"
        log_lines.append(teams_info + "\n")

    log_lines.extend(round_entries)

    # If it is the last page, append final battle_end and loot if not present
    if page_idx == len(rounds_list) - 1:
        end_key = "combat_log.battle_end"
        if not any("winner_team" in line or "Победитель" in line or "victorious" in line or "Winner" in line for line in round_entries):
            winner_team_code = result["winner"]
            if winner_team_code == "DRAW" or winner_team_code == "draw":
                winner_val = t("combat_log.teams.draw", lang, default="Ничья")
            elif winner_team_code == perspective_team:
                winner_val = t("combat_log.teams.my_team", lang, default="Моя команда")
            else:
                winner_val = t("combat_log.teams.enemy_team", lang, default="Команда противника")
            try:
                log_lines.append(t(end_key, lang, winner_team=winner_val))
            except Exception:
                log_lines.append(f"\n🏆 *Бой завершен! Победитель: {winner_val}!*")
            if result["loot"]:
                from bot.modules.items.item import get_name
                from collections import Counter
                counts = Counter(result["loot"])
                translated_loot = []
                for item_id, count in counts.items():
                    translated_name = get_name(item_id, lang)
                    if count > 1:
                        translated_loot.append(f"{translated_name} x{count}")
                    else:
                        translated_loot.append(translated_name)
                try:
                    log_lines.append(t("combat_log.loot_dropped", lang, loot_list=", ".join(translated_loot)))
                except Exception:
                    log_lines.append(f"\n🎁 *Получен лут:* {', '.join(translated_loot)}")

    full_text = "\n".join(log_lines)

    # Build navigation keyboard
    kb_builder = InlineKeyboardBuilder()
    buttons_row = []
    if page_idx > 0:
        buttons_row.append(InlineKeyboardButton(
            text=t("combat_log.buttons.back", lang, default="◀️ Назад"),
            callback_data=f"{prefix} {raw_log_id} {page_idx - 1}{dino_suffix}"
        ))
        
    buttons_row.append(InlineKeyboardButton(
        text=t("combat_log.buttons.page", lang, page=page_idx + 1, pages=len(rounds_list), default=f"Раунд {page_idx + 1}/{len(rounds_list)}"),
        callback_data="none"
    ))

    if page_idx < len(rounds_list) - 1:
        buttons_row.append(InlineKeyboardButton(
            text=t("combat_log.buttons.next", lang, default="Вперед ▶️"),
            callback_data=f"{prefix} {raw_log_id} {page_idx + 1}{dino_suffix}"
        ))

    kb_builder.row(*buttons_row)
    if dino_id:
        kb_builder.row(InlineKeyboardButton(
            text=t("combat_log.buttons.delete_log", lang, default="🗑️ Удалить этот бой"),
            callback_data=f"cld {raw_log_id} {dino_id}"
        ))
    kb_builder.row(InlineKeyboardButton(
        text=t("combat_log.buttons.close", lang, default="❌ Закрыть"),
        callback_data="combat_log_close"
    ))

    try:
        html_text = md_to_html(full_text)
        if callback.message.photo or callback.message.video or callback.message.document:
            await callback.message.answer(
                html_text,
                reply_markup=kb_builder.as_markup()
            )
            await callback.answer()
        else:
            await callback.message.edit_text(
                html_text,
                reply_markup=kb_builder.as_markup()
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await callback.answer(t("combat_log.errors.display_error", lang, error=str(e), default=f"❌ Ошибка отображения лога: {e}"), show_alert=True)

@main_router.callback_query(F.data == 'combat_log_close')
async def combat_log_close_call(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer()

@main_router.callback_query(F.data.startswith('combat_log_delete') | F.data.startswith('cld'))
async def delete_combat_log(call: CallbackQuery):
    parts = call.data.split()
    battle_id = parts[1]
    if not battle_id.startswith("combat_log:"):
        battle_id = f"combat_log:{battle_id}"
    dino_id = parts[2]
    userid = call.from_user.id
    lang = await get_lang(userid)
        
    from bot.redismanager import redis_del, get_redis
    from bot.models.dinosaur import Dino
    from bson import ObjectId
    import json
    
    r = get_redis()
    
    # Delete combat log key
    await redis_del(battle_id)
    
    # Remove from list dino_battles:{dino_id}
    dino_battles_key = f"dino_battles:{dino_id}"
    history_bytes = await r.lrange(dino_battles_key, 0, -1) # type: ignore
    for h_b in history_bytes:
        try:
            item = json.loads(h_b)
            if item["battle_id"] == battle_id:
                await r.lrem(dino_battles_key, 1, h_b) # type: ignore
                break
        except Exception:
            pass
            
    await call.answer(t("combat_log.deleted_success", lang, default="Бой успешно удален из истории."), show_alert=True)
    
    dino_obj = await Dino.find_one(Dino.id == ObjectId(dino_id))
    if dino_obj:
        from bot.handlers.main_menu.dino_profile import battle_history_profile
        await battle_history_profile(dino_obj, lang, call.message, userid)


@main_router.message(Command(commands=['test_combat']))
async def test_combat_cmd(message: Message):
    import uuid
    from bot.modules.combat.auto_combat import AutoCombat, generate_opponents, CombatParticipant
    from bot.redismanager import redis_set
    from bot.models.user import User
    from bot.models.items import Item
    from bson import ObjectId

    userid = message.from_user.id
    from bot.modules.localization import get_lang
    lang = await get_lang(userid)
    db_user = await User.find_one(User.userid == userid)

    # Parse arguments
    args = message.text.split()[1:]
    count = 1
    preferred_types = []
    
    if args:
        try:
            count = int(args[0])
            preferred_types = args[1:]
        except ValueError:
            preferred_types = args
            count = len(preferred_types)

    # Get user's active dinosaur
    dino_obj = None
    if db_user:
        dino_obj = await db_user.get_last_dino()

    # Create participant list
    team_x = []
    if dino_obj:
        # Fetch user's inventory items to pass to dinosaur (for healing)
        db_items = await Item.find(Item.owner_id == userid).to_list()
        inventory_ids = [item.id for item in db_items]
        dino_part = await CombatParticipant.from_dino(dino_obj, inventory_ids)
        team_x.append(dino_part)
    else:
        # Fallback Mock Dinosaur
        mock_dino = CombatParticipant(
            unique_id=f"mock_dino_{userid}",
            name="TestDinoCarry",
            participant_type="dino",
            max_hp=100.0,
            hp=100.0,
            max_energy=100.0,
            energy=100.0,
            stats={"power": 12.0, "dexterity": 10.0, "intelligence": 12.0, "charisma": 10.0},
            role="carry",
            weapon={
                "item_id": "bone_sword",
                "abilities": {"lvl": 0, "endurance": 50}
            },
            shield={
                "item_id": "wood_shield",
                "abilities": {"lvl": 0, "endurance": 120}
            },
            inventory=[
                {
                    "item_id": "therapeutic_mixture",
                    "count": 3
                }
            ]
        )
        team_x.append(mock_dino)

    # Generate Y team
    try:
        team_y = generate_opponents(count, preferred_types, total_danger=1.0)
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации противников: {e}")
        return

    if not team_y:
        await message.answer("❌ Не удалось сгенерировать противников.")
        return

    # Suffix team names to make turn order logs clear
    for p in team_x:
        p.name = f"{p.name} (X)"
    for p in team_y:
        p.name = f"{p.name} (Y)"

    # Run combat
    try:
        combat = AutoCombat(team_x, team_y)
        result = combat.run()
        
        # Save to Redis (1 day TTL)
        combat_log_id = f"combat_log:{uuid.uuid4().hex}"
        await redis_set(combat_log_id, result, ex=86400)
    except Exception as e:
        await message.answer(f"❌ Ошибка в ходе автобоя: {e}")
        return

    # Format summary
    if result["winner"] == "X":
        winner_val = t("combat_log.teams.my_team", lang, default="Моя команда")
    elif result["winner"] == "Y":
        winner_val = t("combat_log.teams.enemy_team", lang, default="Команда противника")
    else:
        winner_val = t("combat_log.teams.draw", lang, default="Ничья")

    try:
        winner_msg = t("combat_log.battle_end", lang, winner_team=winner_val)
        reason_msg = t(result["reason_key"], lang)
    except Exception:
        winner_msg = f"\n🏆 *Бой завершен! Победитель: {winner_val}!*"
        reason_msg = f"\n💀 Все противники выбыли."

    team_x_str = format_team_members(result["starting_data"]["X"], lang)
    team_y_str = format_team_members(result["starting_data"]["Y"], lang)
    try:
        teams_info = t("combat_log.team_info_header", lang, team_x=team_x_str, team_y=team_y_str)
    except Exception:
        teams_info = f"👥 *Составы команд:*\n🟢 Моя команда:\n{team_x_str}\n🔴 Команда противника:\n{team_y_str}"

    summary_text = t("combat_log.ui.auto_combat_finished", lang, default="🎮 *Автобой завершен!*\n") \
                   + t("combat_log.ui.reason_end", lang, reason=reason_msg, default=f"📝 *Причина окончания:* {reason_msg}\n") \
                   + f"{winner_msg}\n\n" \
                   + f"{teams_info}"
    
    if result["loot"]:
        from bot.modules.items.item import get_name
        from collections import Counter
        counts = Counter(result["loot"])
        translated_loot = []
        for item_id, count in counts.items():
            translated_name = get_name(item_id, lang)
            if count > 1:
                translated_loot.append(f"{translated_name} x{count}")
            else:
                translated_loot.append(translated_name)
        try:
            loot_msg = t("combat_log.loot_dropped", lang, loot_list=", ".join(translated_loot))
        except Exception:
            loot_msg = f"\n🎁 *Получен лут:* {', '.join(translated_loot)}"
        summary_text += f"\n{loot_msg}"
        
    summary_text += f"\n\n🔑 *Redis ID:* <code>{combat_log_id}</code> (24h TTL)"

    # Inline button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t("combat_log.buttons.view_log", lang, default="📝 Лог боя"),
        callback_data=f"combat_log_view {combat_log_id} 0"
    ))

    html_summary = md_to_html(summary_text)
    await message.answer(html_summary, reply_markup=builder.as_markup())


@main_router.message(Command(commands=['test_mob_combat', 'mob_combat']))
async def test_mob_combat_cmd(message: Message):
    import uuid
    from bot.modules.combat.auto_combat import AutoCombat, generate_opponents
    from bot.redismanager import redis_set
    from bot.models.user import User

    userid = message.from_user.id
    from bot.modules.localization import get_lang
    lang = await get_lang(userid)

    # Parse arguments
    args = message.text.split()[1:]
    count_x = 3
    count_y = 3
    
    if args:
        try:
            count_x = int(args[0])
            if len(args) > 1:
                count_y = int(args[1])
            else:
                count_y = count_x
        except ValueError:
            pass

    # Generate teams
    try:
        team_x = generate_opponents(count_x, total_danger=1.0)
        team_y = generate_opponents(count_y, total_danger=1.0)
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации мобов: {e}")
        return

    if not team_x or not team_y:
        await message.answer("❌ Не удалось сгенерировать команды мобов.")
        return

    # Suffix team names
    for p in team_x:
        p.name = f"{p.name} (X)"
    for p in team_y:
        p.name = f"{p.name} (Y)"

    # Run combat (NO DB sync since they are just random mobs)
    try:
        combat = AutoCombat(team_x, team_y)
        result = combat.run()
        
        # Save to Redis (1 day TTL)
        combat_log_id = f"combat_log:{uuid.uuid4().hex}"
        await redis_set(combat_log_id, result, ex=86400)
    except Exception as e:
        await message.answer(f"❌ Ошибка в ходе автобоя мобов: {e}")
        return

    # Format summary
    if result["winner"] == "X":
        winner_val = t("combat_log.teams.my_team", lang, default="Моя команда")
    elif result["winner"] == "Y":
        winner_val = t("combat_log.teams.enemy_team", lang, default="Команда противника")
    else:
        winner_val = t("combat_log.teams.draw", lang, default="Ничья")

    try:
        winner_msg = t("combat_log.battle_end", lang, winner_team=winner_val)
        reason_msg = t(result["reason_key"], lang)
    except Exception:
        winner_msg = f"\n🏆 *Бой завершен! Победитель: {winner_val}!*"
        reason_msg = f"\n💀 Все противники выбыли."

    team_x_str = format_team_members(result["starting_data"]["X"], lang)
    team_y_str = format_team_members(result["starting_data"]["Y"], lang)
    try:
        teams_info = t("combat_log.team_info_header", lang, team_x=team_x_str, team_y=team_y_str)
    except Exception:
        teams_info = f"👥 *Составы команд:*\n🟢 Моя команда:\n{team_x_str}\n🔴 Команда противника:\n{team_y_str}"

    summary_text = t("combat_log.ui.pvp_finished", lang, default="🤖 *PvP Бой Моб vs Моб завершен!*\n") \
                   + t("combat_log.ui.reason_end", lang, reason=reason_msg, default=f"📝 *Причина окончания:* {reason_msg}\n") \
                   + f"{winner_msg}\n\n" \
                   + f"{teams_info}" \
                   + t("combat_log.ui.redis_id", lang, combat_log_id=combat_log_id, default=f"\n\n🔑 *Redis ID:* <code>{combat_log_id}</code> (24h TTL)")

    # Inline button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t("combat_log.buttons.view_log", lang, default="📝 Лог боя"),
        callback_data=f"combat_log_view {combat_log_id} 0"
    ))

    html_summary = md_to_html(summary_text)
    await message.answer(html_summary, reply_markup=builder.as_markup())
