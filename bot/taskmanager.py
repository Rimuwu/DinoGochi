import asyncio
import typing
from bot.modules.logs import log
from time import time
from collections import defaultdict

ioloop = asyncio.get_event_loop()
tasks = []
_registered_functions = set()

# Per-task accumulated timing stats: {func_name: [duration_seconds, ...]}
_timing_stats: dict[str, list] = defaultdict(list)
_last_stats_report: float = time()
_STATS_INTERVAL = 60.0  # report every 60 seconds

async def _report_timing_stats():
    """Dumps average execution times for all tasks since last report."""
    global _last_stats_report
    now = time()
    if now - _last_stats_report < _STATS_INTERVAL:
        return
    _last_stats_report = now
    lines = []
    for fname, durations in _timing_stats.items():
        if durations:
            avg = sum(durations) / len(durations)
            lines.append(f"  {fname}: avg={avg:.4f}s over {len(durations)} runs")
    _timing_stats.clear()
    if lines:
        log("Task timings (last minute):\n" + "\n".join(lines), lvl=0)

async def _task_executor(function, repeat_time: float, delay: float, **kwargs):
    """Исполнитель всех задач с обработчиком ошибок и созданием потока
    """
    if not function:
        log(prefix="_task_executor", message="function is None", lvl=4)
        return

    await asyncio.sleep(delay)

    if not repeat_time:
        if function.__name__ == 'start_polling':
            bots = kwargs.get('bots', []).copy()
            del kwargs['bots']

            await function(*bots, **kwargs)
        else:
            try:
                f = await function(**kwargs)
            except Exception as error:
                log(prefix=f"{function.__name__} task_error", message=str(error), lvl=4)
    else:
        from bot.config import conf
        while True:
            try:
                s = time()
                verbose = getattr(conf, 'task_verbose_logging', False)
                skip_log = function.__name__ == 'task_queue_tick'
                if verbose and not skip_log:
                    log(message=f'{function.__name__} start', lvl=0)
                f = await function(**kwargs)
                elapsed = time() - s
                if not skip_log:
                    if verbose:
                        log(message=f'{function.__name__} end - {round(elapsed, 7)}', lvl=0)
                    else:
                        _timing_stats[function.__name__].append(elapsed)
                        await _report_timing_stats()
            except Exception as error:
                log(prefix=f"{function.__name__} task_error", message=str(error), lvl=3)

            await asyncio.sleep(repeat_time)


def add_task(function, repeat_time: float = 0, delay: float = 0, **kwargs: typing.Any) -> None:
    """Добавить задачу в асинхрон

    Args:
        function (Callable[[typing.Any], typing.Any]): функция для задачи
        repeat_time (float, optional): время повтора, если 0 то задача не зациклена. Defaults to 0.
        delay (float, optional): задержка. Defaults to 0.
    """
    assert callable(function), f'{function!r} is not callable'
    assert isinstance(repeat_time, (int, float)), f'repeat_time {repeat_time!r} must be an int or float'
    assert isinstance(delay, (int, float)), f'delay {delay!r} must be an int or float'

    if function in _registered_functions:
        raise RuntimeError(f'Функция {function.__name__} добавлена повторно.')
    else:
        log(f'{function.__name__} добавлена в задачи c временем повтора {repeat_time} и задержкой {delay}', 0)
        _registered_functions.add(function)
        tasks.append((function, repeat_time, delay, kwargs))

def run():
    from bot.dbmanager import check_db, mongo_client
    ioloop.run_until_complete(check_db(mongo_client))
    
    # Создаем задачи на event loop только после инициализации базы данных
    async_tasks = []
    for func, rep, del_t, kwargs in tasks:
        task = ioloop.create_task(_task_executor(func, rep, del_t, **kwargs))
        async_tasks.append(task)
        
    ioloop.run_until_complete(asyncio.gather(*async_tasks))
    ioloop.close()
