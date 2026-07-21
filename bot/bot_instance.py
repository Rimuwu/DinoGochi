from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
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
        # Resolve custom emojis in text or caption if present
        from bot.modules.localization import resolve_custom_emojis

        # 1. Check text or caption
        if hasattr(method, "text"):
            text = getattr(method, "text", None)
            if isinstance(text, str) and ("{" in text or "![" in text):
                method.text = resolve_custom_emojis(text)

        if hasattr(method, "caption"):
            caption = getattr(method, "caption", None)
            if isinstance(caption, str) and ("{" in caption or "![" in caption):
                method.caption = resolve_custom_emojis(caption)

        # 2. Check if method contains media with caption
        if hasattr(method, "media"):
            media = getattr(method, "media", None)
            if media:
                if isinstance(media, list):
                    new_list = []
                    for item in media:
                        if hasattr(item, "caption") and isinstance(getattr(item, "caption", None), str):
                            new_cap = resolve_custom_emojis(item.caption) if ("{" in item.caption or "![" in item.caption) else item.caption
                            u = {"caption": new_cap, "parse_mode": "HTML"}
                            if hasattr(item, "model_copy"):
                                item = item.model_copy(update=u)
                            elif hasattr(item, "copy"):
                                item = item.copy(update=u)
                        new_list.append(item)
                    method.media = new_list
                elif hasattr(media, "caption") and isinstance(getattr(media, "caption", None), str):
                    new_caption = resolve_custom_emojis(media.caption) if ("{" in media.caption or "![" in media.caption) else media.caption
                    u = {"caption": new_caption, "parse_mode": "HTML"}
                    if hasattr(media, "model_copy"):
                        method.media = media.model_copy(update=u)
                    elif hasattr(media, "copy"):
                        method.media = media.copy(update=u)

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

                    updates = {}
                    if hasattr(m, "text") and isinstance(getattr(m, "text", None), str):
                        updates["text"] = clean_str(m.text)
                        if strip_html and hasattr(m, "parse_mode"):
                            updates["parse_mode"] = None

                    if hasattr(m, "caption") and isinstance(getattr(m, "caption", None), str):
                        updates["caption"] = clean_str(m.caption)
                        if strip_html and hasattr(m, "parse_mode"):
                            updates["parse_mode"] = None

                    if hasattr(m, "media") and m.media:
                        if isinstance(m.media, list):
                            new_list = []
                            for item in m.media:
                                if hasattr(item, "caption") and isinstance(getattr(item, "caption", None), str):
                                    icap = clean_str(item.caption)
                                    u = {"caption": icap}
                                    if strip_html and hasattr(item, "parse_mode"):
                                        u["parse_mode"] = None
                                    if hasattr(item, "model_copy"):
                                        item = item.model_copy(update=u)
                                    elif hasattr(item, "copy"):
                                        item = item.copy(update=u)
                                new_list.append(item)
                            updates["media"] = new_list
                        else:
                            item = m.media
                            if hasattr(item, "caption") and isinstance(getattr(item, "caption", None), str):
                                icap = clean_str(item.caption)
                                u = {"caption": icap}
                                if strip_html and hasattr(item, "parse_mode"):
                                    u["parse_mode"] = None
                                if hasattr(item, "model_copy"):
                                    new_item = item.model_copy(update=u)
                                elif hasattr(item, "copy"):
                                    new_item = item.copy(update=u)
                                else:
                                    new_item = item
                                updates["media"] = new_item

                    if updates:
                        if hasattr(m, "model_copy"):
                            return m.model_copy(update=updates)
                        elif hasattr(m, "copy"):
                            return m.copy(update=updates)
                    return m

                # 1. Retry stripping custom emoji tags
                try:
                    clean_m = _clean_method(method, strip_html=False)
                    return await super().__call__(clean_m, request_timeout)
                except TelegramBadRequest:
                    pass

                # 2. Retry stripping all HTML formatting
                try:
                    clean_m = _clean_method(method, strip_html=True)
                    return await super().__call__(clean_m, request_timeout)
                except Exception as final_e:
                    log(f"Final fallback failed for Telegram call: {final_e}", lvl=3)
                    raise e
            raise

bot = CustomBot(conf.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
