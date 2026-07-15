from bot.modules.logs import log

async def ensure_background_tasks():
    from bot.models.activity import CollectingActivity, GameActivity, JourneyActivity
    from bot.models.dinosaur import Egg
    from bot.models.other import Lottery
    from bot.models.items import ItemCraft
    from bot.models.market import Product, Preferential

    log("Запуск синхронизации фоновых задач в Redis...", lvl=1)
    
    try:
        await CollectingActivity.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации CollectingActivity: {e}", lvl=3)

    try:
        await GameActivity.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации GameActivity: {e}", lvl=3)

    try:
        await Egg.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Egg: {e}", lvl=3)

    try:
        await JourneyActivity.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации JourneyActivity: {e}", lvl=3)

    try:
        await Lottery.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Lottery: {e}", lvl=3)

    try:
        await ItemCraft.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации ItemCraft: {e}", lvl=3)

    try:
        await Product.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Product: {e}", lvl=3)

    try:
        await Preferential.verify_tasks()
    except Exception as e:
        log(f"Ошибка синхронизации Preferential: {e}", lvl=3)

    # Перестройка Redis-кеша шардов динозавров
    try:
        from bot.modules.shard_cache import rebuild_shards
        await rebuild_shards()
    except Exception as e:
        log(f"Ошибка перестройки шардов: {e}", lvl=3)

    log("Синхронизация фоновых задач завершена.", lvl=1)
