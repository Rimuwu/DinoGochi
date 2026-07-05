import json
from typing import Any, Optional
import redis.asyncio as aioredis
from bot.config import conf
from bot.modules.logs import log

_redis_client: Optional[aioredis.Redis] = None

def get_redis() -> aioredis.Redis:
    """Returns the singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized. Call init_redis() first.")
    return _redis_client

async def init_redis():
    """Initializes the Redis connection and runs a ping check."""
    global _redis_client
    if _redis_client is not None:
        return

    log("Initializing Redis client...", prefix="Redis")
    try:
        _redis_client = aioredis.from_url(
            conf.redis_url,
            decode_responses=True,
            socket_timeout=5.0
        )
        await _redis_client.ping()
        log("Redis connection successful.", prefix="Redis")

        # Миграция file_base.json в Redis
        import os
        file_base_path = 'bot/data/file_base.json'
        if os.path.exists(file_base_path):
            try:
                with open(file_base_path, encoding='utf-8') as f:
                    data = json.load(f)
                if data:
                    log(f"Migrating {len(data)} items from file_base.json to Redis...", prefix="Redis")
                    for k, v in data.items():
                        await _redis_client.set(f"file_id:{k}", v)
                os.remove(file_base_path)
                log("file_base.json successfully migrated to Redis and deleted.", prefix="Redis")
            except Exception as e:
                log(f"Failed to migrate file_base.json to Redis: {e}", prefix="Redis", lvl=3)

    except Exception as e:
        log(f"Failed to connect to Redis: {e}", prefix="Redis", lvl=4)
        raise

async def redis_get(key: str) -> Optional[Any]:
    """Retrieves a key from Redis and parses its JSON content."""
    client = get_redis()
    try:
        data = await client.get(key)
        if data is not None:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
    except Exception as e:
        log(f"Redis get error for key '{key}': {e}", prefix="Redis", lvl=3)
    return None

async def redis_set(key: str, value: Any, ex: Optional[int] = None):
    """Serializes a value to JSON and stores it in Redis with an optional TTL (in seconds)."""
    client = get_redis()
    try:
        serialized = json.dumps(value, default=str)
        await client.set(key, serialized, ex=ex)
    except Exception as e:
        log(f"Redis set error for key '{key}': {e}", prefix="Redis", lvl=3)

async def redis_del(key: str):
    """Deletes a key from Redis."""
    client = get_redis()
    try:
        await client.delete(key)
    except Exception as e:
        log(f"Redis del error for key '{key}': {e}", prefix="Redis", lvl=3)
