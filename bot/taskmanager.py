import asyncio
from bot.modules.logs import log
from time import time, strftime
from colorama import Fore, Style

ioloop = asyncio.get_event_loop()
tasks = []

async def _task_executor(function, repeat_time: float, delay: float, **kwargs):
    """Исполнитель всех задач с обработчиком ошибок и созданием потока
    """
    await asyncio.sleep(delay)

    if repeat_time:
        while True:
            try:
                await function(**kwargs)
            except Exception as error:
                log(prefix=f"{function.__name__} task_error", message=str(error), lvl=3)

            await asyncio.sleep(repeat_time)
    else:
        try:
            await function(**kwargs)
        except Exception as error:
            log(prefix=f"{function.__name__} task_error", message=str(error), lvl=4)


def add_task(function, repeat_time: float=0, delay: float=0, **kwargs):
    """Добавить задачу в асинхрон

    Args:
        function (def): функция для задачи
        repeat_time (int, optional): время повтора, если 0 то задача не зациклена. Defaults to 0.
        delay (int, optional): задержка. Defaults to 0.
    """

    task = ioloop.create_task(_task_executor(function, repeat_time, delay, **kwargs))

    assert task not in tasks, f'Функция {function.__name__} добавлена повторно.'
    log(f'{function.__name__} добавлена в задачи c временем повтора {repeat_time} и задержкой {delay}', 0)
    tasks.append(task)

def run():
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()