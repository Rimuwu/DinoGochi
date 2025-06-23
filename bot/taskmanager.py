import asyncio
import inspect
import typing
from bot.modules.logs import log
from time import time
from datetime import datetime, timedelta

ioloop = asyncio.get_event_loop()
tasks = []

async def _task_executor(function, 
                         repeat_time: float, 
                         delay: float,
                         **kwargs):
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
        as_flag = inspect.iscoroutinefunction(function)

        while True:
            try:
                s = time()
                log(message=f'{function.__name__} start', lvl=0)

                if as_flag: await function(**kwargs)
                else: function(**kwargs)

                log(message=f'{function.__name__} end - {round(time() - s, 7)}', lvl=0)
            except Exception as error:
                log(prefix=f"{function.__name__} task_error", message=str(error), lvl=3)

            await asyncio.sleep(repeat_time)

async def _specific_task_executor(function, 
                         specific_time: typing.Optional[str],
                         **kwargs):
    """Исполнитель всех задач с обработчиком ошибок и созданием потока
    """
    if not function:
        log(prefix="_specific_task_executor", message="function is None", lvl=4)
        return

    args = specific_time.split(':') # H:M:S
    hours = int(args[0]) if len(args) > 0 else 0
    minutes = int(args[1]) if len(args) > 1 else 0
    seconds = int(args[2]) if len(args) > 2 else 0

    as_flag = inspect.iscoroutinefunction(function)

    while True:

        now = datetime.now()
        target_time = now.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)
        if target_time <= now:
            target_time += timedelta(days=1)
        sleep_seconds = (target_time - now).total_seconds()

        await asyncio.sleep(sleep_seconds)

        try:
            s = time()
            log(message=f'{function.__name__} start', lvl=0)

            if as_flag: await function(**kwargs)
            else: function(**kwargs)

            log(message=f'{function.__name__} end - {round(time() - s, 7)}', lvl=0)
        except Exception as error:
            log(prefix=f"{function.__name__} task_error", message=str(error), lvl=3)

def add_task(function, 
             repeat_time: float = 0, 
             delay: float = 0, 
             specific_time: typing.Optional[str] = None,
             **kwargs: typing.Any) -> None:
    """Добавить задачу в асинхрон

    Args:
        function (Callable[[typing.Any], typing.Any]): функция для задачи
        repeat_time (float, optional): время повтора, если 0 то задача не зациклена. Defaults to 0.
        delay (float, optional): задержка. Defaults to 0.
        specific_time (typing.Optional[str], optional): время запуска задачи в формате HH:MM:SS. Defaults to None.
        **kwargs (typing.Any): аргументы для функции задачи
    """
    assert callable(function), f'{function!r} is not callable'
    assert isinstance(repeat_time, (int, float)), f'repeat_time {repeat_time!r} must be an int or float'
    assert isinstance(delay, (int, float)), f'delay {delay!r} must be an int or float'
    assert specific_time is None or isinstance(specific_time, str), f'specific_time {specific_time!r} must be a str'
    assert specific_time is None or len(specific_time.split(':')) > 0, f'specific_time {specific_time!r} must be in HH:MM:SS format'

    if specific_time:
        task = ioloop.create_task(_specific_task_executor(function, specific_time, **kwargs))
    else:
        task = ioloop.create_task(_task_executor(function, repeat_time, delay, **kwargs))

    if task in tasks:
        raise RuntimeError(f'Функция {function.__name__} добавлена повторно.')
    else:
        if specific_time:
            log(f'{function.__name__} добавлена в задачи c временем старта в {specific_time}', 0)
        else:
            log(f'{function.__name__} добавлена в задачи c временем повтора {repeat_time} и задержкой {delay}', 0)

        tasks.append(task)

def run():
    ioloop.run_until_complete(asyncio.gather(*tasks))
    ioloop.close()
