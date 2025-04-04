import json
import pathlib
import re
from spellchecker import SpellChecker

LANGUAGE = 'ru'  # Укажите язык локализации, который вы хотите использовать

localization_data = {}
base_path = pathlib.Path(__file__).parent
localization_path = base_path / 'ru.json'
with open(localization_path, "r", encoding="utf-8") as loc_file:
    localization = json.load(loc_file)

def check_spelling(data, spell, path=""):
    """
    Рекурсивно проверяет каждое значение в словаре или списке на наличие ошибок.
    Выводит изменения в консоль.
    Игнорирует смайлики и структуры вида {name}.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = check_spelling(value, spell, path=f"{path}.{key}" if path else key)
            save_localization()  # Сохраняем данные после обработки каждого ключа
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = check_spelling(data[i], spell, path=f"{path}[{i}]")
            save_localization()  # Сохраняем данные после обработки каждого элемента списка
    elif isinstance(data, str):
        # Убираем смайлики и структуры вида {name}, сохраняя их для восстановления
        placeholders = {}
        placeholder_index = 0

        # Убираем структуры вида {name}
        def replace_placeholder(match):
            nonlocal placeholder_index
            placeholder = f"__PLACEHOLDER_{placeholder_index}__"
            placeholders[placeholder] = match.group(0)
            placeholder_index += 1
            return placeholder

        data_without_placeholders = re.sub(r"\{.*?\}", replace_placeholder, data)

        # Убираем только эмоджи (оставляем плейсхолдеры)
        emoji_pattern = re.compile(
            "[\U00010000-\U0010FFFF]", flags=re.UNICODE
        )  # Удаляем символы эмоджи
        data_without_emojis = emoji_pattern.sub("", data_without_placeholders)

        # Проверяем строку на ошибки
        corrected_words = []
        for word in data_without_emojis.split():
            if word not in spell:
                corrected_word = spell.correction(word)
                corrected_words.append(corrected_word if corrected_word else word)  # Используем исходное слово, если исправление не найдено
            else:
                corrected_words.append(word)
        corrected_string = " ".join(corrected_words)

        # Восстанавливаем структуры вида {name} и эмоджи
        for placeholder, original in placeholders.items():
            corrected_string = corrected_string.replace(placeholder, original)

        if data != corrected_string:  # Если строка изменилась
            print(f"Изменение в '{path}':")
            print(f"  Оригинал: {data}")
            print(f"  Исправлено: {corrected_string}")
        return corrected_string
    return data

def save_localization():
    """
    Сохраняет текущие данные локализации в файл.
    """
    with open(localization_path, "w", encoding="utf-8") as loc_file:
        json.dump(localization, loc_file, ensure_ascii=False, indent=4)

# Инициализация проверки орфографии
spell = SpellChecker(language=LANGUAGE)

# Проверяем локализационные данные
localization = check_spelling(localization, spell)
