from aiogram.types import LinkPreviewOptions
from aiogram import F
from aiogram.types import InlineQuery
from bot.exec import main_router, bot
from bot.handlers.inline.dino import inline_dino
from bot.handlers.inline.item import inline_item

from bot.handlers.inline.friend import inline_friend
from bot.handlers.inline.add_me import inline_add_me
from bot.handlers.inline.donat import inline_donat
from bot.handlers.inline.product import inline_product
from bot.handlers.inline.profile import inline_profile

# Handler 1: Matches queries that start with "dino " or are exactly "dino"
@main_router.inline_query(F.query.startswith("dino ") | (F.query == "dino"))
async def inline_command_dino(inline_query: InlineQuery):
    # Parse the search query (part after "dino ")
    query_text = inline_query.query
    if query_text.startswith("dino "):
        search_query = query_text[5:].strip()
    else:
        search_query = ""
    await inline_dino(inline_query, search_query)

# Handler 2: Matches queries that start with "item " or are exactly "item"
@main_router.inline_query(F.query.startswith("item ") | (F.query == "item"))
async def inline_command_item(inline_query: InlineQuery):
    # Parse the search query (part after "item ")
    query_text = inline_query.query
    if query_text.startswith("item "):
        search_query = query_text[5:].strip()
    else:
        search_query = ""
    await inline_item(inline_query, search_query)

# Handler 3: Matches queries that start with "friend " or "friends " or are exactly "friend" / "friends"
@main_router.inline_query(F.query.startswith("friend ") | (F.query == "friend") | F.query.startswith("friends ") | (F.query == "friends"))
async def inline_command_friend(inline_query: InlineQuery):
    query_text = inline_query.query
    if query_text.startswith("friends "):
        search_query = query_text[8:].strip()
    elif query_text.startswith("friend "):
        search_query = query_text[7:].strip()
    else:
        search_query = ""
    await inline_friend(inline_query, search_query)

# Handler for add_me: matches exactly "add_me"
@main_router.inline_query(F.query == "add_me")
async def inline_command_add_me(inline_query: InlineQuery):
    await inline_add_me(inline_query)

# Handler for donat: matches exactly "donat"
@main_router.inline_query(F.query == "donat")
async def inline_command_donat(inline_query: InlineQuery):
    await inline_donat(inline_query)

# Handler for product: matches "product " or exactly "product"
@main_router.inline_query(F.query.startswith("product ") | (F.query == "product"))
async def inline_command_product(inline_query: InlineQuery):
    query_text = inline_query.query
    if query_text.startswith("product "):
        search_query = query_text[8:].strip()
    else:
        search_query = ""
    await inline_product(inline_query, search_query)

# Handler for profile: matches exactly "profile"
@main_router.inline_query(F.query == "profile")
async def inline_command_profile(inline_query: InlineQuery):
    await inline_profile(inline_query)

# Handler 4: Matches empty query to display available commands
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from bot.modules.localization import get_lang, t
from bot.models.user import User
from bot.modules.user.user import user_info
from bot.modules.logs import log

@main_router.inline_query(F.query == "")
async def inline_empty_query(inline_query: InlineQuery):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    bot_user = await bot.get_me()
    user = await User().create(userid)

    # Fetch self profile information for direct card rendering
    try:
        profile_text, avatar = await user_info(userid, lang)
    except Exception as e:
        log(f"Error fetching user_info for self {userid}: {e}", prefix="InlineEmptyQuery", lvl=2)
        profile_text = f"👤 User Profile (ID: {userid})"
        avatar = None

    avatar_url = "https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_friend.png"
    if avatar:
        if isinstance(avatar, str):
            if avatar.startswith("http") or avatar.startswith("tg://"):
                avatar_url = avatar
            else:
                try:
                    file_info = await bot.get_file(avatar)
                    avatar_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
                except Exception as e:
                    log(f"Error fetching file path for avatar {avatar}: {e}", prefix="InlineEmptyQuery", lvl=2)
    
    results = [
        InlineQueryResultArticle(
            id="menu_dino",
            title=t("inline.dino_menu_title", lang),
            description=t("inline.dino_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=t("inline.dino_menu_text", lang, bot_username=bot_user.username)
            ),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_dino.png",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("inline.dino_menu_button", lang), switch_inline_query_current_chat="dino ")
            ]])
        ),
        InlineQueryResultArticle(
            id="menu_item",
            title=t("inline.item_menu_title", lang),
            description=t("inline.item_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=t("inline.item_menu_text", lang, bot_username=bot_user.username)
            ),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_item.png",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("inline.item_menu_button", lang), switch_inline_query_current_chat="item ")
            ]])
        ),
        InlineQueryResultArticle(
            id="menu_friend",
            title=t("inline.friend_menu_title", lang),
            description=t("inline.friend_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=t("inline.friend_menu_text", lang, bot_username=bot_user.username)
            ),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_friend.png",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("inline.friend_menu_button", lang), switch_inline_query_current_chat="friend ")
            ]])
        ),
        InlineQueryResultArticle(
            id="menu_add_me",
            title=t("inline.add_me_menu_title", lang),
            description=t("inline.add_me_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=t("add_me", lang, userid=userid, username=user.name),
                parse_mode="HTML"
            ),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_friend.png",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("inline.add_me_menu_button", lang), callback_data=f"send_request {userid}")
            ]])
        ),
        InlineQueryResultArticle(
            id="menu_donat",
            title=t("inline.donat_menu_title", lang),
            description=t("inline.donat_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=t("inline.donat_menu_text", lang),
                parse_mode="Markdown"
            ),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_donat.png",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("inline.donat_menu_button", lang), url=f"https://t.me/{bot_user.username}?start=donat")
            ]])
        ),
        InlineQueryResultArticle(
            id="menu_product",
            title=t("inline.product_menu_title", lang),
            description=t("inline.product_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=t("inline.product_menu_text", lang, bot_username=bot_user.username)
            ),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_product.png",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("inline.product_menu_button", lang), switch_inline_query_current_chat="product ")
            ]])
        ),
        InlineQueryResultArticle(
            id="menu_profile",
            title=t("inline.profile_menu_title", lang),
            description=t("inline.profile_menu_desc", lang),
            input_message_content=InputTextMessageContent(
                message_text=f"[\u200b]({avatar_url}){profile_text}",
                parse_mode="Markdown",
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    prefer_large_media=True,
                    show_above_text=True
                )
            ),
            thumbnail_url=avatar_url,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
            ]])
        )
    ]
    
    await inline_query.answer(results, cache_time=1, is_personal=True)

# Handler 4: Matches all other queries specifically for direct dinosaur search
@main_router.inline_query()
async def inline_direct_dino(inline_query: InlineQuery):
    query_text = inline_query.query.strip()
    await inline_dino(inline_query, query_text)

# Chosen inline result handler to generate, upload image and edit sent message on click
from aiogram.types import ChosenInlineResult, InputMediaPhoto
from bot.models.dinosaur import Dino
from bot.handlers.main_menu.dino_profile import get_dino_profile_text
from bot.models.user import User
from bot.modules.logs import log
import aiohttp
from bson import ObjectId
import traceback

@main_router.chosen_inline_result()
async def chosen_inline_dino(chosen_result: ChosenInlineResult):
    result_id = chosen_result.result_id
    inline_message_id = chosen_result.inline_message_id
    if not inline_message_id:
        log("Chosen inline result received but inline_message_id is missing (requires reply_markup to be present)", prefix="ChosenInline", lvl=2)
        return

    userid = chosen_result.from_user.id
    lang = await get_lang(userid)

    # Handle profile and friend avatar uploads asynchronously
    if result_id.startswith("profile_") or result_id.startswith("friend_") or result_id == "menu_profile":
        if result_id.startswith("friend_"):
            target_id = int(result_id.split('_')[1])
        else:
            target_id = userid

        log(f"Chosen inline result received for profile/friend. Target: {target_id}", prefix="ChosenInline", lvl=1)
        try:
            profile_text, avatar = await user_info(target_id, lang)
            if avatar:
                if isinstance(avatar, str) and not (avatar.startswith("http") or avatar.startswith("tg://")):
                    file_info = await bot.get_file(avatar)
                    from io import BytesIO
                    file_bytes = BytesIO()
                    await bot.download(file_info, destination=file_bytes)
                    image_data = file_bytes.getvalue()
                    
                    data = aiohttp.FormData()
                    data.add_field('reqtype', 'fileupload')
                    data.add_field('time', '72h')
                    data.add_field('fileToUpload', image_data, filename='avatar.jpg', content_type='image/jpeg')
                    
                    catbox_url = None
                    async with aiohttp.ClientSession() as session:
                        async with session.post('https://litterbox.catbox.moe/resources/internals/api.php', data=data, timeout=10.0) as resp:
                            if resp.status == 200:
                                res_text = await resp.text()
                                res_text = res_text.strip()
                                if res_text.startswith("https://litterbox.catbox.moe/") or res_text.startswith("https://litter.catbox.moe/"):
                                    catbox_url = res_text
                    
                    if catbox_url:
                        bot_user = await bot.get_me()
                        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
                        ]])
                        await bot.edit_message_text(
                            text=f"[\u200b]({catbox_url}){profile_text}",
                            inline_message_id=inline_message_id,
                            parse_mode="Markdown",
                            link_preview_options=LinkPreviewOptions(
                                is_disabled=False,
                                prefer_large_media=True,
                                show_above_text=True
                            ),
                            reply_markup=reply_markup
                        )
        except Exception as e:
            log(f"Error handling chosen profile/friend avatar: {e}", prefix="ChosenInline", lvl=2)
        return

    if not result_id.startswith("dino_"):
        return
        
    # Extract the ObjectID string by splitting by underscore
    dino_id_str = result_id[5:].split('_')[0]
        
    userid = chosen_result.from_user.id
    lang = await get_lang(userid)
    
    log(f"Chosen inline result received for dino {dino_id_str} from user {userid}", prefix="ChosenInline", lvl=1)
    
    try:
        dino = await Dino.find_one(Dino.id == ObjectId(dino_id_str))
    except Exception as parse_err:
        log(f"Failed to parse ObjectID '{dino_id_str}': {parse_err}", prefix="ChosenInline", lvl=3)
        return

    if not dino:
        log(f"Dino {dino_id_str} not found in database", prefix="ChosenInline", lvl=2)
        return

    try:
        user = await User().create(userid)
        # Generate the Pillow image
        log(f"Generating image for chosen dino {dino.name}", prefix="ChosenInline", lvl=1)
        image = await dino.image(user.settings.get('profile_view', 1))
        image_bytes = image.data
        log(f"Pillow image generated ({len(image_bytes)} bytes)", prefix="ChosenInline", lvl=1)

        # Upload image anonymously to Litterbox (Catbox)
        log(f"Uploading image to Litterbox...", prefix="ChosenInline", lvl=1)
        catbox_url = None
        data = aiohttp.FormData()
        data.add_field('reqtype', 'fileupload')
        data.add_field('time', '72h')
        data.add_field('fileToUpload', image_bytes, filename='file.jpg', content_type='image/jpeg')
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://litterbox.catbox.moe/resources/internals/api.php', data=data, timeout=10.0) as resp:
                log(f"Litterbox response status: {resp.status}", prefix="ChosenInline", lvl=1)
                if resp.status == 200:
                    res_text = await resp.text()
                    res_text = res_text.strip()
                    if res_text.startswith("https://litterbox.catbox.moe/") or res_text.startswith("https://litter.catbox.moe/"):
                        catbox_url = res_text
                        log(f"Uploaded successfully to Litterbox: {catbox_url}", prefix="ChosenInline", lvl=1)
                    else:
                        log(f"Litterbox upload returned unexpected text: {res_text}", prefix="ChosenInline", lvl=2)
                else:
                    resp_text = await resp.text()
                    log(f"Litterbox upload failed with status {resp.status}. Response: {resp_text}", prefix="ChosenInline", lvl=2)

        # Get profile text
        profile_text = await get_dino_profile_text(userid, dino, lang)

        # Create inline keyboard for return menu
        bot_user = await bot.get_me()
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
        ]])

        if catbox_url:
            log(f"Editing message {inline_message_id} text with new image preview", prefix="ChosenInline", lvl=1)
            try:
                # Edit the text to replace the placeholder link preview with the new custom image link preview
                await bot.edit_message_text(
                    text=f"[\u200b]({catbox_url}){profile_text}",
                    inline_message_id=inline_message_id,
                    parse_mode="Markdown",
                    link_preview_options=LinkPreviewOptions(
                        is_disabled=False,
                        prefer_large_media=True,
                        show_above_text=True
                    ),
                    reply_markup=reply_markup
                )
            except Exception as edit_err:
                log(f"Failed to edit message with new image: {edit_err}", prefix="ChosenInline", lvl=2)
        else:
            log(f"Litterbox upload failed, keeping original placeholder message", prefix="ChosenInline", lvl=1)
            
    except Exception as e:
        tb = traceback.format_exc()
        log(f"Error handling chosen inline dino:\n{tb}", prefix="ChosenInline", lvl=3)
