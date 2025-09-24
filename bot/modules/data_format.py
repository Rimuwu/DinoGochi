from io import BytesIO
import random
import re
import string
from typing import Any, Union

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, User, KeyboardButton

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from bot.const import GAME_SETTINGS
from bot.dataclasess.random_dict import RandomDict
from bot.modules.localization import get_data
from aiogram.types import BufferedInputFile

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

def random_dict(data: dict | int | RandomDict) -> int:
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

    if isinstance(data, RandomDict):
        data = data.__dict__

    if isinstance(data, dict):
        if "type" not in data: return data['act']

        elif data["type"] == "static": return data['act']

        elif data["type"] == "random":
            if data['min'] < data['max']:
                return random.randint(data['min'], data['max'])
            else: return data['min']

        elif data["type"] == "choice":
            if data['act']: return random.choice(data['act'])
            else: return 0

    elif isinstance(data, int): return data
    return 0


def list_to_keyboard(buttons: list, row_width: int = 3, 
                     resize_keyboard: bool = True, one_time_keyboard = None):
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
    builder = ReplyKeyboardBuilder()

    for line in buttons:
        if type(line) == list:
            builder.row(*[KeyboardButton(text=i) for i in line], width=row_width)
        else:
            builder.row(*[KeyboardButton(text=str(line))], width=row_width)

    return builder.as_markup(row_width=row_width, resize_keyboard=resize_keyboard, one_time_keyboard=one_time_keyboard)

def list_to_inline(buttons: list, row_width: int = 3, 
    as_markup: bool = True) -> InlineKeyboardMarkup:
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
    inline = InlineKeyboardBuilder()

    for line in buttons:
        if type(line) == dict:
            inline.row(*[InlineKeyboardButton(text=i, callback_data=j) for i, j in line.items()], width=row_width)
        else:
            inline.add(InlineKeyboardButton(text=str(line), callback_data='None'))

    if as_markup:
        return inline.as_markup(row_width=row_width)
    return inline

def user_name_from_telegram(user: User, username: bool = True) -> str:
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
        'year': 31_536_000,
        'month': 2_592_000, 'weekly': 604800,
        'day': 86400, 'hour': 3600, 
        'minute': 60, 'second': 1
    }
    time_dict = {
        'year': 0,
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

def seconds_to_str(seconds: int, lang: str='en', mini: bool=False, max_lvl='auto'):
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
    if max_lvl == 'auto':
        max_lvl, a, lst_n = 'second', 0, 'second'

        for tp, unit in data.items():
            if unit: 
                a += 1
                lst_n = tp
            if a >= 3:
                max_lvl = tp
                break

        if a < 3: max_lvl = lst_n

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
        if max_lvl != 'second': 
            return f'0 {time_format[max_lvl][3]}'
        return result


def near_key_number(n: int, data: dict, alternative: Any = 1):
    """ Находит ближайшее меньшее число среди ключей.
       В словаре ключи должны быть str(числами), в порядке убывания

       Пример:
        n=6 data={'10': 'много', '5': 'средне', '2': 'мало'}
        >>> 5, средне #key, value

        alterantive - если не получилось найти ключ, будет возвращён
    """
    sorted_dict = dict(sorted(
    ((int(key), value) for key, value in data.items() if isinstance(key, (int, str))),
        key=lambda item: item[0],
        reverse=True
    ))

    for key in sorted_dict.keys():
        if int(key) <= n: return sorted_dict[key]
    return sorted_dict[alternative]

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

def item_list(items: list[dict]):
    """ Добавляет к каждому предмету ключ count c количеством 
    """
    res, individual = [], []

    for i in items:
        if i not in individual:
            individual.append(i.copy())

            if 'count' not in i: i['count'] = items.count(i)
            res.append(i)

    return res

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

def random_data(data: Union[int, str, list, dict, None]):

    if isinstance(data, int): 
        return data

    elif isinstance(data, str): 
        return data

    elif isinstance(data, list): 
        return data

    elif isinstance(data, dict): 

        if 'random-int' in data.keys():
            # В данных должен быть список типа [min, max]
            return random.randint(*data['random-int'])

        elif 'random-choice' in data.keys():
            # В данных должен быть список с Х элементами из списка
            return random.choice(data['random-choice'])

    else: return data

def transform(var: float, max_var: int, max_unit: Union[int, float]) -> int:
    """ 
    Функция transform(var: float, max_var: int, max_unit: int) -> float предназначена для преобразования числа var, находящегося в диапазоне от 0 до max_var, в новое значение на основе указанного значения max_unit.

    ### Параметры:
    - var: число от 0 до max_var, которое нужно преобразовать (например, текущее значение).
    - max_var: максимальное значение диапазона для var (например, 20).
    - max_unit: значение, которое соответствует полному диапазону (например, 100).

    ### Описание работы:
    1. Функция вычисляет, какой процент от значения max_var составляет var.
    2. Умножает этот процент на max_unit, чтобы получить конечный результат.

    ### Возвращаемое значение:
    Функция возвращает преобразованное значение, которое показывает, какое число соответствует указанному проценту от max_unit.

    ### Пример использования:
    Если var = 10, max_var = 20, а max_unit = 100, функция вернет 50, поскольку 10 — это 50% от 20.
    """
    # Вычисляем процент от max_var
    percentage = var / max_var if max_var != 0 else 0

    # Возвращаем соответствующее число от max_unit на основе вычисленного процента
    result = percentage * max_unit

    return round(result)

def distribute_number(number: int, ratios: list[int]):
    """
    Функция distribute_number принимает два аргумента: целое число и список со значениями (соотношениями). Она распределяет данное число по элементам списка в соответствии с их пропорциями. 

    ### Принцип работы:
    1. Сначала вычисляется сумма всех значений в списке (соотношениях).
    2. Затем для каждого элемента списка рассчитывается доля от заданного числа, пропорционально его значению.
    3. В результате возвращается список, содержащий распределённые значения, округлённые до целых чисел.

    ### Пример:
    Если на вход подаётся число 37 и список [15, 9, 1], функция вернёт список [22, 13, 2], что соответствует пропорциональному распределению числа 37 согласно заданным соотношениям.
    """
    total_ratios = sum(ratios)  # Суммируем все части соотношения
    distribution = [(ratio / total_ratios) * number for ratio in ratios]  # Распределяем число
    return [round(value) for value in distribution]  # Округляем результаты

def progress_bar(now, end, col_emoji, 
                 activ_emoji, passive_emoji,
                 start_text = '[', end_text = ']',
                 percent_visible: bool = True):
    """
    # Пример использования
        now = 4
        end = 12
        col_emoji = 10
        activ_emoji = '🔵'
        passive_emoji = '⚪️'

    >>> 33% [🔵🔵🔵⚪️⚪️⚪️⚪️⚪️⚪️⚪️] 100%
    """
    if end <= 0:
        return "Invalid end time. It must be greater than 0."

    # Вычисляем процент завершения
    percent_complete = min(int((now / end) * 100), 100)
    
    # Вычисляем количество активных и неактивных эмодзи
    progress_length = int((now / end) * col_emoji)  # количество активных эмодзи
    if progress_length > col_emoji:
        progress_length = col_emoji  # ограничиваем максимальным количеством эмодзи
    
    active_part = activ_emoji * progress_length
    passive_part = passive_emoji * (col_emoji - progress_length)

    # Формируем строку прогресс бара с процентом и 100% в конце
    bar = f'{start_text}{active_part}{passive_part}{end_text}'
    if percent_visible:
        return f"{percent_complete}% {bar} 100%" 
    return bar

def deepcopy(original):
    if isinstance(original, dict):
        # Создаем новый словарь
        copy_dict = {}
        for key, value in original.items():
            # Рекурсивно копируем ключи и значения
            copy_dict[deepcopy(key)] = deepcopy(value)
        return copy_dict
    elif isinstance(original, list):
        # Если это список, создаем новый список
        return [deepcopy(item) for item in original]
    elif isinstance(original, set):
        # Если это множество, создаем новое множество
        return {deepcopy(item) for item in original}
    elif isinstance(original, tuple):
        # Если это кортеж, возвращаем новый кортеж
        return tuple(deepcopy(item) for item in original)
    else:
        # Если это примитивное значение, просто возвращаем его
        return original

def pil_image_to_file(image, extension='JPEG', quality='web_low'):
    photoBuffer = BytesIO()
    image.convert('RGB').save(photoBuffer, extension, quality=quality)
    photoBuffer.seek(0)

    return BufferedInputFile(photoBuffer.read(), filename=f"DinoGochi.{extension}")

