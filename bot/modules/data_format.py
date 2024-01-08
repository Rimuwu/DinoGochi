import random
import re
import string

from telebot.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, User)

from bot.const import GAME_SETTINGS
from bot.modules.localization import get_data


def escape_markdown(content: str) -> str:
    """ Экранирует символы Markdown в строке.
    """

    parse = re.sub(r"([_*\[\]()~`>\#\+\-=|\!\{\}])", r"", content)
    reparse = re.sub(r"\\\\([_*\[\]()~`>\#\+\-=|!\{\}])", r"", parse)
    if not reparse: reparse = 'noname'
    return reparse 

def chunks(lst: list, n: int) -> list:
    """ Делит список lst, на списки по n элементов
       Возвращает список
    """
    def work():
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
    return list(work())
    
def random_dict(data: dict) -> int:
    """ Предоставляет общий формат данных, подерживающий 
       случайные и статичные элементы.

    Типы словаря:
    { "min": 1, "max": 2, "type": "random" }
    >>> Случайное число от 1 до 2
    { "act": [12, 42, 1], "type": "choice" } 
    >>> Случайный элемент
    { "act": 1, "type": "static" }
    >>> Статичное число 1
    """

    if type(data) == dict:
        if data["type"] == "static": return data['act']

        elif data["type"] == "random":
            if data['min'] < data['max']:
                return random.randint(data['min'], data['max'])
            else: return data['min']
        
        elif data["type"] == "choice":
            if data['act']: return random.choice(data['act'])
            else: return 0
    elif type(data) == int: return data
    return 0

def list_to_keyboard(buttons: list, row_width: int = 3, resize_keyboard: bool = True, one_time_keyboard = None) -> ReplyKeyboardMarkup:
    """ Превращает список со списками в объект клавиатуры.
        Example:
            butttons = [ ['привет'], ['отвяжись', 'ты кто?'] ]

        >      привет
          отвяжись  ты кто?
        
            butttons = ['привет','отвяжись','ты кто?'], 
            row_width = 1

        >  привет
          отвяжись  
          ты кто?
    """
    markup = ReplyKeyboardMarkup(row_width=row_width, 
                                 resize_keyboard=resize_keyboard, 
                                 one_time_keyboard=one_time_keyboard)

    for line in buttons:
        try:
            if type(line) == list:
                markup.add(*[i for i in line])
            else: markup.add(line)
        except Exception as e:
            print('list_to_keyboard', line, type(line), e)

    return markup

def list_to_inline(buttons: list, row_width: int = 3) -> InlineKeyboardMarkup:
    """ Превращает список со списками в объект inlineKeyboard.
        Example:
            butttons = [ {'привет':'call_key'}, {'отвяжись':'call_key'}, {'ты кто?':'call_key'} ]

        >      привет
          отвяжись  ты кто?
        
            butttons = [ {'привет':'call_key', 'отвяжись':'call_key', 'ты кто?':'call_key'} ], 
            row_width = 1

        >  привет
          отвяжись  
          ты кто?
    """
    inline = InlineKeyboardMarkup(row_width=row_width)

    if len(buttons) == 1:
        inline.add(
            *[InlineKeyboardButton(
            text=key, callback_data=item) for key, item in buttons[0].items()])
    else:
        for line in buttons:
            inline.add(*[InlineKeyboardButton(
                text=key, callback_data=item) for key, item in line.items()])
    return inline

def user_name(user: User, username: bool = True) -> str:
    """ Возвращает имя / ник, в зависимости от того, что есть
    """
    if user.username is not None and username:
        return f'@{user.username}'
    else:
        if user.last_name is not None and user.first_name:
            return escape_markdown(f'{user.first_name} {user.last_name}')
        else: return escape_markdown(user.first_name)

def random_quality() -> str:
    """ Случайная редкость
    """
    rarities = list(GAME_SETTINGS['dino_rarity'].keys())
    weights = list(GAME_SETTINGS['dino_rarity'].values())

    quality = random.choices(rarities, weights)[0]
    return quality

def random_code(length: int=10):
    """ Генерирует случайный код из букв и цыфр
    """
    alphabet = string.ascii_letters + string.digits
    code = ''.join(random.choice(alphabet) for i in range(length))
    return code

def seconds_to_time(seconds: int) -> dict:
    """ Преобразует число в словарь
    """
    time_calculation = {
        'month': 2_592_000, 'weekly': 604800,
        'day': 86400, 'hour': 3600, 
        'minute': 60, 'second': 1
    }
    time_dict = {
        'month': 0, 'weekly': 0,
        'day': 0, 'hour': 0, 
        'minute': 0, 'second': 0
    }

    for tp, unit in time_calculation.items():
        tt = seconds // unit

        if tt:
            seconds -= tt * unit
            time_dict[tp] = tt

    return time_dict 

def seconds_to_str(seconds: int, lang: str='en', mini: bool=False, max_lvl='second'):
    """ Преобразует число секунд в строку
       Example:
       > seconds=10000 lang='ru'
       > 1 день 2 минуты 41 секунда
       
       > seconds=10000 lang='ru' mini=True
       > 1д. 2мин. 41сек.
       
       max_lvl - Определяет максимальную глубину погружения
       Example:
       > seconds=3900 max_lvl=second
       > 1ч. 5м.
       
       > seconds=3900 max_lvl=hour
       > 1ч.
    """
    if seconds == 'inf': return "♾"
    if seconds < 0: seconds = 0

    time_format = dict(get_data('time_format', lang)) # type: dict
    result = ''

    def ending_w(time_type: str, unit: int) -> str:
        """Опредеяет окончание для слова
        """
        if mini: return time_format[time_type][3]

        else:
            result = ''
            if unit < 11 or unit > 14:
                unit = unit % 10

            if unit == 1:
                result = time_format[time_type][0]
            elif unit > 1 and unit <= 4:
                result = time_format[time_type][1]
            elif unit > 4 or unit == 0:
                result = time_format[time_type][2]
        return result

    data = seconds_to_time(seconds=seconds)
    for tp, unit in data.items():
        if unit:
            if mini:
                result += f'{unit}{ending_w(tp, unit)} '
            else:
                result += f'{unit} {ending_w(tp, unit)} '
        if max_lvl == tp: break

    if result[:-1]: return result[:-1]
    else: 
        result = '0'
        if max_lvl != 'seconds': 
            return f'0 {time_format[max_lvl][3]}'
        return result


def near_key_number(n: int, data: dict, alternative: int=1):
    """ Находит ближайшее меньшее число среди ключей.
       В словаре ключи должны быть str(числами), в порядке убывания

       Пример:
        n=6 data={'10': 'много', '5': 'средне', '2': 'мало'}
        >>> 5, средне #key, value

        alterantive - если не получилось найти ключ, будет возвращён
    """
    for key in data.keys():
        if int(key) <= n: return data[key]
    return data[alternative]

def crop_text(text: str, unit: int=10, postfix: str='...'):
    """Обрезает текст и добавляет postfix в конце, 
       если текст больше чем unit + len(postfix)
    """
    if len(text) > unit + len(postfix):
        return text[:unit] + postfix
    else: return text

def filling_with_emptiness(lst: list, horizontal: int, vertical: int):
    """ Заполняет пустые элементы страницы для сохранения структуры
    """
    for i in lst:
        if len(i) != vertical:
            for _ in range(vertical - len(i)):
                i.append([' ' for _ in range(horizontal)])
    return lst

def chunk_pages(options: dict, horizontal: int=2, vertical: int=3):
    """ Чанкует страницы и добавляем пустые элементы для сохранения структуры
    """
    if options:
        pages = chunks(chunks(list(options.keys()), horizontal), vertical)
    else: pages = [[]]
    pages = filling_with_emptiness(pages, horizontal, vertical)
    return pages

def encoder_text(text: str, each: int = 5):
    text_list, a = text.split(' '), 0

    for word in text_list:
        if len(word) > 1:
            a += 1
            if a >= each:
                a = 0
                if random.randint(0, 1):
                    text_list[text_list.index(word)] = f'<span class="tg-spoiler">{word}</span>'
                else: text_list[text_list.index(word)] = '###'

    ret_text = ''
    for i in text_list: ret_text += i + ' '

    return str(ret_text)

def count_elements(lst: list) -> str:
    dct = {}
    for i in lst: dct[i] = dct.get(i, 0) + 1

    text_list = []
    for key, value in dct.items(): text_list.append(f'{key} x{value}')
    return ', '.join(text_list)

def str_to_seconds(text: str):
    """ Преобразует текст в секнудны
    """
    words = text.split()
    seconds = 0

    for i in words:
        mn = 1
        if len(i) == 1 and i.isdigit(): seconds += int(i)

        if len(i) > 1:
            if type(i[-1]) == str:
                number = i[:-1]

                if number.isdigit():
                    if i[:-1] == 's': mn = 1
                    elif i[-1] == 'm': mn = 60
                    elif i[-1] == 'h': mn = 3600
                    elif i[-1] == 'd': mn = 86400
                    elif i[-1] == 'w': mn = 86400 * 7

                    seconds += int(number) * mn
    return seconds