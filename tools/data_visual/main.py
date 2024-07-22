import json
import os

ex = os.path.dirname(__file__) # Путь к этому файлу

LANG = 'ru'

with open(f'{ex}/../../bot/localization/{LANG}.json', encoding='utf-8') as f: 
  
    loc = json.load(f) # type: dict
    loc = loc[LANG]['items_names']


with open(f'{ex}/../../bot/json/items.json', encoding='utf-8') as f: 
  
    data = json.load(f) # type: dict 

new_data = []

for i in loc.keys():
    item = data[i]

    item['name'] = loc[i]['name']
    item['original_key'] = i

    if 'description' in loc[i]:
        item['description'] = loc[i]['description']
    
    if 'create' in item:
        item['loc_create'] = []

        for im in item['create']:
            if type(im) == str:
                item['loc_create'].append(loc[im]['name'])

            if type(im) == dict:
                item['loc_create'].append(loc[im['item']]['name'])
    
        item['loc_create'] = list(set(item['loc_create']))
    
    if 'materials' in item:
        
        for im in item['materials']:
            
            if 'recipes' in data[im['item']]:
                data[im['item']]['recipes'].append(loc[i]['name']) 
            else:
                data[im['item']]['recipes'] = [loc[i]['name']]
            
            # if type(im) == str:
            #     if 'recipes' in data[im]:
            #         data[i]['recipes'].append(loc[im]) 
            #     else:
            #         data[i]['recipes'] = [loc[im]]

            # if type(im) == dict:
            #     if 'recipes' in data[i['item']]:
            #         data[i['item']]['recipes'].append(loc[i['item']]['name']) 
            #     else:
            #         data[i['item']]['recipes'] = [loc[i['item']]['name']]

for key, item in data.items():
    if 'recipes' in item:
        item['recipes'] = list(set(item['recipes']))
    new_data.append(item)

with open(ex+"/data.json", 'w', encoding='utf-8') as f:
    json.dump(list(new_data), f, ensure_ascii=False, indent=4)
print('save')