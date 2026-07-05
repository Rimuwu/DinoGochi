from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from bot.models.user import User
from bot.modules.localization import get_lang, get_data, t
from bot.handlers.main_menu.dino_profile import get_dino_profile_text
from bot.const import DINOS
from bot.exec import bot
from bot.modules.logs import log
import uuid

async def inline_dino(inline_query: InlineQuery, search_query: str = ""):
    userid = inline_query.from_user.id
    log(f"Received inline query from user {userid} with search_query: '{search_query}'", prefix="InlineDino", lvl=1)
    
    lang = await get_lang(userid)
    user = await User().create(userid)
    dinos = await user.get_dinos()
    log(f"User {userid} has {len(dinos)} total dinosaurs", prefix="InlineDino", lvl=1)

    if search_query:
        # Filter dinosaurs matching the search query (case-insensitive substring)
        matching_dinos = [d for d in dinos if search_query.lower() in d.name.lower()]
    else:
        matching_dinos = dinos

    # Limit to maximum 10 dinosaurs to ensure fast rendering
    matching_dinos = matching_dinos[:10]

    bot_user = await bot.get_me()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
    ]])

    results = []
    for dino in matching_dinos:
        title = f"🦕 {dino.name}"
        
        rare_labels = get_data('rare', lang)
        rare_label = rare_labels.get(dino.quality, [dino.quality, dino.quality])[1]
        
        description = t(
            "inline.dino_desc",
            lang,
            rare_label=rare_label,
            heal=dino.stats.get('heal', 0),
            energy=dino.stats.get('energy', 0)
        )
        
        # Family sprite for the search result list thumbnail
        dino_data = DINOS['elements'].get(str(dino.data_id))
        if dino_data and 'image' in dino_data:
            sprite_url = f"https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/{dino_data['image']}"
        else:
            sprite_url = "https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/no_generate.png"
            
        # Get profile text to send immediately
        try:
            profile_text = await get_dino_profile_text(userid, dino, lang)
        except Exception:
            profile_text = dino.name

        # Initial message contains the standard placeholder image (no_generate.png) as link preview
        placeholder_url = "https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/no_generate.png"
        message_text = f"[\u200b]({placeholder_url}){profile_text}"

        results.append(
            InlineQueryResultArticle(
                id=f"dino_{dino.id}_{uuid.uuid4().hex[:6]}",
                title=title,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="Markdown",
                    link_preview_options=LinkPreviewOptions(
                        is_disabled=False,
                        prefer_large_media=True,
                        show_above_text=True
                    )
                ),
                description=description,
                thumbnail_url=sprite_url,
                reply_markup=reply_markup
            )
        )

    # If no dinosaurs found, fallback to an article result
    if not results:
        no_dinos_title = t("p_profile.no_dinos_yet", lang, default="No dinosaurs found")
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=no_dinos_title,
                input_message_content=InputTextMessageContent(
                    message_text=no_dinos_title
                ),
                description="Create or hatch a dinosaur first!"
            )
        )

    log(f"Answering inline query with {len(results)} results", prefix="InlineDino", lvl=1)
    await inline_query.answer(results, cache_time=1, is_personal=True)
