"""
Управление кешем шардов динозавров в Redis.

Ключ: dino:shard:{shard_num}  — Redis Set строк ObjectId.

При старте вызывать rebuild_shards() чтобы синхронизировать кеш с БД.
"""
import hashlib
from bson import ObjectId
from bot.redismanager import get_redis
from bot.modules.logs import log


def _shard_key(shard_num: int) -> str:
    return f"dino:shard:{shard_num}"


def _compute_shard(dino_id, shard_count: int) -> int:
    return int(hashlib.md5(str(dino_id).encode()).hexdigest(), 16) % shard_count


def _get_shard_count() -> int:
    from bot.config import conf
    return getattr(conf, 'shard_count', 16)


async def add_dino_to_shard(dino_id) -> None:
    """Добавить динозавра в его Redis-шард при рождении."""
    try:
        shard_count = _get_shard_count()
        shard_num = _compute_shard(dino_id, shard_count)
        redis = get_redis()
        await redis.sadd(_shard_key(shard_num), str(dino_id))
    except Exception as e:
        log(f'add_dino_to_shard error dino_id={dino_id}: {e}', lvl=3)


async def remove_dino_from_shard(dino_id) -> None:
    """Удалить динозавра из его Redis-шарда при смерти/удалении."""
    try:
        shard_count = _get_shard_count()
        shard_num = _compute_shard(dino_id, shard_count)
        redis = get_redis()
        await redis.srem(_shard_key(shard_num), str(dino_id))
    except Exception as e:
        log(f'remove_dino_from_shard error dino_id={dino_id}: {e}', lvl=3)


async def get_shard_dino_ids(shard_num: int) -> list:
    """Вернуть список ObjectId для данного шарда из Redis."""
    try:
        redis = get_redis()
        members = await redis.smembers(_shard_key(shard_num))
        if not members:
            return []
        return [ObjectId(m) for m in members]
    except Exception as e:
        log(f'get_shard_dino_ids error shard={shard_num}: {e}', lvl=3)
        return []


async def rebuild_shards(quiet: bool = False) -> int:
    """Перестроить все шарды из БД.
    Возвращает общее количество динозавров.
    Вызывается при старте чтобы восстановить кеш после перезапуска.
    """
    from bot.models.dinosaur import Dino
    shard_count = _get_shard_count()
    redis = get_redis()

    if not quiet:
        log('Rebuilding dino shard cache...', lvl=0)

    # Очистить абсолютно все старые ключи шардов (например, если shard_count изменился)
    try:
        cur = 0
        while True:
            cur, keys = await redis.scan(cursor=cur, match="dino:shard:*")
            if keys:
                await redis.delete(*keys)
            if cur == 0:
                break
    except Exception as e:
        log(f"Error clearing shard cache keys: {e}", lvl=3)
        # fallback-очистка на случай сбоя scan
        keys = [_shard_key(n) for n in range(max(shard_count, 128))]
        await redis.delete(*keys)

    # Получить все _id динозавров через сырой MongoDB запрос
    from bot.modules.overwriting.DataCalsses import LazyCollection
    dino_col = LazyCollection(Dino)
    all_dinos = await dino_col.find(projection={'_id': 1})

    total = 0
    pipe = redis.pipeline()
    for d in all_dinos:
        dino_id = d['_id']
        shard_num = _compute_shard(dino_id, shard_count)
        pipe.sadd(_shard_key(shard_num), str(dino_id))
        total += 1
    if total:
        await pipe.execute()

    if not quiet:
        log(f'Dino shard cache rebuilt: {total} dinos across {shard_count} shards', lvl=0)
    return total
