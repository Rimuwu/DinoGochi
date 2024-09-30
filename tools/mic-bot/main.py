import json
import os
import sys

from telebot import TeleBot

API_TOKEN = '<API_TOKEN>'
bot = TeleBot(API_TOKEN)

languages = {}
available_locales = []

def load() -> None:
    """Загрузка локализации"""

    for filename in os.listdir("./bot/localization"):
        with open(f'./bot/localization/{filename}', encoding='utf-8') as f:
            languages_f = json.load(f)

        for l_key in languages_f.keys():
            available_locales.append(l_key)
            languages[l_key] = languages_f[l_key]

def alternative_language(lang: str):
    languages = {
        'ua': 'ru'
    }
    try:
        if lang in languages: return languages[lang]
    except:
        pass
    return lang

def get_data(key: str, locale: str):
    """Возвращает данные локализации

    Args:
        key (str): ключ
        locale (str, optional): язык. Defaults to "en".

    Returns:
        str | dict: возвращаемое
    """
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
                    pass
        else:
            return languages[locale]["no_text_key"].format(key=key)

    return localed_data


def t(key: str, locale: str = "en", formating: bool = True, **kwargs) -> str:
    """Возвращает текст на нужном языке

    Args:
        key (str): ключ для текста
        locale (str, optional): код языка. Defaults to "en".

    Returns:
        str: текст на нужном языке
    """
    text = str(get_data(key, locale)) #Добавляем переменные в текст
    if formating:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            pass

    return text

load()

@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, "Hi!")


@bot.message_handler(commands=['translatem2', 'tm2'])
def translate(message):
    args = message.text.split()
    lang = args[1]
    text = args[2]

    chat_id = message.chat.id

    botworker.send_message(chat_id, t(text, lang, False), parse_mode='Markdown')

@bot.message_handler(commands=['translate', 't'])
def translate(message):
    args = message.text.split()
    lang = args[1]
    text = args[2]

    chat_id = message.chat.id

    botworker.send_message(chat_id, t(text, lang, False))


if __name__ == '__main__':
    print('start')
    bot.infinity_polling()