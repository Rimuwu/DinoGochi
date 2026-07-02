from bot.modules.images_save import send_SmartPhoto
from bot.filters.private import IsPrivateChat
from bot.filters.translated_text import Text
from bot.filters.authorized import IsAuthorizedUser
from bot.exec import main_router, bot
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.filters import Command
from bson import ObjectId
from bot.models.items import Item
from bot.models.user import User
from bot.const import GAME_SETTINGS
from bot.modules.items.item import get_name, get_data as get_item_data
from bot.modules.states_fabric.state_handlers import ChooseInventoryHandler
import random
from bot.modules.user.premium import premium

async def get_upgradable_items(userid: int):
    all_items = await Item.find(Item.owner_id == userid).to_list()
    upgradable = []
    for it in all_items:
        # Check types
        if it.type not in ['weapon', 'armor', 'backpack', 'sleep', 'journey', 'collecting', 'game']:
            continue
        lvl = it.abilities.get('lvl', 0)
        # Limit level
        if it.type == 'weapon' and lvl >= 10:
            continue
        if it.type != 'weapon' and lvl >= 5:
            continue
        
        # Count copies
        total_count = 0
        for other in all_items:
            if other.item_id == it.item_id and other.abilities.get('lvl', 0) == lvl:
                total_count += other.count
        if total_count >= 2:
            if not any(u.item_id == it.item_id and u.abilities.get('lvl', 0) == lvl for u in upgradable):
                upgradable.append(it)
    return upgradable

async def get_user_runes(userid: int):
    all_items = await Item.find(Item.owner_id == userid).to_list()
    runes = []
    for it in all_items:
        if it.type == 'rune' and it.count > 0:
            runes.append(it)
    return runes

async def open_blacksmith_menu(userid: int, chatid: int, lang: str):
    reply_markup = await m(userid, 'blacksmith_menu', lang)

    photo = 'images/remain/blacksmith.png'
    await send_SmartPhoto(chatid, photo, t('blacksmith.welcome', lang), 'Markdown', reply_markup)

@HDMessage
@main_router.message(Command(commands=['blacksmith', 'forge', 'кузнец']), IsPrivateChat(), IsAuthorizedUser())
async def blacksmith_command(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    await open_blacksmith_menu(userid, message.chat.id, lang)

async def open_blacksmith_select(userid: int, chatid: int, lang: str):
    upgradable = await get_upgradable_items(userid)
    if not upgradable:
        reply_markup = await m(userid, 'blacksmith_menu', lang)
        await bot.send_message(chatid, t('blacksmith.no_items', lang), reply_markup=reply_markup)
        return
        
    transmitted_data = {
        'chatid': chatid,
        'lang': lang,
        'userid': userid
    }
    
    custom_inventory = []
    for item in upgradable:
        custom_inventory.append({
            '_id': item.id,
            'owner_id': item.owner_id,
            'items_data': item.items_data,
            'count': item.count
        })
        
    await ChooseInventoryHandler(
        blacksmith_select_item, userid, chatid, lang,
        inventory=custom_inventory,
        changing_filters=False,
        transmitted_data=transmitted_data
    ).start()

async def blacksmith_select_item(item_dict: dict, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    
    from bot.modules.get_state import get_state
    state = await get_state(userid, chatid)
    if state:
        await state.clear()
        
    await open_blacksmith_menu(userid, chatid, lang)
    
    db_item = await Item.find_one(Item.owner_id == userid, Item.items_data == item_dict)
    if not db_item:
        await bot.send_message(chatid, t('blacksmith.error_find', lang))
        return
        
    # Check max upgrades/fusions possible based on user items
    all_matching = await Item.find(Item.owner_id == userid, {"items_data.item_id": db_item.item_id}).to_list()
    same_lvl_items = [it for it in all_matching if it.abilities.get('lvl', 0) == db_item.get_level()]
    total_copies = sum(it.count for it in same_lvl_items)
    max_fusions = total_copies // 2
    
    if max_fusions < 1:
        await bot.send_message(chatid, t('blacksmith.no_items', lang))
        return

    max_fusions = min(max_fusions, 1000)
        
    if max_fusions == 1:
        # Proceed directly with quantity 1
        await choose_rune_step(chatid, db_item, 1, lang)
    else:
        # Show quantity selection buttons
        builder = InlineKeyboardBuilder()
        for q in range(1, min(max_fusions, 10) + 1):
            builder.button(text=str(q), callback_data=f"bs_q:{db_item.id}:{q}")
        if max_fusions > 10:
            builder.button(text=f"Max ({max_fusions})", callback_data=f"bs_q:{db_item.id}:{max_fusions}")
        builder.button(text=t('blacksmith.cancel_btn', lang), callback_data="bs_cancel")
        builder.adjust(5)
        
        text = t('blacksmith.choose_quantity', lang, total=total_copies, max_upg=max_fusions)
        await bot.send_message(chatid, text, reply_markup=builder.as_markup())

@main_router.callback_query(IsPrivateChat(), F.data.startswith('bs_q:'))
async def bs_quantity_select(callback: CallbackQuery):
    if not callback.message:
        return
    await callback.message.delete()
    lang = await get_lang(callback.from_user.id)
    
    parts = callback.data.split(':')
    item_db_id = parts[1]
    quantity = int(parts[2])
    
    db_item = await Item.find_one(Item.id == ObjectId(item_db_id))
    if not db_item:
        await bot.send_message(callback.message.chat.id, t('blacksmith.error_find', lang))
        return
        
    await choose_rune_step(callback.message.chat.id, db_item, quantity, lang)

async def choose_rune_step(chatid: int, db_item: Item, quantity: int, lang: str):
    userid = db_item.owner_id
    current_lvl = db_item.get_level()
    target_lvl = current_lvl + 1
    
    runes = await get_user_runes(userid)
    applicable_runes = []
    for rune in runes:
        rune_data = get_item_data(rune.item_id)
        abilities = rune_data.get('abilities', {})
        rune_type = abilities.get('rune_type', 0)
        if rune_type == 1:
            max_lvl = abilities.get('max_lvl', 0)
            if target_lvl <= max_lvl:
                applicable_runes.append(rune)
        elif rune_type == 2:
            rune_target_lvl = abilities.get('target_lvl')
            if rune_target_lvl is None or rune_target_lvl == target_lvl:
                applicable_runes.append(rune)
                
    if not applicable_runes:
        await show_confirmation(chatid, db_item, "none", quantity, lang)
        return
        
    builder = InlineKeyboardBuilder()
    for rune in applicable_runes:
        rname = get_name(rune.item_id, lang, rune.abilities)
        builder.button(text=f"{rname} (x{rune.count})", callback_data=f"bs_r:{db_item.id}:{rune.item_id}:{quantity}")
    builder.button(text=t('blacksmith.no_rune', lang), callback_data=f"bs_r:{db_item.id}:none:{quantity}")
    builder.adjust(1)
    
    await bot.send_message(chatid, t('blacksmith.choose_rune', lang), reply_markup=builder.as_markup())

async def show_confirmation(chatid: int, db_item: Item, rune_item_id: str, quantity: int, lang: str, mark: int = 0, edit_message=None):
    userid = db_item.owner_id
    item_id = db_item.item_id
    current_lvl = db_item.get_level()
    target_lvl = current_lvl + 1
    
    prices = GAME_SETTINGS.get('blacksmith_prices', {})
    single_price = prices.get(str(target_lvl), 100 * target_lvl)
    total_price = single_price * quantity
    
    chances = GAME_SETTINGS.get('blacksmith_chances', {})
    base_chance = chances.get(str(target_lvl), 0.5)
    final_chance = base_chance
    
    if rune_item_id != "none":
        rune_data = get_item_data(rune_item_id)
        rune_type = rune_data.get('abilities', {}).get('rune_type', 0)
        if rune_type == 1:
            max_lvl = rune_data['abilities'].get('max_lvl', 0)
            if target_lvl <= max_lvl:
                final_chance = 1.0
        elif rune_type == 2:
            rune_target_lvl = rune_data['abilities'].get('target_lvl')
            if rune_target_lvl is None or target_lvl == rune_target_lvl:
                add_chance = rune_data['abilities'].get('add_chance', 0.0)
                mult_chance = rune_data['abilities'].get('mult_chance', 1.0)
                final_chance = (base_chance + add_chance) * mult_chance

    # Premium bonus: add flat chance bonus for subscribers
    is_premium = await premium(userid)
    if is_premium and final_chance < 1.0:
        premium_bonus = GAME_SETTINGS.get('blacksmith_premium_bonus', 0.0)
        final_chance += premium_bonus
            
    final_chance = max(0.0, min(1.0, final_chance))
    chance_pct = round(final_chance * 100, 4)
    
    item_name = get_name(item_id, lang, db_item.abilities)
    
    text = t('blacksmith.confirm_text', lang,
             item_name=item_name,
             quantity=quantity,
             price=total_price,
             chance=chance_pct)
             
    builder = InlineKeyboardBuilder()
    # Creator name toggle (only for target lvl >= 2)
    if target_lvl >= 2:
        mark_label = t('blacksmith.mark_name_on' if mark else 'blacksmith.mark_name_off', lang)
        builder.button(text=mark_label, callback_data=f"bs_mark:{db_item.id}:{rune_item_id}:{quantity}:{1 - mark}")
    builder.button(text=t('blacksmith.confirm_btn', lang), callback_data=f"bs_upg:{db_item.id}:{rune_item_id}:{quantity}:{mark}")
    builder.button(text=t('blacksmith.cancel_btn', lang), callback_data="bs_cancel")
    builder.adjust(1)
    
    if edit_message is not None:
        await edit_message.edit_text(text, parse_mode='Markdown', reply_markup=builder.as_markup())
    else:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=builder.as_markup())

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.blacksmith.upgrade'), IsAuthorizedUser())
async def blacksmith_upgrade_button(message: Message):
    userid = message.from_user.id
    lang = await get_lang(userid)
    await open_blacksmith_select(userid, message.chat.id, lang)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.blacksmith.my_items'), IsAuthorizedUser())
async def blacksmith_my_items_button(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)
    
    all_items = await Item.find(Item.owner_id == userid).to_list()
    upgraded_items = [it for it in all_items if it.get_level() > 0]
    
    if not upgraded_items:
        await bot.send_message(chatid, t('blacksmith.no_upgraded_items', lang))
        return
        
    custom_inventory = []
    for item in upgraded_items:
        custom_inventory.append({
            '_id': item.id,
            'owner_id': item.owner_id,
            'items_data': item.items_data,
            'count': item.count
        })
        
    await ChooseInventoryHandler(
        None, userid, chatid, lang,
        inventory=custom_inventory,
        changing_filters=False
    ).start()

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.blacksmith.info'), IsAuthorizedUser())
async def blacksmith_info_button(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    
    chances = GAME_SETTINGS.get('blacksmith_chances', {})
    prices = GAME_SETTINGS.get('blacksmith_prices', {})
    
    table_data = ""
    for lvl in range(1, 11):
        price = prices.get(str(lvl), 100 * lvl)
        chance = chances.get(str(lvl), 0.5) * 100
        coins_word = t('blacksmith.coins_name', lang)
        table_data += f"  `+{lvl}`: {price} {coins_word} | {chance}%\n"
        
    text = t('blacksmith.info_text', lang, table_data=table_data)
    await bot.send_message(chatid, text, parse_mode='Markdown')

@main_router.callback_query(IsPrivateChat(), F.data.startswith('bs_r:'))
async def bs_rune_select(callback: CallbackQuery):
    if not callback.message:
        return
    await callback.message.delete()
    lang = await get_lang(callback.from_user.id)
    
    parts = callback.data.split(':')
    item_db_id = parts[1]
    rune_item_id = parts[2]
    quantity = int(parts[3])
    
    db_item = await Item.find_one(Item.id == ObjectId(item_db_id))
    if not db_item:
        await bot.send_message(callback.message.chat.id, t('blacksmith.error_find', lang))
        return
        
    await show_confirmation(callback.message.chat.id, db_item, rune_item_id, quantity, lang)

@main_router.callback_query(IsPrivateChat(), F.data == 'bs_cancel')
async def bs_cancel(callback: CallbackQuery):
    if not callback.message:
        return
    await callback.message.delete()
    lang = await get_lang(callback.from_user.id)
    await open_blacksmith_menu(callback.from_user.id, callback.message.chat.id, lang)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('bs_mark:'))
async def bs_mark_toggle(callback: CallbackQuery):
    """Toggle creator name mark checkbox on the confirmation screen."""
    if not callback.message:
        return
    await callback.answer()  # acknowledge the callback without flicker
    lang = await get_lang(callback.from_user.id)
    parts = callback.data.split(':')
    item_db_id, rune_item_id, quantity, new_mark = parts[1], parts[2], int(parts[3]), int(parts[4])
    db_item = await Item.find_one(Item.id == ObjectId(item_db_id))
    if not db_item:
        await callback.message.edit_text(t('blacksmith.error_find', lang))
        return
    await show_confirmation(callback.message.chat.id, db_item, rune_item_id, quantity, lang,
                            mark=new_mark, edit_message=callback.message)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('bs_upg:'))
async def bs_upgrade_confirm(callback: CallbackQuery):
    if not callback.message:
        return
    await callback.message.delete()
    
    userid = callback.from_user.id
    chatid = callback.message.chat.id
    lang = await get_lang(userid)
    
    parts = callback.data.split(':')
    item_db_id = parts[1]
    rune_item_id = parts[2]
    quantity = int(parts[3])
    mark_name = int(parts[4]) if len(parts) > 4 else 0
    
    user = await User.find_one(User.userid == userid)
    if not user:
        return
        
    db_item = await Item.find_one(Item.id == ObjectId(item_db_id))
    if not db_item:
        await bot.send_message(chatid, t('blacksmith.error_find', lang))
        return
        
    current_lvl = db_item.get_level()
    target_lvl = current_lvl + 1
    prices = GAME_SETTINGS.get('blacksmith_prices', {})
    single_price = prices.get(str(target_lvl), 100 * target_lvl)
    total_price = single_price * quantity
    
    # Check coins
    if user.coins < total_price:
        await bot.send_message(chatid, t('blacksmith.no_coins', lang, price=total_price, coins=user.coins))
        return
        
    # Check if they have another copy of this item
    all_matching = await Item.find(Item.owner_id == userid, {"items_data.item_id": db_item.item_id}).to_list()
    same_lvl_items = [it for it in all_matching if it.abilities.get('lvl', 0) == current_lvl]
    total_copies = sum(it.count for it in same_lvl_items)
    if total_copies < quantity * 2:
        await bot.send_message(chatid, t('blacksmith.no_items', lang))
        return
        
    # Check rune
    rune_item = None
    if rune_item_id != "none":
        rune_item = await Item.find_one(Item.owner_id == userid, {"items_data.item_id": rune_item_id})
        if not rune_item or rune_item.count < quantity:
            has_count = rune_item.count if rune_item else 0
            await bot.send_message(chatid, t('blacksmith.no_runes_multiple', lang, quantity=quantity, has=has_count))
            return
            
    # Calculate chance
    chances = GAME_SETTINGS.get('blacksmith_chances', {})
    base_chance = chances.get(str(target_lvl), 0.5)
    final_chance = base_chance
    
    if rune_item_id != "none":
        rune_data = get_item_data(rune_item_id)
        rune_type = rune_data.get('abilities', {}).get('rune_type', 0)
        if rune_type == 1:
            max_lvl = rune_data['abilities'].get('max_lvl', 0)
            if target_lvl <= max_lvl:
                final_chance = 1.0
        elif rune_type == 2:
            rune_target_lvl = rune_data['abilities'].get('target_lvl')
            if rune_target_lvl is None or target_lvl == rune_target_lvl:
                add_chance = rune_data['abilities'].get('add_chance', 0.0)
                mult_chance = rune_data['abilities'].get('mult_chance', 1.0)
                final_chance = (base_chance + add_chance) * mult_chance

    # Premium bonus: add flat chance bonus for subscribers
    is_premium = await premium(userid)
    if is_premium and final_chance < 1.0:
        premium_bonus = GAME_SETTINGS.get('blacksmith_premium_bonus', 0.0)
        final_chance += premium_bonus
            
    final_chance = max(0.0, min(1.0, final_chance))
    
    # Deduct coins
    await user.remove_coins(total_price)

    # Remove items (support differing durabilities/abilities by sorting matching items)
    to_remove = quantity * 2
    same_lvl_items.sort(key=lambda it: it.abilities != db_item.abilities)
    for it in same_lvl_items:
        if to_remove <= 0:
            break
        if it.count <= to_remove:
            to_remove -= it.count
            await it.delete()
        else:
            await it.update({"$inc": {"count": -to_remove}})
            to_remove = 0
    
    # Remove runes
    if rune_item_id != "none" and rune_item:
        await Item.remove(userid, rune_item_id, quantity, rune_item.abilities)
        
    # Roll all fusions at once using binomial sampling
    success_count = sum(1 for _ in range(quantity) if random.random() <= final_chance)
    fail_count = quantity - success_count

    from bot.modules.items.item import get_item_endurance_max

    if success_count > 0:
        new_abilities = dict(db_item.abilities)
        new_abilities['lvl'] = target_lvl
        target_item_dict = {"item_id": db_item.item_id, "abilities": {"lvl": target_lvl}}
        new_endurance_max = get_item_endurance_max(target_item_dict)
        if new_endurance_max:
            new_abilities['endurance'] = new_endurance_max
        # Stamp author (userid) if requested (target_lvl >= 2 only)
        if mark_name and target_lvl >= 2:
            new_abilities['author'] = userid
        await Item.add(userid, db_item.item_id, success_count, new_abilities)

    # Send final result summary
    reply_markup = await m(userid, 'blacksmith_menu', lang)
    result_text = t('blacksmith.results', lang, success=success_count, failed=fail_count)
    await bot.send_message(chatid, result_text, parse_mode='Markdown', reply_markup=reply_markup)


# ─── Erase Creator Name ───────────────────────────────────────────────────────

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.blacksmith.erase_name'), IsAuthorizedUser())
async def blacksmith_erase_name_button(message: Message):
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)

    all_items = await Item.find(Item.owner_id == userid).to_list()
    named_items = [it for it in all_items if it.abilities.get('author')]

    if not named_items:
        reply_markup = await m(userid, 'blacksmith_menu', lang)
        await bot.send_message(chatid, t('blacksmith.erase_no_items', lang), reply_markup=reply_markup)
        return

    custom_inventory = [
        {'_id': it.id, 'owner_id': it.owner_id, 'items_data': it.items_data, 'count': it.count}
        for it in named_items
    ]
    transmitted_data = {'chatid': chatid, 'lang': lang, 'userid': userid}
    await ChooseInventoryHandler(
        blacksmith_erase_select, userid, chatid, lang,
        inventory=custom_inventory,
        changing_filters=False,
        transmitted_data=transmitted_data
    ).start()

async def blacksmith_erase_select(item_dict: dict, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    from bot.modules.get_state import get_state
    state = await get_state(userid, chatid)
    if state:
        await state.clear()
    await open_blacksmith_menu(userid, chatid, lang)

    db_item = await Item.find_one(Item.owner_id == userid, Item.items_data == item_dict)
    if not db_item or not db_item.abilities.get('author'):
        await bot.send_message(chatid, t('blacksmith.error_find', lang))
        return

    # Count all copies of this item that have an author stamp
    all_matching = await Item.find(
        Item.owner_id == userid,
        {'items_data.item_id': db_item.item_id,
         'items_data.abilities.lvl': db_item.abilities.get('lvl', 0),
         'items_data.abilities.author': {'$exists': True}}
    ).to_list()
    total_named = sum(it.count for it in all_matching)
    total_named = min(total_named, 1000)

    prices = GAME_SETTINGS.get('blacksmith_prices', {})
    
    lvl = db_item.get_level()
    base_price = prices.get(str(lvl), 100 * lvl)
    per_item_price = base_price * 5
    item_name = get_name(db_item.item_id, lang, db_item.abilities)

    if total_named <= 1:
        # Only one copy — skip quantity selection
        erase_price = per_item_price
        text = t('blacksmith.erase_confirm', lang, item_name=item_name, price=erase_price)
        builder = InlineKeyboardBuilder()
        builder.button(text=t('blacksmith.erase_btn', lang),
                       callback_data=f"bs_erase:{db_item.id}:{erase_price}:1")
        builder.button(text=t('blacksmith.cancel_btn', lang), callback_data="bs_cancel")
        builder.adjust(2)
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=builder.as_markup())
    else:
        # Show quantity buttons
        builder = InlineKeyboardBuilder()
        for q in range(1, min(total_named, 10) + 1):
            builder.button(text=str(q), callback_data=f"bs_erq:{db_item.id}:{per_item_price}:{q}")
        if total_named > 10:
            builder.button(text=f"Max ({total_named})",
                           callback_data=f"bs_erq:{db_item.id}:{per_item_price}:{total_named}")
        builder.button(text=t('blacksmith.cancel_btn', lang), callback_data="bs_cancel")
        builder.adjust(5)
        text = t('blacksmith.erase_choose_qty', lang,
                 item_name=item_name, total=total_named, price_each=per_item_price)
        await bot.send_message(chatid, text, reply_markup=builder.as_markup(),
                                parse_mode='Markdown'
        )

@main_router.callback_query(IsPrivateChat(), F.data.startswith('bs_erq:'))
async def bs_erase_quantity_select(callback: CallbackQuery):
    """Confirm erase after quantity was selected."""
    if not callback.message:
        return
    await callback.message.delete()
    lang = await get_lang(callback.from_user.id)
    parts = callback.data.split(':')
    item_db_id, per_item_price, quantity = parts[1], int(parts[2]), int(parts[3])

    db_item = await Item.find_one(Item.id == ObjectId(item_db_id))
    if not db_item:
        await bot.send_message(callback.message.chat.id, t('blacksmith.error_find', lang))
        return

    erase_price = per_item_price * quantity
    item_name = get_name(db_item.item_id, lang, db_item.abilities)
    chatid = callback.message.chat.id

    text = t('blacksmith.erase_confirm', lang, item_name=item_name, price=erase_price)
    builder = InlineKeyboardBuilder()
    builder.button(text=t('blacksmith.erase_btn', lang),
                   callback_data=f"bs_erase:{db_item.id}:{erase_price}:{quantity}")
    builder.button(text=t('blacksmith.cancel_btn', lang), callback_data="bs_cancel")
    builder.adjust(2)
    await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=builder.as_markup())

@main_router.callback_query(IsPrivateChat(), F.data.startswith('bs_erase:'))
async def bs_erase_confirm(callback: CallbackQuery):
    if not callback.message:
        return
    await callback.message.delete()
    userid = callback.from_user.id
    chatid = callback.message.chat.id
    lang = await get_lang(userid)

    parts = callback.data.split(':')
    item_db_id = parts[1]
    erase_price = int(parts[2])
    quantity = int(parts[3]) if len(parts) > 3 else 1

    user = await User.find_one(User.userid == userid)
    if not user or user.coins < erase_price:
        coins = user.coins if user else 0
        await bot.send_message(chatid, t('blacksmith.no_coins', lang, price=erase_price, coins=coins))
        return

    db_item = await Item.find_one(Item.id == ObjectId(item_db_id))
    if not db_item:
        await bot.send_message(chatid, t('blacksmith.error_find', lang))
        return

    await user.remove_coins(erase_price)

    # Find all named copies of this item type (same item_id + same level) and erase author from `quantity` of them
    all_named = await Item.find(
        Item.owner_id == userid,
        {'items_data.item_id': db_item.item_id,
         'items_data.abilities.lvl': db_item.abilities.get('lvl', 0),
         'items_data.abilities.author': {'$exists': True}}
    ).to_list()

    erased = 0
    for it in all_named:
        if erased >= quantity:
            break
        to_erase = min(it.count, quantity - erased)
        if to_erase >= it.count:
            await it.update({'$unset': {'items_data.abilities.author': ''}})
        else:
            # Partial erase: split — erase `to_erase` copies and keep rest with author
            new_abilities = dict(it.abilities)
            del new_abilities['author']
            await Item.add(userid, it.item_id, to_erase, new_abilities)
            it.count -= to_erase
            await it.save()
        erased += to_erase

    reply_markup = await m(userid, 'blacksmith_menu', lang)
    await bot.send_message(chatid, t('blacksmith.erase_success', lang), reply_markup=reply_markup)
