from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from bot.models.market import Product
from bot.modules.items.item import get_name
from bot.modules.market.market import product_ui
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
import uuid
from bot.exec import bot

async def inline_product(inline_query: InlineQuery, search_query: str = ""):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    log(f"Received inline query for products from user {userid} with search_query: '{search_query}'", prefix="InlineProduct", lvl=1)

    # Fetch active products belonging to the user
    user_products = await Product.find(Product.owner_id == userid).to_list()

    matching_products = []
    for product in user_products:
        # Determine items names to match search query
        items_id = []
        for i in product.items:
            if 'item_id' in i:
                items_id.append(i['item_id'])
        
        item_names = [get_name(iid, lang, custom_emoji=False) for iid in items_id]
        product_display_name = ", ".join(item_names) if item_names else f"Product {product.alt_id}"
        
        if search_query:
            if search_query.lower() in product_display_name.lower() or search_query.lower() in product.alt_id.lower():
                matching_products.append((product, product_display_name))
        else:
            matching_products.append((product, product_display_name))

    matching_products = matching_products[:10]

    bot_user = await bot.get_me()
    results = []
    
    for product, display_name in matching_products:
        try:
            m_text, _ = await product_ui(lang, product.id, False, html=False)
            import re
            m_text = re.sub(r'!\[(.*?)\]\(tg://emoji\?id=\d+\)', r'\1', m_text)
            from bot.modules.data_format import md_to_html
            m_text = md_to_html(m_text)
        except Exception as e:
            log(f"Error formatting product UI for {product.alt_id}: {e}", prefix="InlineProduct", lvl=2)
            m_text = f"📦 {display_name} (Code: {product.alt_id})"

        # Button linking directly to start the bot with product parameter
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("product_ui.buttons.buy", lang, default="🛍️ Buy / View"), url=f"https://t.me/{bot_user.username}?start={product.alt_id}")
        ]])

        # If there are items, we can use the first item's image as the thumbnail
        image_url = "https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/no_generate.png"
        if product.items:
            first_item = product.items[0]
            from bot.modules.items.item import ITEMS
            data_item = ITEMS.get(first_item.get('item_id', ''), {})
            if data_item and 'image' in data_item and data_item['image']:
                icon_val = data_item['image'].get('icon', 'null') if isinstance(data_item['image'], dict) else data_item['image']
                image_url = f"https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/items/{icon_val}.png"

        results.append(
            InlineQueryResultArticle(
                id=f"product<i>{product.alt_id}</i>{uuid.uuid4().hex[:6]}",
                title=f"📦 {display_name}",
                input_message_content=InputTextMessageContent(
                    message_text=m_text,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                ),
                description=f"Type: {product.type} | Code: {product.alt_id}",
                thumbnail_url=image_url,
                reply_markup=reply_markup
            )
        )

    # Fallback if no products found
    if not results:
        no_products_title = t("p_profile.no_products_yet", lang)
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=no_products_title,
                input_message_content=InputTextMessageContent(
                    message_text=no_products_title
                ),
                description=no_products_title
            )
        )

    await inline_query.answer(results, cache_time=1, is_personal=True)
