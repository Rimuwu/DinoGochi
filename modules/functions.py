import json
import logging
import random
import time

from colorama import Fore, Style

with open('json/items.json', encoding='utf-8') as f: items_data = json.load(f)['items']

class LogFuncs:

    def __init__(self) -> None:
        '''Функции логирования'''

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

class DataFormat:

    def __init__(self) -> None:
        '''Функции форматизации данных'''
    
    def random_dict(data: dict) -> dict:
        """ Предоставляет общий формат данных, подерживающий 
            случайные и статичные числа.
        
        Примеры словаря:
          >>> {"min": 1, "max": 2, "type": "random"}
          >>> {"act": 1, "type": "static"}
        """

        if 'type' in data.keys():
            if data["type"] in ["static", "random"]:

                if data["type"] == "static":
                    return data['act']

                elif data["type"] == "random":
                    if data['min'] >= data['max']:
                        return 0
                    else:
                        return random.randint(data['min'], data['max'])
                else:
                    return 0
            else:
                return data
        else:
            return data

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")