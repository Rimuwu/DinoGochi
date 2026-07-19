from bot.models.user import Lang
from bot.models.user import User
# Модуль загрузки локлизации

import json
import os
from typing import Any
from bot.modules.logs import log
from bot.dbmanager import mongo_client

languages = {}
available_locales = []

import re

def load() -> None:
    """Загрузка локализации"""

    for filename in os.listdir("./bot/localization"):
        if filename.endswith(".json"):
            with open(f'./bot/localization/{filename}', encoding='utf-8') as f:
                languages_f = json.load(f)

            for l_key in languages_f.keys():
                available_locales.append(l_key)
                languages[l_key] = languages_f[l_key]

    log(f"Загружено {len(languages.keys())} файла(ов) локализации.", 1)

def reload() -> None:
    """Перезагрузка локализации без downtime"""
    new_languages = {}
    new_locales = []
    for filename in os.listdir("./bot/localization"):
        if filename.endswith(".json"):
            with open(f'./bot/localization/{filename}', encoding='utf-8') as f:
                languages_f = json.load(f)

            for l_key in languages_f.keys():
                new_locales.append(l_key)
                new_languages[l_key] = languages_f[l_key]

    global languages, available_locales
    languages.clear()
    languages.update(new_languages)
    available_locales.clear()
    available_locales.extend(new_locales)
    log(f"Перезагружено {len(languages.keys())} файла(ов) локализации.", 1)

def alternative_language(lang: str):
    languages = {
        'ua': 'ru'
    }
    try:
        if lang in languages: return languages[lang]
    except:
        log(f"Not found lang {lang}", 3)
    return lang

from bot.config import conf
owner_premium_cache = {
    "is_premium": True if getattr(conf, 'debug', False) else False,
    "last_check": 0
}

def update_owner_premium_bg():
    import time
    from bot.config import conf
    if not conf.bot_devs:
        return
    owner_id = conf.bot_devs[0]
    
    async def _update():
        try:
            from bot.exec import bot
            is_premium = False
            
            # 1. Try to get chat member from the bot's configured group
            if getattr(conf, 'bot_group_id', None):
                try:
                    member = await bot.get_chat_member(chat_id=conf.bot_group_id, user_id=owner_id)
                    is_premium = getattr(member.user, 'is_premium', False)
                except Exception:
                    pass
            
            # 2. Fallback to get_chat (which normally lacks is_premium, but handles any unexpected API behaviors)
            if not is_premium:
                try:
                    chat = await bot.get_chat(owner_id)
                    is_premium = getattr(chat, 'is_premium', False)
                    if not is_premium:
                        is_premium = bool(getattr(chat, 'emoji_status_custom_emoji_id', None)) or bool(getattr(chat, 'background_custom_emoji_id', None))
                except Exception:
                    pass

            if getattr(conf, 'debug', False):
                is_premium = True

            if is_premium is None:
                is_premium = False
            owner_premium_cache["is_premium"] = bool(is_premium)
            owner_premium_cache["last_check"] = time.time()
        except Exception as e:
            from bot.modules.logs import log
            log(f"Error checking owner premium in background: {e}", 3)
            owner_premium_cache["last_check"] = time.time() - 86400 + 60

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(_update())
    except RuntimeError:
        pass

def resolve_custom_emojis(text: str) -> str:
    if not isinstance(text, str):
        return text
    
    import time
    if time.time() - owner_premium_cache["last_check"] > 86400:
        update_owner_premium_bg()
        
    has_premium = owner_premium_cache["is_premium"]
    from bot.const import CUSTOM_EMOJIS
    
    standalone_match = re.match(r'^custom_emoji:([^:]+)(?::(\d+))?$', text)
    if standalone_match:
        emoji_name = standalone_match.group(1)
        alt_index_str = standalone_match.group(2)
        alt_index = int(alt_index_str) if alt_index_str is not None else 0
        
        emoji_data = CUSTOM_EMOJIS.get(emoji_name, {})
        emoji_id = emoji_data.get('id')
        alternatives = emoji_data.get('alternatives', [])
        
        if alternatives:
            alt_emoji = alternatives[alt_index] if alt_index < len(alternatives) else alternatives[0]
        else:
            alt_emoji = ""
            
        if has_premium and emoji_id:
            return f"![{alt_emoji}](tg://emoji?id={emoji_id})"
        return alt_emoji

    matches = list(re.finditer(r'\{custom_emoji:([^:}]+)(?::(\d+))?\}', text))
    for match in matches:
        emoji_name = match.group(1)
        alt_index_str = match.group(2)
        alt_index = int(alt_index_str) if alt_index_str is not None else 0
        
        emoji_data = CUSTOM_EMOJIS.get(emoji_name, {})
        emoji_id = emoji_data.get('id')
        alternatives = emoji_data.get('alternatives', [])
        
        if alternatives:
            alt_emoji = alternatives[alt_index] if alt_index < len(alternatives) else alternatives[0]
        else:
            alt_emoji = ""
            
        if has_premium and emoji_id:
            resolved = f"![{alt_emoji}](tg://emoji?id={emoji_id})"
        else:
            resolved = alt_emoji
            
        text = text.replace(match.group(0), resolved, 1)
        
    return text

def get_item_localization(item_id: str, locale: str) -> tuple[str, str]:
    """Returns (name, emoji) for the given item_id and locale."""
    locale = alternative_language(locale)
    if locale not in available_locales:
        locale = 'en'
        
    items_data = languages.get(locale, {}).get('items_names', {})
    item_info = items_data.get(item_id)
    
    if not item_info or not isinstance(item_info, dict):
        items_data = languages.get('en', {}).get('items_names', {})
        item_info = items_data.get(item_id)
        
    if not item_info or not isinstance(item_info, dict):
        return (item_id, "")
        
    name = item_info.get('name', item_id)
    emoji = item_info.get('emoji', "")
    return name, emoji

def format_item_name(name: str, emoji: str) -> str:
    if emoji:
        return f"{emoji} {name}"
    return name

def resolve_translate_urls(data: Any, locale: str) -> Any:
    """
    Рекурсивно проходит по всем ключам локализации, ищет текстовые значения,
    заменяет {translate_url:...} на переводы.
    """
    if isinstance(data, dict):
        return {k: resolve_translate_urls(v, locale) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_translate_urls(item, locale) for item in data]
    elif isinstance(data, str):
        text = data
        matches = list(re.finditer(r'\{translate_url:([^}]+)\}', text))
        for match in matches:
            inner_key = match.group(1)
            translated = str(get_data(inner_key, locale))
            text = text.replace(match.group(0), translated, 1)

        # Resolve {item_name:item_id}
        matches = list(re.finditer(r'\{item_name:([^}]+)\}', text))
        for match in matches:
            item_id = match.group(1)
            name, emoji = get_item_localization(item_id, locale)
            translated = format_item_name(name, emoji)
            text = text.replace(match.group(0), translated, 1)

        # Resolve {item_emoji:item_id}
        matches = list(re.finditer(r'\{item_emoji:([^}]+)\}', text))
        for match in matches:
            item_id = match.group(1)
            _, emoji = get_item_localization(item_id, locale)
            text = text.replace(match.group(0), emoji, 1)

        text = resolve_custom_emojis(text)
        return text
    else:
        return data

def get_data(key: str, locale: str | None) -> Any:
    """Возвращает данные локализации

    Args:
        key (str): ключ
        locale (str, optional): язык. Defaults to "en".

    Returns:
        str | dict: возвращаемое
    """
    if not locale: locale = 'en'
    locale = alternative_language(locale)
    if locale not in available_locales:
        locale = 'en' # Если язык не найден, установить тот что точно есть

    localed_data = languages[locale]

    for way_key in key.split('.'):
        if way_key.isdigit() and type(localed_data) == list:
            way_key = int(way_key)

        if way_key in localed_data or type(way_key) == int:
            if way_key or way_key == 0:
                try:
                    localed_data = localed_data[way_key] 
                except Exception as e:
                    log(f'localiztion.get_data {e}\nway_key - {way_key} locale - {locale} key - {key}', 4)
        else:
            log(f'Ключ {key} ({locale}) не найден!', 4)
            pat = languages.get(locale, {}).get("no_text_key")
            if not pat and "ru" in languages:
                pat = languages["ru"].get("no_text_key")
            if not pat:
                pat = "no_text_key: {key}"
            return pat.format(key=key)

    localed_data = resolve_translate_urls(localed_data, locale)
    return localed_data

def t(key: str, locale: str | None = "en", formating: bool = True, **kwargs) -> str:
    """Возвращает текст на нужном языке
    Ключи типа "text {translate_url:key.key}" это внутренние ключи на какой либо текст

    Args:
        key (str): ключ для текста
        locale (str, optional): код языка. Defaults to "en".

    Returns:
        str: текст на нужном языке
    """
    if not locale:
        locale = 'en'
    text = str(get_data(key, locale))  # Добавляем переменные в текст

    # Ищем все вхождения {translate_url:...} и заменяем их на перевод
    matches = list(re.finditer(r'\{translate_url:([^}]+)\}', text))
    for match in matches:
        inner_key = match.group(1)
        translated = str(get_data(inner_key, locale))
        # Заменяем только первое вхождение, чтобы избежать повторной замены уже изменённого текста
        text = text.replace(match.group(0), translated, 1)

    # Resolve {item_name:item_id}
    matches = list(re.finditer(r'\{item_name:([^}]+)\}', text))
    for match in matches:
        item_id = match.group(1)
        name, emoji = get_item_localization(item_id, locale)
        translated = format_item_name(name, emoji)
        text = text.replace(match.group(0), translated, 1)

    # Resolve {item_emoji:item_id}
    matches = list(re.finditer(r'\{item_emoji:([^}]+)\}', text))
    for match in matches:
        item_id = match.group(1)
        _, emoji = get_item_localization(item_id, locale)
        text = text.replace(match.group(0), emoji, 1)

    if formating:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError, IndexError) as e:
            log(f'Не удалось выполнить форматирование ключа "{key}", ошибка -> {e}', 2)

    text = resolve_custom_emojis(text)
    return text


def tranlate_data(data, locale: str = "en", key_prefix = '', **kwargs) -> Any:
    """ Переводит текст внутри словаря или списка
        
        Args:
        key_prefix - добавляет ко всем ключам префикс

        Example:
            > data = ['enable', 'disable']
            > key_prefix = 'commands_name.'
        >> ['✅ Включить', '❌ Выключить']

        Чтобы отменить префикс, добавьте "noprefix." перед элементом.
        Чтобы отменить перевод добавьте "notranslate." перед элементом.
    """

    if type(data) == list:

        def tr_list(lst):
            result_list = []
            for element in lst:
                if type(element) == str:
                    if key_prefix:
                        if not element.startswith('noprefix.') and not element.startswith('notranslate.'):
                            element = key_prefix + element
                        else:
                            element = element.replace('noprefix.', '')

                    if not element.startswith('notranslate.'):
                        result_list.append(t(element, locale, **kwargs))
                    else:
                        result_list.append(
                            element.replace('notranslate.', ''))
                else:
                    result_list.append(tr_list(element))

            return result_list

        result_list = tr_list(data)
        return result_list

    elif type(data) == dict:
        result_dict = {}
        for key, value in data:
            if key_prefix:
                if not value.startswith('noprefix.'):
                    value = key_prefix + value
                else:
                    value.replace('noprefix.', '')

            result_dict[key] = t(value, locale, **kwargs)

        return result_dict

def get_all_locales(key: str, **kwargs) -> dict:
    """Возвращает текст с ключа key из каждой локализации
    
    Args:
        key (str): ключ для текста

    Returns:
        dict[str]: ключ в словаре - код языка
    """
    locales_dict = {}

    for locale in available_locales:
        locales_dict[locale] = get_data(key, locale, **kwargs)

    return locales_dict

def key_exists(key: str, locale: str | None = 'en') -> bool:
    """Проверяет существование ключа в локализации."""
    if not locale: locale = 'en'
    locale = alternative_language(locale)
    if locale not in available_locales:
        locale = 'en'
    localed_data = languages.get(locale, {})
    for way_key in key.split('.'):
        if way_key.isdigit() and isinstance(localed_data, list):
            way_key = int(way_key)
        if isinstance(localed_data, dict) and way_key in localed_data:
            localed_data = localed_data[way_key]
        elif isinstance(localed_data, list) and isinstance(way_key, int) and way_key < len(localed_data):
            localed_data = localed_data[way_key]
        else:
            return False
    return True

async def get_lang(userid: int, alternative: str = 'en') -> str:
    """ Получает язык пользователя
    """
    try:
        from bot.redismanager import get_redis
        redis = get_redis()
        cached = await redis.get(f"user:lang:{userid}")
        if cached:
            return cached
    except Exception:
        pass

    from bot.models.user import Lang as BeanieLang
    lang = alternative
    data = await BeanieLang.find_one(BeanieLang.userid == userid)

    if data: 
        lang = data.lang

    if lang not in available_locales:
        lang = 'en'

    try:
        from bot.redismanager import get_redis
        redis = get_redis()
        await redis.set(f"user:lang:{userid}", lang)
    except Exception:
        pass

    return lang

from contextvars import ContextVar
current_rare_emoji: ContextVar[bool] = ContextVar('current_rare_emoji', default=True)

async def get_rare_emoji(userid: int) -> bool:
    try:
        from bot.redismanager import get_redis
        redis = get_redis()
        cached = await redis.get(f"user:rare_emoji:{userid}")
        if cached is not None:
            val = cached.decode('utf-8') if isinstance(cached, bytes) else str(cached)
            return val == "1"
    except Exception:
        pass

    from bot.models.user import User as BeanieUser
    rare_emoji = True
    user = await BeanieUser.find_one(BeanieUser.userid == userid)
    if user and 'settings' in user.dict():
        rare_emoji = user.settings.get('rare_emoji', True)

    try:
        from bot.redismanager import get_redis
        redis = get_redis()
        await redis.set(f"user:rare_emoji:{userid}", "1" if rare_emoji else "0")
    except Exception:
        pass
    return rare_emoji

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")
else: load()
