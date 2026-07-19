import json
import re
from typing import Any, Optional
import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods.base import TelegramMethod
from aiogram.exceptions import TelegramBadRequest

from bot.config import conf

def _fsm_json_default(obj):
    """Fallback encoder for types RedisStorage can't serialize by default."""
    try:
        from bson import ObjectId
        if isinstance(obj, ObjectId):
            return str(obj)
    except ImportError:
        pass
    return str(obj)

def _fsm_json_dumps(data: dict) -> str:
    return json.dumps(data, default=_fsm_json_default)

class CustomBot(Bot):
    async def __call__(
        self,
        method: TelegramMethod,
        request_timeout: Optional[int] = None,
    ) -> Any:
        # Intercept and convert markdown to html
        from bot.modules.data_format import convert_markdown_to_html
        
        # Helper check to see if text/caption has custom emoji syntax
        def has_custom_emoji(val: Any) -> bool:
            return isinstance(val, str) and "![" in val and "tg://emoji?id=" in val

        # 1. Check if method has parse_mode and either text or caption
        parse_mode = getattr(method, "parse_mode", None)
        # parse_mode can be str, None, or aiogram's Default sentinel — normalize safely
        parse_mode_upper = parse_mode.upper() if isinstance(parse_mode, str) else ""
        if parse_mode_upper != "HTML":
            should_convert = parse_mode_upper in ("MARKDOWN", "MARKDOWNV2")
            # If SendMessage or EditMessageText or similar
            if hasattr(method, "text"):
                text = getattr(method, "text", None)
                if should_convert or has_custom_emoji(text):
                    if isinstance(text, str):
                        method.text = convert_markdown_to_html(text)
                        method.parse_mode = "HTML"
            # If SendPhoto, SendVideo, EditMessageCaption or similar
            elif hasattr(method, "caption"):
                caption = getattr(method, "caption", None)
                if should_convert or has_custom_emoji(caption):
                    if isinstance(caption, str):
                        method.caption = convert_markdown_to_html(caption)
                        method.parse_mode = "HTML"
        else:
            # If parse_mode is already HTML, we still want to convert custom emojis from Markdown format to HTML tg-emoji tags
            if hasattr(method, "text"):
                text = getattr(method, "text", None)
                if isinstance(text, str) and has_custom_emoji(text):
                    method.text = re.sub(
                        r'!\[([^\]]*)\]\(tg://emoji\?id=(\d+)\)',
                        r'<tg-emoji emoji-id="\2">\1</tg-emoji>',
                        text
                    )
            elif hasattr(method, "caption"):
                caption = getattr(method, "caption", None)
                if isinstance(caption, str) and has_custom_emoji(caption):
                    method.caption = re.sub(
                        r'!\[([^\]]*)\]\(tg://emoji\?id=(\d+)\)',
                        r'<tg-emoji emoji-id="\2">\1</tg-emoji>',
                        caption
                    )

        # 2. Check if method is EditMessageMedia
        if hasattr(method, "media"):
            media = getattr(method, "media", None)
            if media:
                media_parse_mode = getattr(media, "parse_mode", None)
                media_parse_mode_upper = media_parse_mode.upper() if isinstance(media_parse_mode, str) else ""
                if media_parse_mode_upper != "HTML":
                    media_caption = getattr(media, "caption", None)
                    if media_parse_mode_upper in ("MARKDOWN", "MARKDOWNV2") or has_custom_emoji(media_caption):
                        if isinstance(media_caption, str):
                            new_caption = convert_markdown_to_html(media_caption)
                            if hasattr(media, "model_copy"):
                                method.media = media.model_copy(update={"caption": new_caption, "parse_mode": "HTML"})
                            else:
                                method.media = media.copy(update={"caption": new_caption, "parse_mode": "HTML"})
                else:
                    media_caption = getattr(media, "caption", None)
                    if isinstance(media_caption, str) and has_custom_emoji(media_caption):
                        new_caption = re.sub(
                            r'!\[([^\]]*)\]\(tg://emoji\?id=(\d+)\)',
                            r'<tg-emoji emoji-id="\2">\1</tg-emoji>',
                            media_caption
                        )
                        if hasattr(media, "model_copy"):
                            method.media = media.model_copy(update={"caption": new_caption})
                        else:
                            method.media = media.copy(update={"caption": new_caption})

        try:
            return await super().__call__(method, request_timeout)
        except TelegramBadRequest as e:
            err_msg = str(e)
            if any(ign in err_msg for ign in [
                "message to delete not found",
                "query is too old",
                "query ID is invalid",
                "message is not modified",
                "canceled by new edit message request"
            ]):
                return None
            
            if any(err in err_msg for err in ["DOCUMENT_INVALID", "CUSTOM_EMOJI_ID_INVALID", "can't parse entities"]):
                from bot.modules.logs import log
                log(f"TelegramBadRequest caught ({err_msg}), retrying with fallback formatting...", lvl=2)

                def _clean_method(m, strip_html=False):
                    def clean_str(s: str) -> str:
                        if strip_html:
                            return re.sub(r'<[^>]+>', '', s)
                        return re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', s)

                    if hasattr(m, "text") and isinstance(getattr(m, "text", None), str):
                        m.text = clean_str(m.text)
                        if strip_html and hasattr(m, "parse_mode"):
                            m.parse_mode = None

                    if hasattr(m, "caption") and isinstance(getattr(m, "caption", None), str):
                        m.caption = clean_str(m.caption)
                        if strip_html and hasattr(m, "parse_mode"):
                            m.parse_mode = None

                    if hasattr(m, "media") and m.media:
                        media_items = m.media if isinstance(m.media, list) else [m.media]
                        for item in media_items:
                            if hasattr(item, "caption") and isinstance(getattr(item, "caption", None), str):
                                item.caption = clean_str(item.caption)
                                if strip_html and hasattr(item, "parse_mode"):
                                    item.parse_mode = None

                # 1. Retry stripping custom emoji tags
                try:
                    _clean_method(method, strip_html=False)
                    return await super().__call__(method, request_timeout)
                except TelegramBadRequest:
                    pass

                # 2. Retry stripping all HTML formatting
                try:
                    _clean_method(method, strip_html=True)
                    return await super().__call__(method, request_timeout)
                except Exception as final_e:
                    log(f"Final fallback failed for Telegram call: {final_e}", lvl=3)
                    raise e
            raise

bot = CustomBot(conf.bot_token)
_fsm_redis = aioredis.from_url(
    conf.redis_url,
    decode_responses=False,  # RedisStorage requires bytes, not str
    socket_timeout=5.0,
    max_connections=200
)
STORAGE = RedisStorage(redis=_fsm_redis, json_dumps=_fsm_json_dumps)
dp = Dispatcher(storage=STORAGE)

main_router = Router(name='MainRouter')
dp.include_router(main_router)
