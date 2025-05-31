import json
from collections import defaultdict

path = '../../bot/json/dino_data.json'

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

egg_ids = [str(e) for e in data['data']['egg']]
egg_to_dinos = defaultdict(list)

dino_keys = [k for k, v in data['elements'].items() if v['type'] == 'dino']

for idx, dino_key in enumerate(dino_keys):
    egg_id = egg_ids[idx % len(egg_ids)]
    egg_to_dinos[egg_id].append(dino_key)

# Добавляем к каждому яйцу поле "dino"
for egg_id in egg_ids:
    data['elements'][egg_id]['dino'] = egg_to_dinos.get(egg_id, [])

with open('./dino_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print('Готово! К каждому яйцу добавлено поле "dinos".')
# Подсчет яиц без динозавров
egg_elements = [k for k, v in data['elements'].items() if v.get('type') == 'egg']
no_dino_eggs = [k for k in egg_elements if not data['elements'][k].get('dino')]
print(f'Яиц без динозавров: {len(no_dino_eggs)}')
if no_dino_eggs:
    print('ID яиц без динозавров:', no_dino_eggs)
