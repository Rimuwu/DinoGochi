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
            if "message to delete not found" in err_msg or "query is too old" in err_msg or "query ID is invalid" in err_msg or "message is not modified" in err_msg:
                return None
            raise

bot = CustomBot(conf.bot_token)
_fsm_redis = aioredis.from_url(
    conf.redis_url,
    decode_responses=False,  # RedisStorage requires bytes, not str
    socket_timeout=5.0
)
STORAGE = RedisStorage(redis=_fsm_redis, json_dumps=_fsm_json_dumps)
dp = Dispatcher(storage=STORAGE)

main_router = Router(name='MainRouter')
dp.include_router(main_router)
