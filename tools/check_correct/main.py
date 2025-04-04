import json
import pathlib
from spellchecker import SpellChecker


LANGUAGE = 'ru'  # Укажите язык локализации, который вы хотите использовать

localization_data = {}
base_path = pathlib.Path(__file__) .parent #.parent.parent
localization_path = base_path / 'ru.json' #base_path / "bot"  / "localization" / f"{LANGUAGE}.json"
with open(localization_path, "r", encoding="utf-8") as loc_file:
    localization = json.load(loc_file)

def check_spelling(data, spell):
    """
    Рекурсивно проверяет каждое значение в словаре или списке на наличие ошибок.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = check_spelling(value, spell)
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = check_spelling(data[i], spell)
    elif isinstance(data, str):
        # Проверяем строку на ошибки
        corrected_words = []
        for word in data.split():
            if word not in spell:
                corrected_word = spell.correction(word)
                corrected_words.append(corrected_word if corrected_word else word)  # Используем исходное слово, если исправление не найдено
            else:
                corrected_words.append(word)
        return " ".join(corrected_words)
    return data

# Инициализация проверки орфографии
spell = SpellChecker(language=LANGUAGE)

# Проверяем локализационные данные
localization = check_spelling(localization, spell)

# Сохраняем исправленные данные обратно в файл
with open(localization_path, "w", encoding="utf-8") as loc_file:
    json.dump(localization, loc_file, ensure_ascii=False, indent=4)
