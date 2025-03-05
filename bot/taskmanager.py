import asyncio
import typing
from bot.modules.logs import log
from time import time

ioloop = asyncio.get_event_loop()
tasks = []

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
        while True:
            try:
                s = time()
                log(message=f'{function.__name__} start', lvl=0)
                f = await function(**kwargs)
                log(message=f'{function.__name__} end - {round(time() - s, 7)}', lvl=0)
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

    task = ioloop.create_task(_task_executor(function, repeat_time, delay, **kwargs))

    if task in tasks:
        raise RuntimeError(f'Функция {function.__name__} добавлена повторно.')
    else:
        log(f'{function.__name__} добавлена в задачи c временем повтора {repeat_time} и задержкой {delay}', 0)
        tasks.append(task)

def run():
    ioloop.run_until_complete(asyncio.gather(*tasks))
    ioloop.close()
