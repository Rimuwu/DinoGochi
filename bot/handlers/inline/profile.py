from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from bot.modules.user.user import user_info
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
import uuid
from bot.exec import bot

async def inline_profile(inline_query: InlineQuery):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    log(f"Received inline query for profile from user {userid}", prefix="InlineProfile", lvl=1)

    try:
        profile_text, _ = await user_info(userid, lang)
    except Exception as e:
        log(f"Error fetching user_info for self {userid}: {e}", prefix="InlineProfile", lvl=2)
        profile_text = f"👤 User Profile (ID: {userid})"

    bot_user = await bot.get_me()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
    ]])

    from bot.modules.localization import resolve_custom_emojis
    clean_text = resolve_custom_emojis(profile_text, html=False)

    avatar_url = avatar if (isinstance(avatar, str) and avatar.startswith("http")) else "https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_profile.png"
    message_text = f'<a href="{avatar_url}">&#8203;</a>{clean_text}'

    results = [
        InlineQueryResultArticle(
            id=f"profile<i>{userid}</i>{uuid.uuid4().hex[:6]}",
            title=t("inline.profile_menu_title", lang),
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    prefer_large_media=True,
                    show_above_text=True
                )
            ),
            description=t("inline.profile_menu_desc", lang),
            thumbnail_url=avatar_url,
            reply_markup=reply_markup
        )
    ]

    await inline_query.answer(results, cache_time=1, is_personal=True)
