from io import BytesIO
import random
import re
import string
from typing import Union

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, User, KeyboardButton

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from bot.const import GAME_SETTINGS
from bot.modules.localization import get_data
from aiogram.types import BufferedInputFile

from bot.modules.logs import log

import html as _html

def escape_markdown(content: str) -> str:
    """ Экранирует спецсимволы в строке для безопасности HTML.
    """
    if not isinstance(content, str):
        return str(content) if content is not None else ""
    return _html.escape(content)

def escape_html(content: str) -> str:
    """ Экранирует спецсимволы в строке для безопасности HTML.
    """
    if not isinstance(content, str):
        return str(content) if content is not None else ""
    return _html.escape(content) 

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


def parse_custom_emoji_markdown(text: str) -> tuple[str, str | None, str | None]:
    """ Parses custom emoji formats from button text:
        - '<tg-emoji emoji-id="123">alt</tg-emoji> Text'
        - '{custom_emoji:name} Text'
        - '![alt](tg://emoji?id=123) Text'
        returns (clean_text, emoji_id, alt_emoji)
    """
    import re
    if not isinstance(text, str):
        return str(text), None, None

    emoji_id = None
    alt_emoji = None

    # 1. Check <tg-emoji emoji-id="123">alt</tg-emoji>
    def replace_tg_emoji(m):
        nonlocal emoji_id, alt_emoji
        emoji_id = m.group(1)
        alt_emoji = m.group(2)
        return alt_emoji

    text_cleaned = re.sub(r'<tg-emoji emoji-id="(\d+)">(.*?)</tg-emoji>', replace_tg_emoji, text)

    # 2. Check {custom_emoji:name} or {custom_emoji:name:index}
    def replace_custom_placeholder(m):
        nonlocal emoji_id, alt_emoji
        emoji_name = m.group(1)
        from bot.const import CUSTOM_EMOJIS, ITEMS_CUSTOM_EMOJIS
        data = CUSTOM_EMOJIS.get(emoji_name) or ITEMS_CUSTOM_EMOJIS.get(emoji_name) or {}
        if data.get('id'):
            emoji_id = str(data['id'])
        alts = data.get('alternatives', [])
        alt_emoji = alts[0] if alts else ""
        return alt_emoji

    text_cleaned = re.sub(r'\{custom_emoji:([^:}]+)(?::\d+)?\}', replace_custom_placeholder, text_cleaned)

    # 3. Check ![alt](tg://emoji?id=123)
    def replace_md_emoji(m):
        nonlocal emoji_id, alt_emoji
        alt_emoji = m.group(1)
        emoji_id = m.group(2)
        return alt_emoji

    text_cleaned = re.sub(r'\!\[(.*?)\]\(tg://emoji\?id=(\d+)\)', replace_md_emoji, text_cleaned)

    text_cleaned = re.sub(r'\s+', ' ', text_cleaned).strip()
    if not text_cleaned:
        text_cleaned = " "

    return text_cleaned, emoji_id, alt_emoji


def strip_emoji_prefix(text: str) -> str:
    """Убирает простые статусные эмодзи (типа ❌, 🟢, 🗑, 🚫) из начала текста."""
    if not text:
        return text
    # Список известных статусных эмодзи
    chars_to_strip = "❌🟢🗑✅⚠️ℹ️🍔🥚👒⚒🪵🚫⏮⏭🔎🔃⚙️♻️◀▶🔥🎁❤ "
    cleaned = text
    while cleaned and cleaned[0] in chars_to_strip:
        cleaned = cleaned[1:]
    cleaned = cleaned.strip()
    return cleaned if cleaned else text


def remove_alt_emoji_from_text(text: str, alt_emoji: str | None) -> str:
    """Убирает стандартный эмодзи из текста кнопки, если к кнопке прикреплен иконкой кастомный премиум-эмодзи."""
    if not text:
        return text
    if alt_emoji:
        alt_stripped = alt_emoji.strip()
        if alt_stripped and text.startswith(alt_stripped):
            text = text[len(alt_stripped):].lstrip()
        elif alt_emoji and text.startswith(alt_emoji):
            text = text[len(alt_emoji):].lstrip()
        elif alt_stripped:
            parts = text.split(maxsplit=1)
            if parts and parts[0] == alt_stripped:
                text = parts[1] if len(parts) > 1 else ""
    return text.strip() or " "


def parse_custom_emoji_placeholder(text: str) -> tuple[str, str | None, str | None]:
    """Парсит плейсхолдер {custom_emoji:name} или {custom_emoji:name:index} из текста кнопки.
    Возвращает (clean_text, emoji_key, alt_emoji).
    alt_emoji — первый fallback эмодзи, уже проставленный в тексте t().
    """
    import re
    m = re.search(r'\{custom_emoji:([^:}]+)(?::(\d+))?\}', text)
    if m:
        emoji_key = m.group(1)
        clean_text = text[:m.start()].rstrip() + text[m.end():].lstrip()
        return clean_text.strip() or " ", emoji_key, None
    return text, None, None


def resolve_button_data(text: str, custom_emoji_key: str | None, is_premium: bool = True) -> tuple[str, str | None]:
    """ Разрешает ключ кастомного эмодзи (название из custom_emojis.json или raw ID)
        в кортеж (final_text, resolved_emoji_id).

        Если у владельца бота есть Telegram Premium:
            - Возвращает переданный текст без изменений и ID эмодзи.
        Если у владельца бота нет Telegram Premium:
            - Добавляет текстовый fallback-эмодзи в начало текста и возвращает None в качестве ID эмодзи.
    """
    text_str = str(text)
    if not text_str or text_str.strip() == "":
        text_str = " "

    if not custom_emoji_key:
        return text_str, None

    text_str = strip_emoji_prefix(text_str)
    if not text_str or text_str.strip() == "":
        text_str = " "

    try:
        from bot.const import CUSTOM_EMOJIS
        from bot.modules.localization import owner_premium_cache, update_owner_premium_bg
        import time

        # Sync/trigger premium check if needed
        if time.time() - owner_premium_cache["last_check"] > 86400:
            update_owner_premium_bg()

        has_premium = owner_premium_cache["is_premium"] and is_premium

        # 1. Resolve from CUSTOM_EMOJIS mapping
        if custom_emoji_key in CUSTOM_EMOJIS:
            emoji_data = CUSTOM_EMOJIS[custom_emoji_key]
            emoji_id = emoji_data.get('id')
            alternatives = emoji_data.get('alternatives', [])
            alt_emoji = alternatives[0] if alternatives else ""

            if has_premium and emoji_id:
                return text_str, str(emoji_id)
            else:
                final_text = f"{alt_emoji} {text_str}" if alt_emoji else text_str
                if not final_text or final_text.strip() == "":
                    final_text = " "
                return final_text, None

        # 2. Resolve from ITEMS_CUSTOM_EMOJIS mapping
        try:
            from bot.const import ITEMS_CUSTOM_EMOJIS
            if custom_emoji_key in ITEMS_CUSTOM_EMOJIS:
                emoji_data = ITEMS_CUSTOM_EMOJIS[custom_emoji_key]
                emoji_id = emoji_data.get('id')
                alternatives = emoji_data.get('alternatives', [])
                alt_emoji = alternatives[0] if alternatives else ""

                if has_premium and emoji_id:
                    return text_str, str(emoji_id)
                else:
                    final_text = f"{alt_emoji} {text_str}" if alt_emoji else text_str
                    if not final_text or final_text.strip() == "":
                        final_text = " "
                    return final_text, None
        except Exception:
            pass

        # 3. If it's a raw digit ID
        if str(custom_emoji_key).isdigit():
            if has_premium:
                return text_str, str(custom_emoji_key)
            else:
                return text_str, None
    except Exception:
        pass

    return text_str, None


def list_to_keyboard(buttons: list, row_width: int = 3, 
                     resize_keyboard: bool = True, one_time_keyboard = None,
                     is_premium: bool = True):
    """ Превращает список со списками в объект клавиатуры.
        Поддерживает передачу как строк, так и словарей с параметрами кнопок.

        Параметры словаря кнопки (dict):
            - text (str): Текст кнопки.
            - style (str): Стиль кнопки ('primary', 'success', 'danger').
            - custom_emoji_id / icon_custom_emoji_id (str): Название эмодзи из custom_emojis.json
              (например, 'forbidden', 'trash', 'thumbs_up') или числовой Telegram custom_emoji_id.
              Если у создателя бота нет Premium, автоматически подставит текстовый fallback-эмодзи в начало текста.

        Example:
            butttons = [ 
                ['привет'], 
                [{"text": "Отмена", "style": "danger", "custom_emoji_id": "forbidden"}] 
            ]

        >      привет
          [🚫 Отмена] (красная кнопка со значком)
    """
    builder = ReplyKeyboardBuilder()

    def make_button(item):
        if isinstance(item, KeyboardButton):
            return item
        elif isinstance(item, dict):
            text = item.get("text", "")
            style = item.get("style")
            custom_emoji_key = item.get("custom_emoji_id") or item.get("icon_custom_emoji_id")
            
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
            if emoji_id:
                text = clean_text
                if not custom_emoji_key:
                    custom_emoji_key = emoji_id
            
            # Bypass premium check for items custom emoji IDs (digit strings)
            if custom_emoji_key and str(custom_emoji_key).isdigit():
                text, icon_custom_emoji_id = text, str(custom_emoji_key)
            else:
                text, icon_custom_emoji_id = resolve_button_data(text, custom_emoji_key, is_premium=is_premium)
            
            if icon_custom_emoji_id is not None:
                text = remove_alt_emoji_from_text(text, alt_emoji)

            kwargs = {"text": text}
            if style is not None:
                kwargs["style"] = style
            if icon_custom_emoji_id is not None:
                kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
            return KeyboardButton(**kwargs)
        else:
            text = str(item)
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
            if emoji_id:
                # Bypass premium check for items custom emoji IDs (digit strings)
                if emoji_id.isdigit():
                    text, icon_custom_emoji_id = clean_text, emoji_id
                else:
                    text, icon_custom_emoji_id = resolve_button_data(clean_text, emoji_id, is_premium=is_premium)

                if icon_custom_emoji_id is not None:
                    text = remove_alt_emoji_from_text(text, alt_emoji)

                kwargs = {"text": text}
                if icon_custom_emoji_id is not None:
                    kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
                return KeyboardButton(**kwargs)
            else:
                return KeyboardButton(text=text)

    for line in buttons:
        if isinstance(line, list):
            builder.row(*[make_button(i) for i in line], width=row_width)
        else:
            builder.row(make_button(line), width=row_width)

    return builder.as_markup(row_width=row_width, resize_keyboard=resize_keyboard, one_time_keyboard=one_time_keyboard)


def list_to_inline(buttons: list, row_width: int = 3, is_premium: bool = True) -> InlineKeyboardMarkup:
    """ Превращает список со списками в объект inlineKeyboard.
        Поддерживает стандартный формат {'текст': 'callback_data'} и расширенный.

        Параметры расширенного формата (значение ключа - словарь, либо отдельный словарь с ключом 'text'):
            - text (str): Текст кнопки (при передаче отдельного словаря).
            - callback_data (str): Данные колбэка.
            - style (str): Стиль кнопки ('primary', 'success', 'danger').
            - custom_emoji_id / icon_custom_emoji_id (str): Название эмодзи из custom_emojis.json
              или числовой Telegram custom_emoji_id. Если у создателя бота нет Premium,
              автоматически подставит текстовый fallback-эмодзи перед текстом кнопки.
            - url (str): Ссылка для перехода.
            - web_app (WebAppInfo): WebApp данные.

        Example:
            # Вариант 1 (вложенный словарь в старом стиле):
            buttons = [
                {"Удалить": {"callback_data": "delete", "style": "danger", "custom_emoji_id": "trash"}}
            ]
            
            # Вариант 2 (список словарей кнопок):
            buttons = [
                [{"text": "Удалить", "callback_data": "delete", "style": "danger", "custom_emoji_id": "trash"}]
            ]
    """
    inline = InlineKeyboardBuilder()

    def make_inline_button(item):
        if isinstance(item, InlineKeyboardButton):
            return item
        elif isinstance(item, dict):
            text = item.get("text", "")
            callback_data = item.get("callback_data", "None")
            style = item.get("style")
            custom_emoji_key = item.get("custom_emoji_id") or item.get("icon_custom_emoji_id")
            url = item.get("url")
            web_app = item.get("web_app")
            
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
            if emoji_id:
                text = remove_alt_emoji_from_text(clean_text, alt_emoji)
                if not custom_emoji_key:
                    custom_emoji_key = emoji_id
            
            text, icon_custom_emoji_id = resolve_button_data(text, custom_emoji_key, is_premium=is_premium)
            
            kwargs = {"text": text}
            if callback_data is not None:
                kwargs["callback_data"] = callback_data
            if url is not None:
                kwargs["url"] = url
            if web_app is not None:
                kwargs["web_app"] = web_app
            if style is not None:
                kwargs["style"] = style
            if icon_custom_emoji_id is not None:
                kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
            return InlineKeyboardButton(**kwargs)
        else:
            text = str(item)
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
            if emoji_id:
                text, icon_custom_emoji_id = resolve_button_data(remove_alt_emoji_from_text(clean_text, alt_emoji), emoji_id, is_premium=is_premium)
                kwargs = {"text": text, "callback_data": "None"}
                if icon_custom_emoji_id is not None:
                    kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
                return InlineKeyboardButton(**kwargs)
            else:
                return InlineKeyboardButton(text=text, callback_data="None")

    for line in buttons:
        if isinstance(line, list):
            row_buttons = []
            for item in line:
                if isinstance(item, dict) and "text" not in item:
                    # Old style dict mapping text to callback/properties
                    for text, val in item.items():
                        kwargs = {}
                        if isinstance(val, dict):
                            callback_data = val.get("callback_data", "None")
                            style = val.get("style")
                            custom_emoji_key = val.get("custom_emoji_id") or val.get("icon_custom_emoji_id")
                            url = val.get("url")
                            web_app = val.get("web_app")
                            
                            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
                            if emoji_id:
                                text = remove_alt_emoji_from_text(clean_text, alt_emoji)
                                if not custom_emoji_key:
                                    custom_emoji_key = emoji_id
                            
                            text, icon_custom_emoji_id = resolve_button_data(text, custom_emoji_key, is_premium=is_premium)
                            
                            kwargs["text"] = text
                            if callback_data is not None:
                                kwargs["callback_data"] = callback_data
                            if url is not None:
                                kwargs["url"] = url
                            if web_app is not None:
                                kwargs["web_app"] = web_app
                            if style is not None:
                                kwargs["style"] = style
                            if icon_custom_emoji_id is not None:
                                kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
                        else:
                            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
                            if emoji_id:
                                text, icon_custom_emoji_id = resolve_button_data(clean_text, emoji_id, is_premium=is_premium)
                                kwargs["text"] = text
                                if icon_custom_emoji_id is not None:
                                    kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
                            else:
                                kwargs["text"] = str(text)
                            kwargs["callback_data"] = str(val)
                        row_buttons.append(InlineKeyboardButton(**kwargs))
                else:
                    row_buttons.append(make_inline_button(item))
            inline.row(*row_buttons, width=row_width)
        elif isinstance(line, dict):
            if "text" in line:
                inline.row(make_inline_button(line), width=row_width)
            else:
                row_buttons = []
                for text, val in line.items():
                    kwargs = {}
                    if isinstance(val, dict):
                        callback_data = val.get("callback_data", "None")
                        style = val.get("style")
                        custom_emoji_key = val.get("custom_emoji_id") or val.get("icon_custom_emoji_id")
                        url = val.get("url")
                        web_app = val.get("web_app")
                        
                        clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
                        if emoji_id:
                            text = remove_alt_emoji_from_text(clean_text, alt_emoji)
                            if not custom_emoji_key:
                                custom_emoji_key = emoji_id
                        
                        text, icon_custom_emoji_id = resolve_button_data(text, custom_emoji_key, is_premium=is_premium)
                        
                        kwargs["text"] = text
                        if callback_data is not None:
                            kwargs["callback_data"] = callback_data
                        if url is not None:
                            kwargs["url"] = url
                        if web_app is not None:
                            kwargs["web_app"] = web_app
                        if style is not None:
                            kwargs["style"] = style
                        if icon_custom_emoji_id is not None:
                            kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
                    else:
                        clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(text)
                        if emoji_id:
                            text, icon_custom_emoji_id = resolve_button_data(remove_alt_emoji_from_text(clean_text, alt_emoji), emoji_id, is_premium=is_premium)
                            kwargs["text"] = text
                            if icon_custom_emoji_id is not None:
                                kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
                        else:
                            kwargs["text"] = str(text)
                        kwargs["callback_data"] = str(val)
                    row_buttons.append(InlineKeyboardButton(**kwargs))
                inline.row(*row_buttons, width=row_width)
        elif isinstance(line, InlineKeyboardButton):
            inline.row(line, width=row_width)
        else:
            inline.row(make_inline_button(line), width=row_width)

    return inline.as_markup(row_width=row_width)


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


def near_key_number(n: int, data: dict, alternative: int=1):
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
    if end is None or not isinstance(end, (int, float)) or end <= 0:
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
    try:
        with image.convert('RGB') as converted:
            converted.save(photoBuffer, extension, quality=quality)
    finally:
        try:
            image.close()
        except Exception:
            pass
    photoBuffer.seek(0)
    data = photoBuffer.read()
    photoBuffer.close()

    return BufferedInputFile(data, filename=f"DinoGochi.{extension}")


def md_to_html(text: str) -> str:
    if not isinstance(text, str):
        return text
    from bot.modules.localization import resolve_custom_emojis
    return resolve_custom_emojis(text)

def format_team_members(members, lang):
    from bot.modules.items.item import get_name
    from bot.modules.localization import t
    lines = []
    for p in members:
        eq = []
        if p.get("weapon"):
            eq.append(get_name(p['weapon'], lang))
        if p.get("shield"):
            eq.append(get_name(p['shield'], lang))
        eq = [item for item in eq if item]
        eq_str = f"\n  ({' '.join(eq)})" if eq else ""
        
        name = p['name']
        if p.get("type") == "mob" and p.get("mob_id"):
            translated = t(f"mobs.{p['mob_id']}.name", lang)
            if "mobs." not in translated:
                name = translated
            else:
                name = p['mob_id'].capitalize()
            mob_emoji = t(f"mobs.{p['mob_id']}.emoji", lang)
            if "mobs." in mob_emoji or not mob_emoji:
                mob_emoji = "👾"
            name = f"{mob_emoji} {name}"
        else:
            for suffix in [" (X)", " (Y)"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
                
        cleaned_name = name.replace('_', ' ')
        lines.append(f"• <b>{cleaned_name}</b> (HP: {int(p['hp'])}/{int(p['max_hp'])}){eq_str}")
    return "\n".join(lines)





