from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from bot.modules.localization import get_lang, t
import uuid
from bot.exec import bot

async def inline_donat(inline_query: InlineQuery):
    userid = inline_query.from_user.id
    lang = await get_lang(userid)
    bot_user = await bot.get_me()
    
    message_text = t("inline.donat_menu_text", lang)
    button_text = t("inline.donat_menu_button", lang)
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=button_text, url=f"https://t.me/{bot_user.username}?start=donat")
    ]])
    
    results = [
        InlineQueryResultArticle(
            id=f"donat_{userid}_{uuid.uuid4().hex[:6]}",
            title=t("inline.donat_menu_title", lang),
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="Markdown"
            ),
            description=t("inline.donat_menu_desc", lang),
            thumbnail_url="https://raw.githubusercontent.com/Rimuwu/DinoGochi/main/images/remain/no_generate.png",
            reply_markup=reply_markup
        )
    ]
    
    await inline_query.answer(results, cache_time=1, is_personal=True)
