import json
from typing import Optional, List, Dict, Any
from bot.redismanager import get_redis

async def add_to_tavern(userid: int, name: str, lang: str):
    """ Adds a user to the Redis tavern. """
    redis_client = get_redis()
    doc = {
        '_id': str(userid),
        'userid': userid,
        'time_in': int(time_import()),
        'lang': lang,
        'name': name
    }
    await redis_client.hset("tavern:users", str(userid), json.dumps(doc))

async def remove_from_tavern(userid: int):
    """ Removes a user from the Redis tavern. """
    redis_client = get_redis()
    await redis_client.hdel("tavern:users", str(userid))

async def is_in_tavern(userid: int) -> bool:
    """ Checks if a user is in the Redis tavern. """
    redis_client = get_redis()
    return await redis_client.hexists("tavern:users", str(userid))

async def get_tavern_users() -> List[Dict[str, Any]]:
    """ Returns all users currently in the Redis tavern. """
    redis_client = get_redis()
    all_users = await redis_client.hgetall("tavern:users")
    results = []
    for v in all_users.values():
        try:
            results.append(json.loads(v))
        except Exception:
            pass
    return results

async def get_tavern_count() -> int:
    """ Returns the number of users in the Redis tavern. """
    redis_client = get_redis()
    return await redis_client.hlen("tavern:users")

def time_import():
    import time
    return time.time()
