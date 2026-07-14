import os
import sys
import time
import asyncio
import contextvars
import tracemalloc
import types
from collections import defaultdict
from collections.abc import Coroutine
from bot.modules.logs import log

# ContextVar storing a mutable dict: {'name': str, 'queries': int, 'queries_detail': dict, 'query_path': list}
current_monitor_context = contextvars.ContextVar('current_monitor_context', default=None)

# Global stats dictionary
monitor_stats = defaultdict(lambda: {
    'type': 'unknown',
    'count': 0,
    'duration': 0.0,
    'db_queries': 0,
    'ram_growth': 0.0,
    'cpu_time': 0.0,
    'db_queries_detail': {},
    'min_queries': 0,
    'min_queries_path': [],
    'max_queries': 0,
    'max_queries_path': []
})

# Start Python's built-in tracemalloc memory tracker
try:
    if not tracemalloc.is_tracing():
        tracemalloc.start()
except Exception as e:
    log(f"Failed to start tracemalloc: {e}", lvl=2)

try:
    _ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
except Exception:
    _ticks = 100

def get_cpu_time() -> float:
    try:
        with open('/proc/self/stat', 'r') as f:
            parts = f.read().split()
            return (int(parts[13]) + int(parts[14])) / _ticks
    except Exception:
        return 0.0

def get_ram_usage() -> float:
    """Returns RSS memory usage in MB."""
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return 0.0

def get_system_cpu_usage() -> float:
    try:
        with open('/proc/loadavg', 'r') as f:
            return float(f.read().split()[0]) * 100.0
    except Exception:
        return 0.0

def get_db_op_details(fn, *args, **kwargs):
    coll_name = "unknown"
    op_name = "unknown"
    
    try:
        # Resolve functools.partial
        func = fn
        while hasattr(func, 'func'):
            func = func.func
            
        # Get the target object: either func.__self__ or the first argument in args
        target = getattr(func, '__self__', None)
        if target is None and args:
            target = args[0]
            
        if target is not None:
            # 1. If target is a Cursor
            if hasattr(target, 'collection'):
                coll = getattr(target, 'collection', None)
                if coll is not None and hasattr(coll, 'name'):
                    coll_name = coll.name
                op_val = getattr(func, '__name__', 'op') or 'op'
                op_str = str(op_val)
                if op_str.startswith('_'):
                    op_str = op_str[1:]
                op_name = f"cursor.{op_str}"
                
            # 2. If target is a Collection
            elif hasattr(target, 'name') and hasattr(target, 'database'):
                coll_name = target.name
                op_val = getattr(func, '__name__', 'op') or 'op'
                op_name = str(op_val)
                
            # 3. If target is a Database
            elif hasattr(target, 'client') and hasattr(target, 'name'):
                coll_name = f"db:{target.name}"
                op_val = getattr(func, '__name__', 'op') or 'op'
                op_name = str(op_val)
    except Exception as e:
        log(f"Error in get_db_op_details: {e}", lvl=3)
        
    if op_name == "unknown":
        try:
            op_val = getattr(func, '__name__', 'op') or 'op'
            op_name = str(op_val)
        except Exception:
            op_name = "op"
            
    return coll_name, op_name

def increment_db_query(fn, *args, **kwargs):
    try:
        ctx = current_monitor_context.get()
        if ctx is not None:
            ctx['queries'] += 1
            coll_name, op_name = get_db_op_details(fn, *args, **kwargs)
            key = f"{coll_name}.{op_name}"
            ctx['queries_detail'][key] = ctx['queries_detail'].get(key, 0) + 1
            if 'query_path' not in ctx:
                ctx['query_path'] = []
            ctx['query_path'].append(key)
    except Exception as e:
        log(f"Error in increment_db_query: {e}", lvl=3)

def save_stat_to_redis(name: str, exec_type: str, duration: float, queries: int, ram_growth: float, cpu_time: float, queries_detail: dict, query_path: list):
    async def _async_save():
        try:
            from bot.redismanager import redis_get, redis_set
            key = f"monitor_perf:{name}"
            data = await redis_get(key)
            if not isinstance(data, dict):
                data = {
                    'type': exec_type,
                    'count': 0,
                    'duration': 0.0,
                    'db_queries': 0,
                    'ram_growth': 0.0,
                    'cpu_time': 0.0,
                    'db_queries_detail': {},
                    'min_queries': queries,
                    'min_queries_path': query_path,
                    'max_queries': queries,
                    'max_queries_path': query_path
                }
            
            data['type'] = exec_type
            data['count'] += 1
            data['duration'] += duration
            data['db_queries'] += queries
            data['ram_growth'] += ram_growth
            data['cpu_time'] += cpu_time
            
            if 'db_queries_detail' not in data:
                data['db_queries_detail'] = {}
                
            for q_key, q_val in queries_detail.items():
                data['db_queries_detail'][q_key] = data['db_queries_detail'].get(q_key, 0) + q_val
            
            # Min / Max tracking
            if 'min_queries' not in data or queries < data['min_queries']:
                data['min_queries'] = queries
                data['min_queries_path'] = query_path
            if 'max_queries' not in data or queries > data['max_queries']:
                data['max_queries'] = queries
                data['max_queries_path'] = query_path
                
            # TTL: 1 week (604800 seconds)
            await redis_set(key, data, ex=604800)
        except Exception as e:
            log(f"Failed to save stat for {name} to Redis: {e}", lvl=3)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_async_save())
    except Exception:
        pass

async def get_all_perf_stats() -> dict:
    from bot.redismanager import get_redis, redis_get
    try:
        r = get_redis()
        keys = await r.keys("monitor_perf:*")
        stats = {}
        for key in keys:
            name = key.replace("monitor_perf:", "")
            data = await redis_get(key)
            if data:
                stats[name] = data
        return stats
    except Exception as e:
        log(f"Failed to fetch stats from Redis: {e}", lvl=3)
        return {}

async def clear_all_perf_stats():
    from bot.redismanager import get_redis, redis_del
    try:
        r = get_redis()
        keys = await r.keys("monitor_perf:*")
        for key in keys:
            await redis_del(key)
    except Exception as e:
        log(f"Failed to clear stats from Redis: {e}", lvl=3)

def get_recursive_size(obj, seen=None):
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    
    # Avoid traversing modules, classes, functions, generator objects
    if isinstance(obj, (types.ModuleType, types.FunctionType, types.MethodType, types.BuiltinFunctionType, types.BuiltinMethodType, type)):
        return sys.getsizeof(obj)
        
    size = sys.getsizeof(obj)
    
    try:
        if isinstance(obj, dict):
            size += sum(get_recursive_size(k, seen) + get_recursive_size(v, seen) for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            size += sum(get_recursive_size(i, seen) for i in obj)
        elif hasattr(obj, '__dict__'):
            size += get_recursive_size(obj.__dict__, seen)
    except Exception:
        pass
    return size

def get_heavy_globals(limit=20):
    heavy_globals = []
    seen = set()
    
    try:
        # Snapshot of modules to avoid RuntimeError: dictionary changed size during iteration
        modules_snap = list(sys.modules.items())
        
        for mod_name, module in modules_snap:
            if module is None or not mod_name.startswith(('bot', 'main')):
                continue
            try:
                mod_dict = getattr(module, '__dict__', None)
                if not mod_dict:
                    continue
                for var_name, val in mod_dict.items():
                    if var_name.startswith('__'):
                        continue
                    # Avoid measuring module import references
                    if isinstance(val, sys.modules[__name__].__class__):
                        continue
                    
                    size = get_recursive_size(val, seen)
                    if size > 1024:  # > 1 KB
                        heavy_globals.append({
                            'module': mod_name,
                            'variable': var_name,
                            'type': type(val).__name__,
                            'size': size
                        })
            except Exception:
                pass
    except Exception:
        pass
            
    heavy_globals.sort(key=lambda x: x['size'], reverse=True)
    return heavy_globals[:limit]

def get_tracemalloc_stats(limit=15):
    stats_list = []
    try:
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            for stat in top_stats[:limit]:
                stats_list.append({
                    'file': stat.traceback[0].filename,
                    'line': stat.traceback[0].lineno,
                    'size': stat.size,
                    'count': stat.count
                })
    except Exception as e:
        log(f"Error taking tracemalloc snapshot: {e}", lvl=3)
    return stats_list

def get_active_tasks_info():
    tasks_info = []
    try:
        all_tasks = asyncio.all_tasks()
        for t in all_tasks:
            t_name = t.get_name()
            t_coro = t.get_coro()
            coro_name = getattr(t_coro, '__name__', 'unknown')
            if hasattr(t_coro, 'cr_frame') and t_coro.cr_frame:
                file_name = t_coro.cr_frame.f_code.co_filename
                line_no = t_coro.cr_frame.f_lineno
            else:
                stack = t.get_stack()
                if stack:
                    file_name = stack[-1].f_code.co_filename
                    line_no = stack[-1].f_lineno
                else:
                    file_name = "unknown"
                    line_no = 0
            
            age = None
            start_time = getattr(t, '_start_time', None)
            if start_time:
                age = time.time() - start_time
                
            mon_name = getattr(t, '_monitor_name', None)
            
            tasks_info.append({
                'name': t_name,
                'monitor_name': mon_name,
                'coro': coro_name,
                'file': file_name,
                'line': line_no,
                'age': age
            })
    except Exception as e:
        log(f"Error getting active tasks info: {e}", lvl=3)
    return tasks_info

class MonitoredCoroWrapper(Coroutine):
    def __init__(self, coro, name: str, exec_type: str):
        self.coro = coro
        self.name = name
        self.exec_type = exec_type
        
        self.cpu_time = 0.0
        self.ram_growth = 0.0
        
        # Shared mutable context dictionary
        self.monitor_ctx = {
            'name': self.name,
            'queries': 0,
            'queries_detail': {},
            'query_path': []
        }

    def send(self, value):
        token = current_monitor_context.set(self.monitor_ctx)
        
        # Record task start time
        try:
            task = asyncio.current_task()
            if task is not None:
                if not hasattr(task, '_start_time'):
                    task._start_time = time.time()
                if not hasattr(task, '_monitor_name'):
                    task._monitor_name = self.name
        except Exception:
            pass
            
        mem_before, _ = tracemalloc.get_traced_memory()
        t0 = time.perf_counter()
        
        try:
            res = self.coro.send(value)
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            return res
        except StopIteration as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            # Save stats to Redis
            save_stat_to_redis(
                name=self.name,
                exec_type=self.exec_type,
                duration=self.cpu_time,
                queries=self.monitor_ctx['queries'],
                ram_growth=self.ram_growth / (1024.0 * 1024.0),
                cpu_time=self.cpu_time,
                queries_detail=self.monitor_ctx['queries_detail'],
                query_path=self.monitor_ctx.get('query_path', [])
            )
            raise e
        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            # Save stats to Redis
            save_stat_to_redis(
                name=self.name,
                exec_type=self.exec_type,
                duration=self.cpu_time,
                queries=self.monitor_ctx['queries'],
                ram_growth=self.ram_growth / (1024.0 * 1024.0),
                cpu_time=self.cpu_time,
                queries_detail=self.monitor_ctx['queries_detail'],
                query_path=self.monitor_ctx.get('query_path', [])
            )
            raise e
        finally:
            current_monitor_context.reset(token)

    def throw(self, typ, val=None, tb=None):
        token = current_monitor_context.set(self.monitor_ctx)
        
        # Record task start time
        try:
            task = asyncio.current_task()
            if task is not None:
                if not hasattr(task, '_start_time'):
                    task._start_time = time.time()
                if not hasattr(task, '_monitor_name'):
                    task._monitor_name = self.name
        except Exception:
            pass
            
        mem_before, _ = tracemalloc.get_traced_memory()
        t0 = time.perf_counter()
        
        try:
            res = self.coro.throw(typ, val, tb)
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            return res
        except StopIteration as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            save_stat_to_redis(
                name=self.name,
                exec_type=self.exec_type,
                duration=self.cpu_time,
                queries=self.monitor_ctx['queries'],
                ram_growth=self.ram_growth / (1024.0 * 1024.0),
                cpu_time=self.cpu_time,
                queries_detail=self.monitor_ctx['queries_detail'],
                query_path=self.monitor_ctx.get('query_path', [])
            )
            raise e
        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            save_stat_to_redis(
                name=self.name,
                exec_type=self.exec_type,
                duration=self.cpu_time,
                queries=self.monitor_ctx['queries'],
                ram_growth=self.ram_growth / (1024.0 * 1024.0),
                cpu_time=self.cpu_time,
                queries_detail=self.monitor_ctx['queries_detail'],
                query_path=self.monitor_ctx.get('query_path', [])
            )
            raise e
        finally:
            current_monitor_context.reset(token)

    def close(self):
        try:
            self.coro.close()
        except Exception:
            pass

    def __await__(self):
        value = None
        while True:
            try:
                value = yield self.send(value)
            except BaseException as e:
                if isinstance(e, StopIteration):
                    return e.value
                try:
                    tb = getattr(e, '__traceback__', None)
                    value = self.throw(type(e), e, tb)
                except StopIteration as stop_err:
                    return stop_err.value
                except Exception as inner_err:
                    raise inner_err

# Patch Motor frameworks executor to count DB queries on the main thread
try:
    import motor.frameworks.asyncio
    _orig_run_on_executor = motor.frameworks.asyncio.run_on_executor

    def patched_run_on_executor(loop, fn, *args, **kwargs):
        increment_db_query(fn, *args, **kwargs)
        return _orig_run_on_executor(loop, fn, *args, **kwargs)

    motor.frameworks.asyncio.run_on_executor = patched_run_on_executor
except Exception as e:
    log(f"Failed to patch motor framework: {e}", lvl=2)
