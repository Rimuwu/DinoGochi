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
        profile_text, avatar = await user_info(userid, lang)
    except Exception as e:
        log(f"Error fetching user_info for self {userid}: {e}", prefix="InlineProfile", lvl=2)
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
                    log(f"Error fetching file path for avatar {avatar}: {e}", prefix="InlineProfile", lvl=2)

    message_text = f"[\u200b]({avatar_url}){profile_text}"

    bot_user = await bot.get_me()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
    ]])

    results = [
        InlineQueryResultArticle(
            id=f"profile_{userid}_{uuid.uuid4().hex[:6]}",
            title=t("inline.profile_menu_title", lang),
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="Markdown",
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
