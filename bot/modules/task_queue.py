import time
import asyncio
import uuid
import json
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from bot.redismanager import get_redis, redis_get, redis_set
from bot.modules.logs import log

# Registry of handlers: task_type -> (handler_func, rate_limit)
handlers: Dict[str, Tuple[Callable[[Any], Any], int]] = {}

# Resource locks for sequential execution (e.g. dinosaur ID)
running_resources: Set[str] = set()

# Execution history to enforce rate limit per second: task_type -> list of timestamps
execution_history: Dict[str, List[float]] = {}


def task_handler(task_type: str, rate_limit: int = 0) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
    """Decorator to register a task handler with an optional rate limit (executions per second)."""
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        handlers[task_type] = (func, rate_limit)
        return func
    return decorator


async def enqueue_task(
    task_type: str, 
    data: Dict[str, Any], 
    run_at: Optional[float] = None, 
    resource_id: Optional[str] = None
) -> str:
    """Enqueues a task in the Redis queue to be run at a specific time."""
    task_id: str = str(uuid.uuid4())
    if run_at is None:
        run_at = time.time()

    task_payload: Dict[str, Any] = {
        "task_id": task_id,
        "task_type": task_type,
        "data": data,
        "run_at": run_at,
        "resource_id": resource_id
    }

    # Store payload in Redis with a 2-day TTL
    await redis_set(f"task:data:{task_id}", task_payload, ex=86400 * 2)

    # Add task ID to Sorted Set with run_at as the score
    client = get_redis()
    await client.zadd("task:queue", {task_id: run_at})

    log(f"Enqueued task {task_id} ({task_type}) for run_at={run_at}, resource_id={resource_id}", lvl=0, prefix="TaskQueue")
    return task_id


class StreamTaskRunner:
    @staticmethod
    async def run_task(
        task_type: str, 
        data: Dict[str, Any], 
        timeout: float = 10.0, 
        resource_id: Optional[str] = None
    ) -> Any:
        """Pushes a task to the queue and waits for its response from the stream/list with a timeout."""
        task_id: str = str(uuid.uuid4())
        response_key: str = f"task:response:{task_id}"

        task_payload: Dict[str, Any] = {
            "task_id": task_id,
            "task_type": task_type,
            "data": data,
            "run_at": time.time(),
            "resource_id": resource_id,
            "response_key": response_key
        }

        # Store payload in Redis with a short TTL
        await redis_set(f"task:data:{task_id}", task_payload, ex=300)

        # Queue it immediately
        client = get_redis()
        await client.zadd("task:queue", {task_id: time.time()})

        # Wait for the response
        try:
            res = await client.blpop(response_key, timeout=int(timeout)) # type: ignore
            if res:
                # blpop returns a tuple: (list_key, value)
                result_data = json.loads(res[1])
                if "error" in result_data:
                    raise RuntimeError(result_data["error"])
                return result_data.get("result")
            else:
                raise TimeoutError(f"Task of type '{task_type}' timed out after {timeout} seconds")
        finally:
            # Clean up Redis keys
            await client.delete(response_key)
            await client.delete(f"task:data:{task_id}")


async def execute_single_task(task_id: str, payload: Dict[str, Any], handler_func: Callable[[Any], Any]) -> None:
    """Executes a single task, sends response if required, and clears the resource lock."""
    resource_id: Optional[str] = payload.get("resource_id")
    response_key: Optional[str] = payload.get("response_key")
    client = get_redis()

    try:
        # Run the registered handler
        result = await handler_func(payload.get("data"))

        # Send response if caller is waiting
        if response_key:
            await client.rpush(response_key, json.dumps({"result": result})) # type: ignore
            await client.expire(response_key, 60)
    except Exception as e:
        import traceback
        err_msg = f"Task {task_id} failed: {e}\n{traceback.format_exc()}"
        log(err_msg, lvl=3, prefix="TaskQueue")
        if response_key:
            await client.rpush(response_key, json.dumps({"error": str(e)})) # type: ignore
            await client.expire(response_key, 60)
    finally:
        # Release resource lock
        if resource_id:
            running_resources.discard(resource_id)
        # Clean up data key
        await client.delete(f"task:data:{task_id}")


async def task_queue_tick() -> None:
    """Periodic worker checking for ready tasks, verifying rate limits and sequential resource constraints."""
    client = get_redis()
    now: float = time.time()

    # Get tasks that should be run (score <= now)
    task_ids: List[str] = await client.zrangebyscore("task:queue", 0, now)
    if not task_ids:
        return

    tasks_to_run: List[Tuple[str, Dict[str, Any], Callable[[Any], Any], int]] = []

    for task_id in task_ids:
        # Process at most 10 tasks per tick
        if len(tasks_to_run) >= 10:
            break

        payload = await redis_get(f"task:data:{task_id}")
        if not payload:
            await client.zrem("task:queue", task_id)
            continue

        task_type: str = payload.get("task_type", "")
        resource_id: Optional[str] = payload.get("resource_id")

        handler_info = handlers.get(task_type)
        if not handler_info:
            log(f"Handler not found for task type '{task_type}'. Discarding task {task_id}.", lvl=3, prefix="TaskQueue")
            await client.zrem("task:queue", task_id)
            await client.delete(f"task:data:{task_id}")
            continue

        handler_func, rate_limit = handler_info

        # Check rate limit per second
        if rate_limit > 0:
            history = execution_history.setdefault(task_type, [])
            execution_history[task_type] = [t for t in history if t > now - 1.0]
            if len(execution_history[task_type]) >= rate_limit:
                # Defer execution to the next tick
                continue

        # Check sequential resource constraint (lock)
        if resource_id and resource_id in running_resources:
            # Defer execution to the next tick
            continue

        # Add to execution list and lock the resource
        tasks_to_run.append((task_id, payload, handler_func, rate_limit))
        if resource_id:
            running_resources.add(resource_id)

    # Spawn executions
    for task_id, payload, handler_func, rate_limit in tasks_to_run:
        # Remove task from Redis ZSET queue so other ticks don't grab it
        await client.zrem("task:queue", task_id)

        task_type = payload["task_type"]
        if rate_limit > 0:
            execution_history[task_type].append(time.time())

        asyncio.create_task(execute_single_task(task_id, payload, handler_func))
