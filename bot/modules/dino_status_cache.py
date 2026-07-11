from bot.redismanager import get_redis
from bot.modules.logs import log

_STATUS_TTL = 7200

def _status_key(dino_id):
    return f"dino:status:{dino_id}"

async def get_cached_status(dino_id):
    try:
        redis = get_redis()
        return await redis.get(_status_key(dino_id))
    except Exception as e:
        log(f"get_cached_status error: {e}", lvl=2)
        return None

async def get_cached_statuses(dino_ids):
    try:
        redis = get_redis()
        keys = [_status_key(d_id) for d_id in dino_ids]
        return await redis.mget(keys)
    except Exception as e:
        log(f"get_cached_statuses error: {e}", lvl=2)
        return [None] * len(dino_ids)

async def set_cached_status(dino_id, status):
    try:
        redis = get_redis()
        await redis.set(_status_key(dino_id), status, ex=_STATUS_TTL)
    except Exception as e:
        log(f"set_cached_status error: {e}", lvl=2)

async def invalidate_status_cache(dino_id):
    try:
        redis = get_redis()
        await redis.delete(_status_key(dino_id))
    except Exception as e:
        log(f"invalidate_status_cache error: {e}", lvl=2)

