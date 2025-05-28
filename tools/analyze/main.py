import json
from collections import Counter, defaultdict

with open('c:/Папки/коды/Telegram DinoGochi/DinoGochi/tools/analyze/dino_data.json', encoding='utf-8') as f:
    data = json.load(f)

elements = data.get('elements', {})

name_counter = Counter()
class_counter = Counter()
class_names = defaultdict(list)

for elem_id, elem in elements.items():
    name = elem.get('name')
    class_ = elem.get('class')
    if name:
        name_counter[name] += 1
    if class_:
        class_counter[class_] += 1
        class_names[class_].append(name)

print('Статистика по именам:')
a = 0
for name, count in name_counter.most_common():
    print(f'{name}: {count}')
    a += 1

print(f'Всего уникальных имен: {a}')

print('\nСтатистика по классам:')
for class_, count in class_counter.most_common():
    print(f'{class_}: {count}')
    # print('  Имена:', ', '.join(filter(None, class_names[class_])))