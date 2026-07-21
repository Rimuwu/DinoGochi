from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from bot.modules.items.item import ITEMS, get_name, item_info
from bot.modules.localization import get_lang, get_data, t
from bot.modules.logs import log
import uuid
from bot.exec import bot

from bot.models.items import Item

async def inline_item(inline_query: InlineQuery, search_query: str = ""):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    log(f"Received inline query for items from user {userid} with search_query: '{search_query}'", prefix="InlineItem", lvl=1)

    # Fetch items from the user's inventory
    user_items = await Item.find(Item.owner_id == userid).to_list()

    matching_items = []
    
    # Filter items from the user's inventory
    for item in user_items:
        item_id = item.item_id
        localized_name = get_name(item_id, lang, custom_emoji=False)
        if search_query:
            if search_query.lower() in localized_name.lower() or search_query.lower() in item_id.lower():
                matching_items.append(item)
        else:
            matching_items.append(item)

    # Limit to maximum 10 items for fast rendering
    matching_items = matching_items[:10]

    bot_user = await bot.get_me()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
    ]])

    results = []
    for item in matching_items:
        item_id = item.item_id
        data_item = ITEMS.get(item_id, {})
        localized_name = get_name(item_id, lang, custom_emoji=False)
        
        # Prepare direct image link from GitHub repo
        if 'image' in data_item and data_item['image']:
            icon_val = data_item['image'].get('icon', 'null') if isinstance(data_item['image'], dict) else data_item['image']
            image_url = f"https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/items/{icon_val}.png"
        else:
            image_url = "https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/no_generate.png"

        try:
            # Generate the item info text
            profile_text, _ = await item_info(item.items_data, lang, html=True)
        except Exception as e:
            log(f"Error rendering item info for {item_id}: {e}", prefix="InlineItem", lvl=2)
            profile_text = localized_name

        message_text = profile_text
        
        # Localized rank and type description
        rank_val = data_item.get('rank', 'common')
        type_val = data_item.get('type', 'material')
        
        if 'class' in data_item:
            type_loc = data_item['class']
        else:
            type_loc = type_val
 
        loc_d = get_data('item_info', lang)
        if isinstance(loc_d, dict):
            rank_name = loc_d.get('rank', {}).get(rank_val, rank_val.capitalize())
            type_info_dict = loc_d.get('type_info', {}).get(type_loc)
            if type_info_dict and 'type_name' in type_info_dict:
                type_name = type_info_dict['type_name']
            else:
                type_name = type_loc.capitalize()
        else:
            rank_name = rank_val.capitalize()
            type_name = type_val.capitalize()

        desc_text = t("inline.item_desc", lang, rank=rank_name, type=type_name)

        results.append(
            InlineQueryResultArticle(
                id=f"item_{item.id}",
                title=f"🎒 {localized_name}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    link_preview_options=LinkPreviewOptions(
                        is_disabled=True
                    )
                ),
                description=desc_text,
                thumbnail_url=image_url,
                reply_markup=reply_markup
            )
        )

    # Fallback if no items found
    if not results:
        no_items_title = t("p_profile.no_items_yet", lang)
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=no_items_title,
                input_message_content=InputTextMessageContent(
                    message_text=no_items_title
                ),
                description=no_items_title
            )
        )

    await inline_query.answer(results, cache_time=1, is_personal=True)
