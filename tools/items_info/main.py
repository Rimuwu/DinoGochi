import json
import os

ex = os.path.dirname(__file__) # Путь к этому файлу

LANG = 'ru'

with open(f'{ex}/../../bot/localization/{LANG}.json', encoding='utf-8') as f: 
  
    loc = json.load(f) # type: dict
    loc = loc[LANG]['items_names']


with open(f'{ex}/../../bot/json/items.json', encoding='utf-8') as f: 
  
    data = json.load(f) # type: dict 


with open(f'{ex}/../../bot/json/settings.json', encoding='utf-8') as f: 
  
    settings = json.load(f) # type: dict 

collecting_items = settings['collecting_items']

locations = {
    "forest": {
        "items": {
            'com': ['jar_honey', 'cookie', 'blank_piece_paper', 'feather'],
            'unc': ['timer', 'therapeutic_mixture', 'sweet_pancakes', 'blank_piece_paper', 'drink_recipe'],
            'rar': ['bento_recipe', 'candy_recipe', 'drink_recipe', 'tooling'],
            'mys': ['salad_recipe', 'torch_recipe', 'popcorn_recipe'],
            'leg': ['soup_recipe', 'gourmet_herbs', 'board_games', 'book_forest', 'flour_recipe', 'magic_stone']
        }
    },
    "lost-islands": {
        "items": {
            'com': ['slice_pizza', 'fish_oil', 'twigs_tree', 'skin', 'blank_piece_paper'],
            'unc': ['tooling', 'therapeutic_mixture', 'sweet_pancakes', 'drink_recipe'],
            'rar': ['curry_recipe', 'bread_recipe', 'tea_recipe', 'flour_recipe', 'timer', 'blank_piece_paper'],
            'mys': ['bear', 'clothing_recipe', 'meat_recipe'],
            'leg': ['taco_recipe', 'sandwich_recipe', 'hot_chocolate_recipe', 'book_lost-islands', 'magic_stone']
        }
    },
    "desert": {
        "items": {
            'com': ['chocolate', 'candy', 'dango', 'flour_recipe', 'rope', 'blank_piece_paper'],
            'unc': ['juice_recipe', 'hot_chocolate_recipe', 'cake_recipe', 'tooling'],
            'rar': ['pouch_recipe', 'sword_recipe', 'onion_recipe', 'arrow_recipe'],
            'mys': ['backpack_recipe', 'shield_recipe', 'pickaxe_recipe', 'drink_recipe', 'magic_stone'],
            'leg': ['steak_recipe', 'broth_recipe', 'sushi_recipe', 'book_desert', 'magic_stone']
        }
    },
    "mountains": {
        "items": {
            'com': ['sandwich', 'dango', 'mushroom', 'therapeutic_mixture', 'blank_piece_paper', 'drink_recipe'],
            'unc': ['bacon_recipe', 'bento_recipe', 'sandwich_recipe'],
            'rar': ['berry_pie_recipe', 'fish_pie_recipe', 'meat_pie_recipe'],
            'mys': ['basket_recipe', 'net_recipe', 'rod_recipe', 'magic_stone'],
            'leg': ['mysterious_egg', 'unusual_egg', 'rare_egg', 'mystic_egg', 'legendary_egg', 'book_mountains', 'magic_stone']
        }
    },
    "magic-forest": {
        "items": {
            'com': ['tea', 'tooling', 'bear', 'rope', 'gourmet_herbs'],
            'unc': ['croissant_recipe', 'therapeutic_mixture'],
            'rar': ['bag_goodies', 'rubik_cube', 'lock_bag', 'skinning_knife'],
            'mys': ['chest_food', 'recipe_chest', 'magic_stone'],
            'leg': ['mysterious_egg', 'unusual_egg', 'rare_egg', 'mystic_egg', 'legendary_egg', 'book_magic-forest', 'magic_stone']
        }
    }
}

text = ''

def get_name(id): 
    if type(id) == dict: id = id['item']

    if id in loc:
        return loc[id]['name']
    else: return id

def count_elements(lst: list, r: str = ', ') -> str:
    lst = list(map(get_name, lst))
    lst = list(set(lst))
    lst.sort()
    return r.join(lst)

lst_i = []
for location in locations:
    for rar in locations[location]['items']:
        for item in locations[location]['items'][rar]:
            lst_i.append(get_name(item))

text += f'Journey -> {count_elements(lst_i)}\n'
text += f'Bar -> {get_name("ale")}\n'

for ttp in collecting_items:
    lst_i = []
    for rar in collecting_items[ttp]:
        for item in collecting_items[ttp][rar]:
            lst_i.append(get_name(item))

    text += f'{ttp} -> {count_elements(lst_i)}\n'

text += '\nNo recipe Craft\n'

for key, item in data.items():

    if 'ns_craft' in item:
        for ns_key in item['ns_craft']:

            text += f"{count_elements(item['ns_craft'][ns_key]['materials'], ' + ')} -> {count_elements(item['ns_craft'][ns_key]['create'])}\n"

text += '\nRecipe Craft\n'

for key, item in data.items():

    if 'materials' in item:

        text += f"{count_elements(item['materials'], ' + ')} -> {get_name(key)} -> {count_elements(item['create'], ', ')}\n"

text += '\nAll Items\n'

lst = []
for key, item in data.items():
    lst.append(get_name(key))

text += count_elements(lst)

print(text)
print(len(text))

file = open('items.txt', 'w', encoding='utf-8')
file.write(text)
file.close()