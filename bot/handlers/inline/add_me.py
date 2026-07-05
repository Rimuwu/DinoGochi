from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from bot.modules.localization import get_lang, t
from bot.models.user import User
import uuid

async def inline_add_me(inline_query: InlineQuery):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    
    message_text = t("add_me", lang, userid=userid, username=user.name)
    button_text = t("inline.add_me_menu_button", lang)
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=button_text, callback_data=f"send_request {userid}")
    ]])
    
    results = [
        InlineQueryResultArticle(
            id=f"add_me_{userid}_{uuid.uuid4().hex[:6]}",
            title=t("inline.add_me_menu_title", lang),
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="HTML"
            ),
            description=t("inline.add_me_menu_desc", lang),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/inline/inline_friend.png",
            reply_markup=reply_markup
        )
    ]
    
    await inline_query.answer(results, cache_time=1, is_personal=True)
