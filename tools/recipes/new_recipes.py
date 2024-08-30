import json
import os
from pprint import pprint



ex = os.path.dirname(__file__) # Путь к этому файлу

with open(f'{ex}/../../bot/json/items/recipes.json', encoding='utf-8') as f: 
  
    items = json.load(f) # type: dict


def item_list(items: list[dict]):
    """ Добавляет к каждому предмету ключ count c количеством 
    """
    res = []

    for item in items:
        st = item.copy()
        count = items.count(item)

        new_item = item.copy()
        new_item['count'] = count

        res.append(new_item)
        for _ in range(count): items.remove(st)

    return res

new_dct = {}
for key, value in items.items():

    materials = item_list(value['materials'])

    new_dct[key] = value
    new_dct[key]['create'] = {
        "main": item_list(value['create'])
    }
    new_dct[key]['materials'] = materials


print(new_dct)

with open(f'{ex}/../../bot/json/items/recipes.json', 'w', encoding='utf-8') as f:
    json.dump(new_dct, f, ensure_ascii=False, indent=4)