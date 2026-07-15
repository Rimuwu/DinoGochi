from time import time
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from bot.modules.logs import log

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        start_time = time()
        
        user_id = "unknown"
        if hasattr(event, "from_user") and event.from_user:
            user_id = str(event.from_user.id)
            
        event_info = ""
        if isinstance(event, Message):
            event_info = f"msg='{event.text}'" if event.text else "msg=[Media/Other]"
        elif isinstance(event, CallbackQuery):
            event_info = f"cb='{event.data}'"
            
        handler_name = "unknown"
        if "handler" in data:
            h_obj = data["handler"]
            if hasattr(h_obj, "callback"):
                handler_name = f"{h_obj.callback.__module__}.{h_obj.callback.__name__}"
            else:
                handler_name = str(h_obj)

        from bot.modules.monitor import MonitoredCoroWrapper
        try:
            coro = handler(event, data)
            wrapped_coro = MonitoredCoroWrapper(coro, handler_name, 'handler')
            result = await wrapped_coro
            duration = int((time() - start_time) * 1000)
            log(f"Handler: {handler_name} | User: {user_id} | {event_info} | Duration: {duration} ms", lvl=1, prefix="Update")
            return result
        except Exception as e:
            duration = int((time() - start_time) * 1000)
            log(f"FAIL Handler: {handler_name} | User: {user_id} | {event_info} | Duration: {duration} ms | Err: {e}", lvl=3, prefix="Update")
            raise



from bot.exec import main_router
main_router.message.middleware(LoggingMiddleware())
main_router.callback_query.middleware(LoggingMiddleware())

