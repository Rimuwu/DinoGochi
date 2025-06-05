import json
import random

# Путь к файлу
DATA_FILE = './dino_data.json'

# Загрузка данных
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

eggs = data['data']['egg']

elements = data.get('elements', {})

# Получаем ключи динозавров
dino_keys = [k for k, v in elements.items() if v.get('type') == 'dino']

# Сначала раздаём по одному яйцу каждому динозавру, пока есть яйца
egg_idx = 0
for key in dino_keys:
    if egg_idx < len(eggs):
        elements[key]['egg'] = eggs[egg_idx]
        egg_idx += 1
    else:
        # Если яйца закончились, добавляем случайное яйцо
        elements[key]['egg'] = random.choice(eggs)

# # Если остались яйца, раздаём их случайным динозаврам
# while egg_idx < len(eggs):
#     key = random.choice(dino_keys)
#     elements[key]['egg'] = eggs[egg_idx]
#     egg_idx += 1

# Сохраняем обратно
with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)