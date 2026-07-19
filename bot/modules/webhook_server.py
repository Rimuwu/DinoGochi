import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import conf
from bot.modules.logs import log

async def run_webhook_server(bot: Bot, dp: Dispatcher):
    app = web.Application()

    path = conf.webhook_path
    if not path.startswith('/'):
        path = f"/{path}"

    webhook_url = f"{conf.webhook_domain.rstrip('/')}{path}"
    log(f"Настройка вебхука на URL: {webhook_url}", lvl=1)

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    handler.register(app, path=path)
    setup_application(app, dp, bot=bot)

    async def handle_inline_image(request):
        filename = request.match_info.get('filename')
        if not filename or not filename.startswith('img-') or '..' in filename or '/' in filename or '\\' in filename:
            return web.Response(status=400, text="Invalid filename")

        filepath = os.path.join('bot/temp', filename)
        if not os.path.exists(filepath):
            return web.Response(status=404, text="Image not found")

        try:
            content_type = 'image/png'
            if filename.endswith('.jpg') or filename.endswith('.jpeg'):
                content_type = 'image/jpeg'

            with open(filepath, 'rb') as f:
                file_bytes = f.read()

            return web.Response(body=file_bytes, content_type=content_type)
        except Exception as e:
            log(f"Error serving inline image {filename}: {e}", lvl=3)
            return web.Response(status=500, text="Internal server error")

    app.router.add_get('/inline-image/{filename}', handle_inline_image)

    runner = web.AppRunner(app)
    await runner.setup()

    host = getattr(conf, 'webhook_host', '0.0.0.0')
    port = getattr(conf, 'webhook_port', 8080)

    site = web.TCPSite(runner, host=host, port=port)
    await site.start()

    log(f"Сервер вебхуков запущен на http://{host}:{port}{path}", lvl=1)

    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dp.resolve_used_update_types()
    )

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        log("Остановка сервера вебхуков...", lvl=1)
        try:
            await bot.delete_webhook()
        except Exception as e:
            log(f"Ошибка удаления вебхука при остановке: {e}", lvl=3)
        await runner.cleanup()
