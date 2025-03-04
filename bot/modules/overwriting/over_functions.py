
from asyncio import sleep
from typing import Callable

async def async_antiflood(function: Callable, *args, number_retries=3, **kwargs):
    """
    Use this function inside loops in order to avoid getting TooManyRequests error.
    Example:

    .. code-block:: python3
        for chat_id in chat_id_list:
        msg = await async_antiflood(bot.send_message, chat_id, text)

    :param function: The function to call
    :type function: :obj:`Callable`

    :param number_retries: Number of retries to send
    :type function: :obj:int

    :param args: The arguments to pass to the function
    :type args: :obj:`tuple`

    :param kwargs: The keyword arguments to pass to the function
    :type kwargs: :obj:`dict`

    :return: None
    """

    for _ in range(number_retries - 1):
        try:
            return await function(*args, **kwargs)
        except Exception as ex:
            error_code = ex.args[0] if ex.args else None
            if error_code == 429:
                await sleep(5)
            else:
                raise
    else:
        return await function(*args, **kwargs)