import os
import sys
import time
import asyncio
import tracemalloc
from collections import defaultdict
from collections.abc import Coroutine
from bot.modules.logs import log

# Global stats dictionary
monitor_stats = defaultdict(lambda: {
    'type': 'unknown',
    'count': 0,
    'duration': 0.0,
    'db_queries': 0,
    'ram_growth': 0.0,
    'cpu_time': 0.0
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

def increment_db_query():
    try:
        task = asyncio.current_task()
        if task and hasattr(task, '_monitor_name'):
            task._monitor_queries = getattr(task, '_monitor_queries', 0) + 1
    except Exception:
        pass

class MonitoredCoroWrapper(Coroutine):
    def __init__(self, coro, name: str, exec_type: str):
        self.coro = coro
        self.name = name
        self.exec_type = exec_type
        
        self.cpu_time = 0.0
        self.ram_growth = 0.0
        self.queries = 0
        
        # Initialize stats key
        stats = monitor_stats[self.name]
        stats['type'] = self.exec_type

    def send(self, value):
        task = None
        try:
            task = asyncio.current_task()
            if task:
                task._monitor_name = self.name
                if not hasattr(task, '_monitor_queries'):
                    task._monitor_queries = self.queries
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
            
            if task:
                self.queries = getattr(task, '_monitor_queries', 0)
            return res
        except StopIteration as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            if task:
                self.queries = getattr(task, '_monitor_queries', 0)
            
            # Save final stats
            stats = monitor_stats[self.name]
            stats['count'] += 1
            stats['duration'] += self.cpu_time
            stats['db_queries'] += self.queries
            stats['ram_growth'] += self.ram_growth / (1024.0 * 1024.0) # MB
            stats['cpu_time'] += self.cpu_time
            raise e
        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            if task:
                self.queries = getattr(task, '_monitor_queries', 0)
            
            stats = monitor_stats[self.name]
            stats['count'] += 1
            stats['duration'] += self.cpu_time
            stats['db_queries'] += self.queries
            stats['ram_growth'] += self.ram_growth / (1024.0 * 1024.0)
            stats['cpu_time'] += self.cpu_time
            raise e
        finally:
            pass

    def throw(self, typ, val=None, tb=None):
        task = None
        try:
            task = asyncio.current_task()
            if task:
                task._monitor_name = self.name
                if not hasattr(task, '_monitor_queries'):
                    task._monitor_queries = self.queries
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
            
            if task:
                self.queries = getattr(task, '_monitor_queries', 0)
            return res
        except StopIteration as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            if task:
                self.queries = getattr(task, '_monitor_queries', 0)
            
            stats = monitor_stats[self.name]
            stats['count'] += 1
            stats['duration'] += self.cpu_time
            stats['db_queries'] += self.queries
            stats['ram_growth'] += self.ram_growth / (1024.0 * 1024.0)
            stats['cpu_time'] += self.cpu_time
            raise e
        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            self.cpu_time += t_elapsed
            mem_after, _ = tracemalloc.get_traced_memory()
            self.ram_growth += max(0, mem_after - mem_before)
            
            if task:
                self.queries = getattr(task, '_monitor_queries', 0)
            
            stats = monitor_stats[self.name]
            stats['count'] += 1
            stats['duration'] += self.cpu_time
            stats['db_queries'] += self.queries
            stats['ram_growth'] += self.ram_growth / (1024.0 * 1024.0)
            stats['cpu_time'] += self.cpu_time
            raise e
        finally:
            pass

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
        increment_db_query()
        return _orig_run_on_executor(loop, fn, *args, **kwargs)

    motor.frameworks.asyncio.run_on_executor = patched_run_on_executor
except Exception as e:
    log(f"Failed to patch motor framework: {e}", lvl=2)
