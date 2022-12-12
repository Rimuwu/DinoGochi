import logging
from colorama import Fore, Style
import time

class LogFuncs:

    def __init__(self) -> None:
        ...

    def console_message(message, lvl=1) -> None:
        """
        LVL: \n
        1 - info\n
        2 - warning\n
        3 - error\n
        4 - critical
        """

        if lvl == 1:
            logging.info(message)
            print(Fore.GREEN + f"{time.strftime('%Y %m-%d %H.%M.%S')} Бот: {message}" + Style.RESET_ALL)
        elif lvl == 2:
            logging.warning(message)
            print(Fore.BLUE + f"{time.strftime('%Y %m-%d %H.%M.%S')} Бот: {message}" + Style.RESET_ALL)
        elif lvl == 3:
            logging.error(message)
            print(Fore.YELLOW + f"{time.strftime('%Y %m-%d %H.%M.%S')} Бот: {message}" + Style.RESET_ALL)
        else:
            logging.critical(message)
            print(Fore.RED + f"{time.strftime('%Y %m-%d %H.%M.%S')} Бот: {message}" + Style.RESET_ALL)

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")