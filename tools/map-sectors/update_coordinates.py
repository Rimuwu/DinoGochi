import json
import re

def increment_coordinates(text):
    """Увеличивает все координаты в формате 'x.y' на +1 для каждой координаты"""
    def replace_coord(match):
        x, y = match.group(1), match.group(2)
        new_x = str(int(x) + 1)
        new_y = str(int(y) + 1)
        return f'"{new_x}.{new_y}"'
    
    # Регулярное выражение для поиска координат в кавычках
    pattern = r'"(\d+)\.(\d+)"'
    return re.sub(pattern, replace_coord, text)

# Читаем исходный файл
with open('map.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Преобразуем координаты
updated_content = increment_coordinates(content)

# Записываем обновленный файл
with open('map.json', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("Координаты успешно обновлены!")

# Проверяем что JSON валидный после изменений
try:
    with open('map.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print("JSON файл валидный после обновления.")
except json.JSONDecodeError as e:
    print(f"Ошибка в JSON после обновления: {e}")
