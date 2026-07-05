from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from bot.modules.user.friends import get_frineds, get_friend_data
from bot.modules.user.user import user_info
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
import uuid
from bot.exec import bot

async def inline_friend(inline_query: InlineQuery, search_query: str = ""):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    log(f"Received inline query for friends from user {userid} with search_query: '{search_query}'", prefix="InlineFriend", lvl=1)

    friends_data = await get_frineds(userid)
    friend_ids = friends_data.get('friends', [])

    matching_friends = []
    for friend_id in friend_ids:
        # Get friend details (customized name/name from DB or Telegram)
        f_data = await get_friend_data(friend_id, userid)
        name = f_data.get('name', f"User {friend_id}")
        if search_query:
            if search_query.lower() in name.lower() or search_query.lower() in str(friend_id):
                matching_friends.append((friend_id, name))
        else:
            matching_friends.append((friend_id, name))

    matching_friends = matching_friends[:10]

    bot_user = await bot.get_me()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🦖 DinoGochi", url=f"https://t.me/{bot_user.username}")
    ]])

    results = []
    for friend_id, name in matching_friends:
        try:
            profile_text, avatar = await user_info(friend_id, lang)
        except Exception as e:
            log(f"Error fetching user_info for friend {friend_id}: {e}", prefix="InlineFriend", lvl=2)
            profile_text = f"👥 {name} (ID: {friend_id})"
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
                        log(f"Error fetching file path for avatar {avatar}: {e}", prefix="InlineFriend", lvl=2)

        message_text = f"[\u200b]({avatar_url}){profile_text}"

        results.append(
            InlineQueryResultArticle(
                id=f"friend_{friend_id}_{uuid.uuid4().hex[:6]}",
                title=f"👤 {name}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="Markdown",
                    link_preview_options=LinkPreviewOptions(
                        is_disabled=False,
                        prefer_large_media=True,
                        show_above_text=True
                    )
                ),
                description=f"ID: {friend_id}",
                thumbnail_url=avatar_url,
                reply_markup=reply_markup
            )
        )

    # Fallback if no friends found
    if not results:
        no_friends_title = t("p_profile.no_friends_yet", lang)
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=no_friends_title,
                input_message_content=InputTextMessageContent(
                    message_text=no_friends_title
                ),
                description=no_friends_title
            )
        )

    await inline_query.answer(results, cache_time=1, is_personal=True)
