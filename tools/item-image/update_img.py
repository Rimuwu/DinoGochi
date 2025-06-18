import os
import json
import random

# Задайте путь к папке с файлами JSON
path = "../../bot/json/items/"

# Списки для случайного выбора
element_list = ['circle', 'square']
bg_list = ["blue", "cyan", "green", "orange", "pink", "red", "violet", "yellow"]

for filename in os.listdir(path):
    if filename.endswith('.json'):
        file_path = os.path.join(path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Перебираем все элементы в файле
        changed = False

        for key, item in data.items():
            print(key)
            old_image = item.get('image', None)
            item['image'] = {
                'icon': old_image,
                'element': random.choice(element_list),
                'bg': random.choice(bg_list)
            }
            changed = True

        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)