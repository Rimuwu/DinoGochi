import json
from logging.handlers import RotatingFileHandler
import random
import os
import sys
import emoji
from pprint import pprint

import translators
from langdetect import DetectorFactory, detect, detect_langs
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from g4f import Client
import time
from tqdm import tqdm
import time

from g4f.Provider import (
    DDG, # +
    Pizzagpt, # +
    PollinationsAI, # +
    Yqcloud # + gpt-4
)

import logging

# Logger
logger = logging.getLogger()

DetectorFactory.seed = 0
ex = os.path.dirname(__file__) # Путь к этому файлу

# File logger
log_filehandler = RotatingFileHandler(
        filename=f"{ex}/logs/last.log", 
        encoding='utf-8', mode='a+')
log_streamhandler = logging.StreamHandler()
log_formatter = logging.Formatter("%(message)s")
log_filehandler.setFormatter(log_formatter)
log_streamhandler.setFormatter(log_formatter)

# Добавляем обработчики к логгеру
logger.addHandler(log_filehandler)
logger.addHandler(log_streamhandler)
logger.setLevel(logging.INFO)  # или другой уровень по необходимости

# base_names = {}
# cash_replaces = {}

with open(os.path.join(ex, 'settings.json'), encoding='utf-8') as f: 
    """ Загружаем константы из файла найстроек """
    settings = json.load(f) # type: dict

    replace_codes = settings['replace_codes']
    replace_words = settings['replace_words']
    one_replace_s = settings['one_replace_s']
    translators_names = settings['translators']

    main_code = settings['main_code']
    langs_path = settings['langs_path']
    dump_path = settings['dump_path']
    start_symbols = settings['start_symbols']

    zero_translator = settings['zero_translator']
    ignore_translate_keys = settings['ignore_translate_keys']
    strat_sym, end_sym = settings['sp_sym']
    
    no_edit = settings['no_edit']

# langs_path = "./test/langs"
# dump_path = "./test/dumps"

# --- Добавляем списки user_agents и proxies ---
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Добавьте больше user-agent по желанию
]
proxies = [
    # Пример: 'http://user:pass@proxy_ip:port',
    'http://KxxvFT:Kg0MSmP7iv@45.147.192.2:6070',
    'http://KxxvFT:Kg0MSmP7iv@77.94.1.194:6070',
    'http://KxxvFT:Kg0MSmP7iv@77.83.148.232:6070'
    # Оставьте пустым если не используете прокси, либо добавьте свои
]
providers = [
    # DDG,
    # Pizzagpt,
    PollinationsAI,
    # Yqcloud,
    # None
]

# client = Client()
# response = client.chat.completions.create(
#     model="gpt-4o-mini",
#     messages=[{"role": "user", "content": "Hello"}],
#     web_search=False
# )

import concurrent.futures

def only_translate(text, from_language, to_language, translator, text_key, client: Client, **kwargs):
    # --- Ротация user-agent, прокси, дополнительных заголовков и задержка ---
    user_agent = random.choice(user_agents)
    proxy = random.choice(proxies) if proxies else None
    # Дополнительные заголовки
    accept_list = [
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'application/json, text/plain, */*',
        '*/*',
    ]
    accept_language_list = [
        'en-US,en;q=0.9',
        'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'en;q=0.8',
    ]
    connection_list = ['keep-alive', 'close']
    dnt_list = ['1', '0']
    # Генерация случайного Referer
    referers = [
        'https://www.google.com/',
        'https://www.bing.com/',
        'https://duckduckgo.com/',
        'https://yandex.ru/',
        'https://www.yahoo.com/',
        'https://www.ecosia.org/',
    ]
    headers = {
        'User-Agent': user_agent,
        'Accept': random.choice(accept_list),
        'Accept-Language': random.choice(accept_language_list),
        'Connection': random.choice(connection_list),
        'DNT': random.choice(dnt_list),
        'Referer': random.choice(referers),
    }
    # Случайная задержка 0.5-2.5 сек
    time.sleep(random.uniform(0.1, 0.5))

    def do_request():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f'You are a strict translation module for Telegram bot. Your task is to translate the text from language "{from_language}" to language "{to_language}". Rules: 1. DO NOT guess, rephrase or autocorrect. 2. DO NOT explain anything. Just return the translation. 3. DO NOT translate, delete, rearrange or change: - #1042# (any number within # characters) - this must be kept exactly, in the same form and position, without any changes. This is **mandatory** the fact that if #1042# (or similar) exists in the input, it is present in the output **exactly as it is**. 4. Markdown formatting (for example, **bold**, _italic_, [link](url)) should be fully saved. 5. Always keep the original style, structure and order of the elements - especially the arrangement of punctuation. 6. If the input consists only of untranslated elements, return it unchanged. 7. If you cannot translate or the text does not make sense - return exactly the text that needs to be translated without changes. 8. If the text is already in the target language - return it unchanged. 9. If the text is very short (1-2 words), consider it as a button icon - translate it briefly and keep its format and tone. 10. You also get a key "{text_key}" - if the text value is unclear, you can consider this key as context (but do not output it). 11. If the text is short, then it may be a button, you have to stick to the same length for translation. 12. Output only translated text - no explanation, no changes. 13. If you cant translate, return the "NOTEXT". Text to translate: {text}'
                },
            ],
            headers=headers,
            proxy=proxy
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(do_request)
        try:
            response = future.result(timeout=30)
        except concurrent.futures.TimeoutError:
            return ''

    return response.choices[0].message.content
    # return f'{text} {from_language} -> {to_language}'

def check_count_unicode(text):
    """
    Возвращает кортеж (count_special, count_emoji):
    - count_special: количество всех символов из one_replace_s в тексте
    - count_emoji: количество эмодзи в тексте
    """
    if not isinstance(text, str):
        return 0, 0

    special_one_replace_s = one_replace_s + ['{', '}', '#', '\n', '\\']
    count_special = sum(text.count(sym) for sym in special_one_replace_s)
    count_emoji = len(emoji.emoji_list(text))
    return count_special, count_emoji

def walk_keys(data, callback, path=""):
    """
    Рекурсивно обходит словарь/список и вызывает callback для каждого текстового значения.
    path — путь до ключа (через точку)
    """
    if isinstance(data, dict):
        for k, v in data.items():
            new_path = f"{path}.{k}" if path else k
            walk_keys(v, callback, new_path)
    elif isinstance(data, list):
        for idx, v in enumerate(data):
            new_path = f"{path}.{idx}" if path else str(idx)
            walk_keys(v, callback, new_path)
    else:
        callback(path, data)


def build_structure(data):
    """
    Создаёт структуру дампа: все не-словарные/не-списковые значения заменяет на 'NOTEXT'.
    """
    if isinstance(data, dict):
        return {k: build_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [build_structure(v) for v in data]
    # elif isinstance(data, (int, float, bool)):
    #     return data
    else:
        return 'NOTEXT'


def compare_structures(base, dump, path=""):
    """
    Сравнивает структуру base (исходный словарь) и dump (дамп перевода).
    Возвращает:
      - новые ключи (есть в base, нет в dump)
      - изменённые (значения отличаются)
      - удалённые (есть в dump, нет в base)
    """
    new_keys, changed_keys, deleted_keys = [], [], []
    if isinstance(base, dict):
        base_keys = set(base.keys())
        dump_keys = set(dump.keys()) if isinstance(dump, dict) else set()

        for k in base_keys:
            new_path = f"{path}.{k}" if path else k
            if k not in dump_keys:
                new_keys.append(new_path)
            else:
                n, c, d = compare_structures(base[k], dump[k], new_path)
                new_keys += n
                
                # Проверяем, что последний или предпоследний элемент пути не находится в no_edit
                path_parts = new_path.split('.')
                last = path_parts[-1]
                second_last = path_parts[-2] if len(path_parts) > 1 else None
                if last in no_edit or (second_last and second_last in no_edit):
                    pass  # пропускаем добавление в changed_keys
                else:
                    changed_keys += c

                deleted_keys += d

        for k in dump_keys - base_keys:
            new_path = f"{path}.{k}" if path else k
            deleted_keys.append(new_path)

    elif isinstance(base, list) and isinstance(dump, list):
        for idx, v in enumerate(base):
            new_path = f"{path}.{idx}" if path else str(idx)

            if idx >= len(dump):
                new_keys.append(new_path)
            else:
                n, c, d = compare_structures(v, dump[idx], new_path)
                new_keys += n
                
                # Проверяем, что последний или предпоследний элемент пути не находится в no_edit
                path_parts = new_path.split('.')
                last = path_parts[-1]
                second_last = path_parts[-2] if len(path_parts) > 1 else None
                if last in no_edit or (second_last and second_last in no_edit):
                    pass  # пропускаем добавление в changed_keys
                else:
                    changed_keys += c

                deleted_keys += d

        for idx in range(len(base), len(dump)):
            new_path = f"{path}.{idx}" if path else str(idx)
            deleted_keys.append(new_path)
    else:
        # if isinstance(base, (int, float, bool)):
        #     new_keys.append(path)
        if base != dump:
            changed_keys.append(path)
    return new_keys, changed_keys, deleted_keys

def save_replace(code: int, text: str, translate: bool, data = '', cash_replaces: None | dict = None):
    """
    Сохраняет замену в словаре cash_replaces.
    """
    new_code = f'{code}'
    r_code = f'{strat_sym}{code}{end_sym}'
    
    if cash_replaces is None:
        cash_replaces = {}
    else:
        cash_replaces = cash_replaces.copy()

    s_1 = new_code not in cash_replaces
    s_2 = r_code not in cash_replaces
    s_3 = new_code not in replace_words
    s_4 = r_code not in replace_words

    # for k, v in cash_replaces.items():
    #     if v["text"] == text and v["translate"] == translate and v.get("data", "") == data:
    #         return k

    if all([s_1, s_3, s_2, s_4]):
        # if new_code.startswith(strat_sym) and new_code.endswith(end_sym):
        #     pass
        # else:
        #     new_code = r_code
        # new_code = f'{new_code}0{new_code}0'
        cash_replaces[new_code] = {"text": text, 
                               "translate": translate, "data": data}
        return new_code, cash_replaces
    else:
        r = 0
        if type(code) == int:
            r = code + 1
        elif code.isdigit(): # type: ignore
            r += int(code) + 1
        else:
            r = int(code[1:-1]) + 1 # type: ignore
        # r = random.randint(1, 1000)
        return save_replace(r, text, translate, data, cash_replaces=cash_replaces)

def replace_specials(text: str, cash_replaces: dict):
    # "(121)": {"text": "_", "translate": false},
    """
    Заменяет спецсимволы и эмодзи на коды для защиты от перевода.
    """
    if not isinstance(text, str):
        return text
    
    for _ in range(12):
        # Заменяем спецсимволы
        for key, item in replace_words.items():
            if item['text'] in text:
                code, cash_replaces = save_replace(int(key), item['text'], item['translate'], cash_replaces=cash_replaces)

                text = text.replace(
                    item['text'], f"{strat_sym}{code}{end_sym}")

        # Прячем эмодзи
        for em in emoji.emoji_list(text):
            code, cash_replaces = save_replace(100,
                                em['emoji'], False, cash_replaces=cash_replaces)

            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(em['emoji'], text_code)

        # Прячем переменные вида {name}
        matches = re.findall(r'\{.*?\}', text)
        for match in matches:
            code, cash_replaces = save_replace(200, 
                                match, False, cash_replaces=cash_replaces)

            text_code = f"{strat_sym}{code}{end_sym}"
            text = text.replace(match, text_code)

        # # Прячем переменные вида /слово (только первое целое слово после /)
        # matches = re.findall(r'/\w+', text)
        # for match in matches:
        #     code, cash_replaces = save_replace(300,
        #             match, False, cash_replaces=cash_replaces)
        #     text_code = f"{strat_sym}{code}{end_sym}"
        #     text = text.replace(match, text_code)

        # matches = re.findall(r'<\s*[^<>]+\s*>', text)
        # for match in matches:
        #     code, cash_replaces = save_replace(400,
        #             match, True)
        #     text_code = f"{strat_sym}{code}{end_sym}"
        #     text = text.replace(match, text_code)
        
        # # Прячем переменные вида <b>word</b>
        # matches = re.findall(r'<\s*[^<>]+\s*>', text)
        # for match in matches:
        #     code, cash_replaces = save_replace(500,
        #             match, True)
        #     text_code = f"{strat_sym}{code}{end_sym}"
        #     text = text.replace(match, text_code)

        # # Прячем переменные вида *Слово*
        # for one_repl in one_replace_s:
        #     tx = fr'\{one_repl}\s*.*?\s*\{one_repl}'
        #     matches = re.findall(tx, text)
        #     for match in matches:
        #         code, cash_replaces = save_replace(600,
        #                             match[1:-1], True, one_repl)
        #         text_code = f"{strat_sym}{code}{end_sym}"
        #         text = text.replace(match, text_code)

    # # Прячем конструкции вида #число##число#... (любое количество подряд)
    # # Новый паттерн: ищет одну или более групп #число#, подряд и

    # matches = re.findall(r'(#[0-9]+#)+', text)
    # for match in matches:
    #     if strat_sym in match or end_sym in match:
    #         continue
    #     if len(match) >= 6:
    #         code, cash_replaces = save_replace(700, match, False, cash_replaces=cash_replaces)
    #         text_code = f"{strat_sym}{code}{end_sym}"
    #         text = text.replace(match, text_code)
    #         print(f"Заменено: {match} -> {text_code}")

    return text, cash_replaces

def smart_contains(text, word):
    """
    Проверяет, содержится ли подстрока word в тексте text.
    """
    if not isinstance(text, str) or not isinstance(word, str) or not word:
        return False
    return word in text

def restore_specials(text, to_lang, from_lang, text_key, cash_replaces):
    """
    Восстанавливает спецсимволы и эмодзи после перевода.
    """
    if not isinstance(text, str): return text

    for _ in range(12):
        # for key, item in replace_words.items():
        #     word_text = item['text']

        #     fr_key = key[1:-1]
        #     for code_in_text in [
        #         f'{strat_sym}{fr_key}{end_sym}',
        #         f'{strat_sym} {fr_key}{end_sym}',
        #         f'{strat_sym}{fr_key} {end_sym}',
        #         f'{strat_sym} {fr_key} {end_sym}',
        #         # f'{fr_key}{end_sym}',
        #         # f'{strat_sym}{fr_key}',
        #         # f'{fr_key} {end_sym}',
        #         # f'{strat_sym} {fr_key}',
        #         # f'{fr_key}{end_sym}',
        #         # f' {strat_sym}{fr_key}'
        #     ]:

        #         if smart_contains(text, code_in_text):
        #             text = text.replace(code_in_text, word_text)

        for code, item in cash_replaces.copy().items():
            word_text = item['text']
            # repl = False

            for code_in_text in [
                f'{strat_sym}{code}{end_sym}',
                f'{strat_sym} {code}{end_sym}',
                f'{strat_sym}{code} {end_sym}',
                f'{strat_sym} {code} {end_sym}',
                f'{strat_sym}{strat_sym}{code}{end_sym}',
                f'{strat_sym}{code}{end_sym}{end_sym}',
                f'{strat_sym}{strat_sym} {code}{end_sym}',
                f'{strat_sym}{code} {end_sym}{end_sym}',
                f'{strat_sym} {code}{end_sym}{end_sym}',
                f'{code}{end_sym}',
                f'{strat_sym}{code}',
                f'{code} {end_sym}',
                f'{strat_sym} {code}',
                f'{code}{end_sym}',
                f' {strat_sym}{code}',
            ]:

                if smart_contains(text, code_in_text):
                    if item['translate']:
                        stage_text = translate_text(word_text, to_lang, from_lang, text_key, cash_replaces)
                        if not isinstance(stage_text, str):
                            stage_text = str(stage_text)
                        if item['data']:
                            # Оборачиваем только восстановленный текст, а не весь text
                            stage_text = f"{item['data']}{stage_text}{item['data']}"
                        text = text.replace(code_in_text, stage_text)
                    else:
                        text = text.replace(code_in_text, word_text)

                    # text = text.replace(code_in_text, word_text)
                    # continue
                else:
                    text = text.replace(code_in_text, word_text)

    # raw_code_pattern = r'#(\d+)#'
    # matches = re.findall(raw_code_pattern, text)
    # for code in matches:
    #     if code in cash_replaces:
    #         word_text = cash_replaces[code]['text']
    #         text = text.replace(f'#{code}#', word_text)

    # Восстановление эмодзи (пример: #128512# -> 😀)
    return text


def match_case(original, translated, lang):
    # orig_words = original.split()
    # trans_words = translated.split()
    # # Если количество слов совпадает, применяем стиль регистра для каждого слова
    # if len(orig_words) == len(trans_words):
    #     result = []
    #     for i, word in enumerate(trans_words):
    #         if orig_words[i].isupper():
    #             result.append(word.capitalize())
    #         elif orig_words[i].islower():
    #             result.append(word.lower())
    #         elif orig_words[i].istitle():
    #             result.append(word.title())
    #         else:
    #             result.append(word)
    #     return ' '.join(result)

    # # Новое: если весь оригинал в нижнем регистре — вернуть перевод в нижнем регистре
    # if original.islower():
    #     return translated.lower()
    # # Новое: если только первое слово с большой буквы, остальные маленькие
    # if (
    #     original
    #     and original[0].isupper()
    #     and (len(original) == 1 or original[1:].islower())
    # ):
    #     # Если перевод состоит из нескольких слов, делаем capitalize только первое слово
    #     if translated:
    #         return translated[0].capitalize() + translated[1:].lower()
    #     return translated

    # # Если не совпадает — применяем общий стиль
    # if original.isupper():
    #     return translated.capitalize()
    # if original.istitle():
    #     return translated.title()
    return translated

def repl_code(trans, lang):
    code = replace_codes.get(trans.lower(), {}).get(lang, lang)
    return code

def translate_text(text: str, to_lang: str, from_lang: str, text_key: str, 
                   cash_replaces: dict, rep: int = 0, client = None, **kwargs):
    """
    Переводит текст, защищая спецсимволы и эмодзи.
    """

    if cash_replaces is None:
        cash_replaces = {}

    trans = 'lingvanex'

    if to_lang is None and from_lang is None:
        return text

    if not isinstance(text, str) or not text.strip():
        return text
    safe_text, cash_replaces = replace_specials(text, cash_replaces)
    translated = safe_text

    try:
        lang = detect(safe_text)
        langs = detect_langs(safe_text)
    except Exception as e:
        lang = None
        langs = []

    if lang in ['en', 'it', 'sv', 'pl']:
        translated = safe_text
        logger.info(f'EN_LANG: lang {lang} to {to_lang} key {text_key} text {safe_text}')
        print(f"Не переводим: {text} - {lang}")

    # elif lang is None and len(langs) == 0 and ns_lang is None:
    #     translated = safe_text
    #     print(f"Не переводим (не определён): {text} - {lang}")
    #     logger.info(f'NO_LANG: ({ns_lang}) lang {lang} to {to_lang} key {text_key} text {safe_text}')
    #     return restore_specials(translated, to_lang, from_lang, text_key, cash_replaces)

    elif safe_text[1:-1] in cash_replaces.keys():
        cash_replaces[safe_text[1:-1]]['translated'] = False
        translated = safe_text
        print(f"Не переводим (замена): {text} - {lang}")
        logger.info(f'NO_TRANSLATE_REPEAT: lang {lang} to {to_lang} key {text_key} text {safe_text}')
        return restore_specials(translated, to_lang, from_lang, text_key, cash_replaces)

    elif safe_text in replace_words.keys():
        cash_replaces[safe_text]['translated'] = False
        translated = safe_text
        print(f"Не переводим (замена): {text} - {lang}")
        logger.info(f'NO_TRANSLATE_REPEAT: lang {lang} to {to_lang} key {text_key} text {safe_text}')
        return restore_specials(translated, to_lang, from_lang, text_key, cash_replaces)

    elif lang or len(langs) == 0:
        try:
            forbidden = [
                "HTTP", "ERR_CHALLENGE", "Blocked by DuckDuckGo", "Bot limit exceeded", "ERR_BN_LIMIT",
                "Misuse detected. Please get in touch, we can   come up with a solution for your use case.",
                "Too Many Requests", "Misuse", "message='Too", "AI-powered", 'more](https://pollinations.ai/redirect/2699274)', "module—no guesswork", '\n\n---\n', 'Telegram bot', '\u0000'
            ]

            # --- Основной вызов перевода ---
            translated = only_translate(safe_text,
                                    from_language=repl_code(trans, from_lang), 
                                    to_language=repl_code(trans, to_lang),
                                    translator=trans,
                                    text_key=text_key,
                                    client=client,
                                    **kwargs)
            
            try:
                new_detect = detect(translated)
            except:
                new_detect = None

            if new_detect in ['ru'] and rep < 25:
                print(f"Не переведён!: {text}")
                return translate_text(safe_text, to_lang, from_lang, text_key, 
                                      cash_replaces, rep=rep + 1, client=client, **kwargs)
            elif new_detect in ['ru']:
                print(f"Не переведён (проверка): {text}")
                logger.info(f'NO_TRANSLATE: lang {from_lang} to {to_lang} key {text_key} text {text}')
                return restore_specials(translated, to_lang, from_lang, text_key, cash_replaces)

            # Проверка на наличие запрещённых слов в результате перевода
            if any(f in translated for f in forbidden):
                print(f"Обнаружено запрещённое слово в переводе: {translated}")
                prv = random.choice(providers)
                client = Client(prv)
                if rep < 25:
                    return translate_text(safe_text, to_lang, from_lang, text_key, 
                                          cash_replaces, rep=rep + 1, client=client, **kwargs)
                else:
                    print(f"Не удалось получить корректный перевод после {rep} попыток.")
                    translated = safe_text
                    logger.info(f'NO_TRANSLATE: lang {from_lang} to {to_lang} key {text_key} text {text}')

            if translated == "" and rep < 25:
                print(f"Пустой перевод, пробую ещё раз: {text}")
                return translate_text(safe_text, to_lang, from_lang, text_key, 
                                      cash_replaces, rep=rep + 1, client=client, **kwargs)
            elif translated == "":
                print(f"Пустой перевод {rep} раз: {text}")
                logger.info(f'VOID_TRANSLATE: lang {from_lang} to {to_lang} key {text_key} text {text}')
                return 'NOTEXT'

            count1, count2 = check_count_unicode(translated)
            count_01, count_02 = check_count_unicode(safe_text)
            if count1 != count_01 or count2 != count_02:
                print(f"Количество спецсимволов или эмодзи не совпадает: {text} - {lang} - {translated}")
                return translate_text(
                    safe_text, to_lang, from_lang, text_key, cash_replaces, 
                    rep=rep + 1, client=client, **kwargs
                )

            # translated = match_case(text, translated, to_lang)

            if translated == safe_text and rep < 25:
                print(f"Перевод не изменился, пробую ещё раз: {text} - {lang}")
                return translate_text(
                    safe_text, to_lang, from_lang, text_key, cash_replaces, rep=rep + 1,
                    client=client, **kwargs
                )
            if translated == safe_text:
                print(f"Перевод не изменился за {rep} попыток: {text} - {lang}")
                logger.info(f'NOEDIT: lang {from_lang} to {to_lang} key {text_key} text {text}')

            # dict_data = {
            #     "text": safe_text,
            #     "lang": lang,
            #     "to_lang": to_lang,
            #     "translated": translated,
            #     "trans": trans
            # }
            # pprint(dict_data)
        except Exception as e:
            # --- Обработка ошибок HTTP 418 и ERR_CHALLENGE ---
            err_str = str(e)
            if any(code in err_str for code in ["418", "ERR_CHALLENGE", "Blocked by DuckDuckGo", "ERR_BN_LIMIT", "Too Many Requests"]):
                print(f"[RETRY] Перехвачена ошибка провайдера: {err_str}")
                prv = random.choice(providers)
                client = Client(prv)
                if rep < 25:
                    return translate_text(
                        safe_text, to_lang, from_lang, text_key, cash_replaces, 
                        rep=rep + 1, client=client, **kwargs
                    )
                else:
                    print(f"[FAIL] Не удалось получить корректный перевод после {rep} попыток (ошибка провайдера).")
                    logger.info(f'ERROR_TRANSLATE: lang {from_lang} to {to_lang} key {text_key} text {text}')
                    translated = safe_text

    else:
        translated = 'NOTEXT'
        logger.info(f'EXIT: lang {from_lang} to {to_lang} key {text_key} text {text}')
        print(f"Не переведено {len(langs)} {from_lang} -> {text}")
    return restore_specials(translated, to_lang, from_lang, text_key, cash_replaces)


def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def set_by_path(dct, path, value, dump=None):
    """
    Устанавливает значение по пути вида 'a.b.0.c' в словаре/списке.
    Если передан dump, сверяет ожидаемый тип на каждом уровне с dump.
    Если на последнем уровне ожидается список, но найден dict — индекс становится ключом.
    """
    keys = path.split('.')
    cur = dct
    dump_cur = dump
    for idx, k in enumerate(keys[:-1]):
        next_k = keys[idx + 1]
        # Определяем ожидаемый тип на этом уровне
        expected_type = None
        if dump_cur is not None:
            try:
                if isinstance(dump_cur, dict):
                    dump_next = dump_cur.get(k)
                elif isinstance(dump_cur, list) and k.isdigit():
                    dump_next = dump_cur[int(k)] if int(k) < len(dump_cur) else None
                else:
                    dump_next = None
                if isinstance(dump_next, list):
                    expected_type = list
                elif isinstance(dump_next, dict):
                    expected_type = dict
                else:
                    expected_type = None
            except Exception:
                expected_type = None
        # Если текущий уровень — список, используем int-индекс
        if isinstance(cur, list):
            if not k.isdigit():
                raise TypeError(f"Ожидался числовой индекс для списка, но получен ключ '{k}'")
            k_int = int(k)
            while len(cur) <= k_int:
                # Если dump подсказывает тип, используем его, иначе по next_k
                if expected_type is not None:
                    cur.append([] if expected_type is list else {})
                else:
                    cur.append([] if next_k.isdigit() else {})
            cur = cur[k_int]
            if dump_cur is not None and isinstance(dump_cur, list) and k_int < len(dump_cur):
                dump_cur = dump_cur[k_int]
            else:
                dump_cur = None
        elif isinstance(cur, dict):
            # Если dump подсказывает тип, используем его, иначе по next_k
            if k not in cur:
                if expected_type is not None:
                    cur[k] = [] if expected_type is list else {}
                else:
                    cur[k] = [] if next_k.isdigit() else {}
            cur = cur[k]
            if dump_cur is not None and isinstance(dump_cur, dict):
                dump_cur = dump_cur.get(k)
            else:
                dump_cur = None
        else:
            raise TypeError(f"Неожиданный тип: {type(cur)} для ключа {k}")
    last = keys[-1]
    # На последнем уровне сверяем с dump, если возможно
    if dump_cur is not None:
        if isinstance(cur, list) and last.isdigit() and isinstance(dump_cur, list):
            last = int(last)
            while len(cur) <= last:
                cur.append(None)
            cur[last] = value
        elif isinstance(cur, dict) and isinstance(dump_cur, dict):
            cur[last] = value
        else:
            # Если типы не совпадают, всё равно пытаемся записать
            if isinstance(cur, list) and last.isdigit():
                last = int(last)
                while len(cur) <= last:
                    cur.append(None)
                cur[last] = value
            elif isinstance(cur, dict):
                cur[last] = value
            else:
                raise TypeError(f"Неожиданный тип на последнем уровне: {type(cur)} для ключа {last}")
    else:
        if isinstance(cur, list) and last.isdigit():
            last = int(last)
            while len(cur) <= last:
                cur.append(None)
            cur[last] = value
        elif isinstance(cur, dict):
            cur[last] = value
        else:
            raise TypeError(f"Неожиданный тип на последнем уровне: {type(cur)} для ключа {last}")


def del_by_path(dct, path):
    """
    Удаляет значение по пути вида 'a.b.0.c' в словаре/списке.
    """
    keys = path.split('.')
    cur = dct
    for k in keys[:-1]:
        if isinstance(cur, list) and k.isdigit():
            cur = cur[int(k)]
        elif isinstance(cur, dict):
            cur = cur[k]
        else:
            raise TypeError(f"Неожиданный тип: {type(cur)} для ключа {k}")

    last = keys[-1]
    if isinstance(cur, list) and last.isdigit():
        last = int(last)
        del cur[last]
    elif isinstance(cur, dict):
        if last not in cur:
            raise KeyError(f"Ключ {last} не найден в словаре")
        del cur[last]
    else:
        raise TypeError(f"Неожиданный тип на последнем уровне: {type(cur)} для ключа {last}")

# Проверяем, начинается ли path с любого из new_keys или changed_keys
def is_prefix_in_keys(keys, path):
    """
    Проверяет, заканчивается ли path на любой из путей в keys,
    либо если path заканчивается на key, либо если key — предпоследний элемент в path.
    Например: keys = ['a.b', 'c'], path = 'a.b.1.d' -> True если 'a.b' или 'a.b.1' в keys.
    """
    
    path_parts = path.split('.')
    for key in keys:
        if path == key:
            return True
        if path.endswith(f"{key}"):
            return True

        if len(path_parts) > 1 and path_parts[-2] == key:
            return True

    return False

a_c_upd = 0
STOP_BY_CTRL_C = False  # глобальный флаг

def ctrl_c_watcher():
    global STOP_BY_CTRL_C
    try:
        input("\n[LOG] Для остановки перевода нажмите Enter...\n")
        STOP_BY_CTRL_C = True
        print("[LOG] Остановка по Enter. Завершаю работу после текущих операций...")
    except Exception:
        STOP_BY_CTRL_C = True
        print("[LOG] Остановка по ошибке в watcher.")

def translate_worker(args):
    global a_c_upd, STOP_BY_CTRL_C
    path, value, lang, main_lang, dump_data, lang_data, dump_path_, lang_path, new_keys, changed_keys, ignore_translate_keys, total, times, pbar = args

    # Для каждого потока свой клиент с рандомным провайдером
    local_client = Client(random.choice(providers))
    translated = value
    if STOP_BY_CTRL_C:
        return (path, translated, value)

    if isinstance(value, str):
        path_set = set(path.split('.'))
        ignore_set = set(ignore_translate_keys)

        t0 = time.time()
        skip_translate = False

        # Если хотя бы один ключ из пути в ignore_translate_keys — не переводим

        if path_set & ignore_set:
            if path.endswith('text'):
                translated = translate_text(value, lang, main_lang, path, {}, client=local_client)
                if translated == value:
                    translated = translate_text(value, lang, main_lang, path, {}, client=local_client)

            skip_translate = True
            logger.info(f'SKIP_TRANSLATE (ignore_keys): lang {lang} to {main_lang} key {path}')

        # Если длина значения <= 2 — не переводим
        if not skip_translate and len(value) <= 2:
            translated = value
            skip_translate = True
            logger.info(f'SKIP_TRANSLATE (<= 2): lang {lang} to {main_lang} key {path}')

        # Если весь текст состоит только из эмодзи — не переводим
        if (
            not skip_translate
            and isinstance(value, str)
            and value.strip()
            and all(c in [e['emoji'] for e in emoji.emoji_list(value)] for c in value if not c.isspace())
        ):
            translated = value
            skip_translate = True
            logger.info(f'SKIP_TRANSLATE (only_emoji): lang {lang} to {main_lang} key {path}')

        # Если не было причин пропустить — переводим
        if not skip_translate:
            if STOP_BY_CTRL_C:
                return (path, translated, value)

            translated = translate_text(value, lang, main_lang, path, {}, client=local_client)
            if translated == value and not STOP_BY_CTRL_C:
                translated = translate_text(value, lang, main_lang, path, {}, client=local_client)

        t1 = time.time()
        times.append(t1 - t0)
        return (path, translated, value)
    
    return (path, translated, value)

def get_by_path(dct, path):
    """Получить значение по пути вида 'a.b.0.c' из словаря/списка."""
    keys = path.split('.')
    cur = dct
    for k in keys:
        if isinstance(cur, list) and k.isdigit():
            idx = int(k)
            if idx < len(cur):
                cur = cur[idx]
            else:
                return None
        elif isinstance(cur, dict):
            if k in cur:
                cur = cur[k]
            else:
                return None
        else:
            return None
    return cur

def sort_dict_by_reference(data, reference):
    """
    Рекурсивно сортирует словарь data по структуре и порядку ключей reference.
    Если в data есть лишние ключи — они добавляются в конец.
    """
    if isinstance(reference, dict) and isinstance(data, dict):
        sorted_dict = {}
        # Сначала ключи из reference, в их порядке
        for k in reference:
            if k in data:
                sorted_dict[k] = sort_dict_by_reference(data[k], reference[k])
        # Затем лишние ключи из data, которых нет в reference
        for k in data:
            if k not in reference:
                sorted_dict[k] = data[k]
        return sorted_dict
    elif isinstance(reference, list) and isinstance(data, list):
        # Сортируем каждый элемент списка по соответствующему элементу reference
        sorted_list = []
        for i, ref_item in enumerate(reference):
            if i < len(data):
                sorted_list.append(sort_dict_by_reference(data[i], ref_item))
            else:
                break
        # Добавляем лишние элементы из data
        if len(data) > len(reference):
            sorted_list.extend(data[len(reference):])
        return sorted_list
    else:
        return data

def main():
    global a_c_upd, zero_translator, main_lang, STOP_BY_CTRL_C

    # Запускаем watcher в отдельном потоке
    watcher_thread = threading.Thread(target=ctrl_c_watcher, daemon=True)
    watcher_thread.start()

    # Получаем язык из аргументов командной строки
    lang_arg = None
    if len(sys.argv) > 1:
        lang_arg = sys.argv[1].lower()

    # 1. Загрузка главного словаря
    main_lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{main_code}.json"))
    main_data = read_json(main_lang_path).get(main_code, {})

    # 2. Получение всех языков для перевода
    langs_dir = os.path.normpath(os.path.join(ex, langs_path))
    lang_files = [f for f in os.listdir(langs_dir) if f.endswith('.json')]
    lang_codes = [f.replace('.json', '') for f in lang_files if f.replace('.json', '') != main_code]

    # Если указан язык, фильтруем только его
    if lang_arg:
        lang_codes = [lang for lang in lang_codes if lang == lang_arg]
        if not lang_codes:
            print(f"Язык {lang_arg} не найден для перевода.")
            return

    print(translators.translators_pool)
    print(f"Языки для перевода: {lang_codes}")

    for lang in lang_codes:
        a_c_upd = 0
        print(f"\n=== Перевод для {lang} ===")
        # Определяем главный язык для перевода

        lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{lang}.json"))
        dump_path_ = os.path.normpath(os.path.join(ex, dump_path, f"{lang}.json"))

        # Загружаем главный словарь для текущего языка
        main_lang_path = os.path.normpath(os.path.join(ex, langs_path, f"{main_code}.json"))
        main_data = read_json(main_lang_path).get(main_code, {})

        lang_data = read_json(lang_path).get(lang, {})
        dump_data = read_json(dump_path_)

        # 3. Создать структуру дампа
        main_struct = build_structure(main_data)
        # Если дамп пустой, создаём структуру только для новых/изменённых ключей
        if not dump_data:
            dump_data = {lang: main_struct}
            write_json(dump_path_, dump_data)

        # 4. Сравнить структуры
        new_keys, changed_keys, deleted_keys = compare_structures(main_data, dump_data[lang])

        print(f'Новые ключи: {new_keys}')
        print(f'Изменённые ключи: {changed_keys}')
        print(f'Удалённые ключи: {deleted_keys}')

        # --- ДОБАВЛЯЕМ КЛЮЧИ, где в lang_data стоит 'NOTEXT' ---
        def collect_notext_paths(data, path=""):
            if isinstance(data, dict):
                for k, v in data.items():
                    new_path = f"{path}.{k}" if path else k
                    collect_notext_paths(v, new_path)
            elif isinstance(data, list):
                for idx, v in enumerate(data):
                    new_path = f"{path}.{idx}" if path else str(idx)
                    collect_notext_paths(v, new_path)
            else:
                if data == "NOTEXT":
                    if path not in changed_keys:
                        changed_keys.append(path)

        collect_notext_paths(lang_data)

        # 5. Удалить лишние ключи
        for key in deleted_keys:
            try:
                del_by_path(lang_data, key)
            except Exception as e:
                print(f"Ошибка удаления {key} из lang_data: {e}")
            try:
                del_by_path(dump_data[lang], key)
            except Exception as e:
                print(f"Ошибка удаления {key} из dump_data: {e}")

        # Добавляем новые ключи в lang_data, если их нет
        for key in new_keys:
            try:
                # Получаем оригинальное значение по ключу
                orig_value = get_by_path(main_data, key)
                # Если это не строка, копируем как есть, иначе 'NOTEXT'
                if not isinstance(orig_value, str):
                    set_by_path(lang_data, key, orig_value, dump_data[lang])

            except Exception as e:
                print(f"Ошибка добавления {key} в lang_data: {e}")

        # Сохраняем только после удаления всех ключей
        write_json(dump_path_, dump_data)
        write_json(lang_path, {lang: lang_data})

        # --- Сортировка lang_data по main_data ---
        lang_data = sort_dict_by_reference(lang_data, main_data)
        write_json(lang_path, {lang: lang_data})

        if new_keys or changed_keys:
            print(f'\nНачало перевода...')
            logging.info(f'\n---------------------------------------')
            logging.info(f'{time.strftime("%Y-%m-%d %H:%M:%S")} - Начало перевода для {lang}')
            logging.info(f'---------------------------------------')

            # Собираем пути для перевода: новые или изменённые ключи, либо если значение None или "NOTEXT"
            paths_to_translate = []

            # --- Собираем только переводимые пути (строки, а также int, float, bool) ---
            def collect_leaf_paths(data, base_path=""):
                result = []
                if isinstance(data, dict):
                    for k, v in data.items():
                        new_path = f"{base_path}.{k}" if base_path else k
                        result.extend(collect_leaf_paths(v, new_path))
                elif isinstance(data, list):
                    for idx, v in enumerate(data):
                        new_path = f"{base_path}.{idx}" if base_path else str(idx)
                        result.extend(collect_leaf_paths(v, new_path))
                elif isinstance(data, (str, int, float, bool)):
                    result.append((base_path, data))
                return result

            paths_to_translate = []
            for path in new_keys + changed_keys:
                orig_value = get_by_path(main_data, path)
                if isinstance(orig_value, (dict, list)):
                    paths_to_translate.extend(collect_leaf_paths(orig_value, path))
                else:
                    paths_to_translate.append((path, orig_value))
            
            total = len(paths_to_translate)

            if total == 0:
                print("Нет новых или изменённых ключей для перевода.")
            else:
                print(f"Всего ключей для перевода: {total}")

            times = []
            pbar = tqdm(total=total, desc="Перевод", unit="ключ")

            worker_args = [
                (path, value, lang, main_code, dump_data, lang_data, dump_path_, lang_path, new_keys, changed_keys, ignore_translate_keys, total, times, pbar)
                for path, value in paths_to_translate
            ]

            try:
                save_counter = 0  # счетчик для промежуточного сохранения
                with ThreadPoolExecutor(max_workers=6) as executor:
                    future_to_path = {executor.submit(translate_worker, arg): arg[0] for arg in worker_args}
                    for future in as_completed(future_to_path):
                        if STOP_BY_CTRL_C:
                            print("[LOG] Получен сигнал остановки. Завершаю перевод.")
                            break

                        path, translated, value = future.result()
                        # Если перевод получился "NOTEXT", то и в дамп пишем "NOTEXT"
                        if translated == "NOTEXT":
                            value = "NOTEXT"

                        if not isinstance(translated, (bool, int, float)):
                            print(f"Переведено: {path} -> {translated}")

                        set_by_path(lang_data, path, translated, dump_data[lang])
                        set_by_path(dump_data, f'{lang}.'+path, value)

                        pbar.update(1)
                        save_counter += 1

                        # Сохраняем прогресс каждые 5 ключей (можно изменить)
                        if save_counter % 5 == 0:
                            # Сортируем перед сохранением
                            lang_data = sort_dict_by_reference(lang_data, main_data)
                            write_json(lang_path, {lang: lang_data})
                            write_json(dump_path_, dump_data)

                pbar.close()
                # Сортируем перед финальным сохранением
                lang_data = sort_dict_by_reference(lang_data, main_data)
                write_json(lang_path, {lang: lang_data})
                write_json(dump_path_, dump_data)

                if STOP_BY_CTRL_C:
                    print("[LOG] Работа остановлена пользователем.")
                    return

            except KeyboardInterrupt:
                STOP_BY_CTRL_C = True
                print("\n[LOG] Остановка по Ctrl+C. Сохраняю прогресс и завершаю работу...")
                pbar.close()
                # Сортируем перед финальным сохранением
                lang_data = sort_dict_by_reference(lang_data, main_data)
                write_json(lang_path, {lang: lang_data})
                write_json(dump_path_, dump_data)
                sys.exit(0)

            if STOP_BY_CTRL_C:
                print("[LOG] Работа остановлена пользователем.")
                return

            pbar.close()
            # Сохраняем только один раз после всех переводов
            write_json(lang_path, {lang: lang_data})
            write_json(dump_path_, dump_data)

if __name__ == '__main__':
    main()