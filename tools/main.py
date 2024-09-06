# Удалить все деньги
# Удалить весь рынок
# оставляем - premium_activator, 3_days_premium, stone_resurrection
# Проверить, что у всех должен быть 1 ключ языка и сделать индекс на это
# Добавить идексы ко всем новым коллекциям

import json
import os
from random import uniform
import pymongo

mongo_client = pymongo.MongoClient('localhost', 27017)

users = mongo_client.user.users
items = mongo_client.items.items
dinosaurs = mongo_client.dinosaur.dinosaurs
langs = mongo_client.user.lang
users = mongo_client.user.users
sellers = mongo_client.market.sellers

# ex = os.path.dirname(__file__) # Путь к этому файлу
# with open(f'{ex}/dino_data.json', encoding='utf-8') as f: 
#     DINOS = json.load(f).copy() # type: dict


# print('start money')
# users.update_many({}, {"$set": {'coins': 10000}})
# print('end money')

# not_delete = ['premium_activator', '3_days_premium', 'stone_resurrection', 'meow_book', 'book_forest', 'book_lost-islands', 'book_desert', 'book_mountains', 'book_magic-forest']

# set_1 = ['egg_case', 'gift_2024', 'gift_2023', 'recipe_chest', 'chest_food']

# all_nin = ['premium_activator', '3_days_premium', 'stone_resurrection', 'meow_book', 'book_forest', 'book_lost-islands', 'book_desert', 'book_mountains', 'book_magic-forest', 'egg_case', 'gift_2024', 'gift_2023', 'recipe_chest', 'chest_food']


# print('start set_1')
# items.update_many(
#     {
#         "items_data.item_id": {'$in': set_1}
#     }, {'$set': {'count': 1}}
#     )
# print('start delete')

# items.delete_many(
#     {
#         "items_data.item_id": {'$nin': all_nin}
#     })

# quality_spec = {
#     'com': [0, 1],
#     'unc': [0, 2],
#     'rar': [0, 3],
#     'mys': [0, 4], 
#     'leg': [0, 5]
# }

# def set_standart_specifications(dino_type: str, dino_quality: str):

#     """
#     return power, dexterity, intelligence, charisma
#     """

#     power = 0
#     dexterity = 0 # Ловкость
#     intelligence = 0
#     charisma = 0

#     power = round(uniform( *quality_spec[dino_quality] ), 4)
#     dexterity = round(uniform( *quality_spec[dino_quality] ), 4)
#     intelligence = round(uniform( *quality_spec[dino_quality] ), 4)
#     charisma = round(uniform( *quality_spec[dino_quality] ), 4)

#     if dino_type == 'Herbivore':
#         charisma += round(uniform( *quality_spec[dino_quality] ), 4)

#     elif dino_type == 'Carnivore':
#         power += round(uniform( *quality_spec[dino_quality] ), 4)

#     elif dino_type == 'Flying':
#         dexterity += round(uniform( *quality_spec[dino_quality] ), 4)

#     return round(power, 4), round(dexterity, 4), round(intelligence, 4), round(charisma, 4)

# def get_dino_data(data_id: int):
#     data = {}
#     try:
#         data = DINOS['elements'][str(data_id)]
#     except Exception as e:
#         pass
#     return data

# print('start set chars')

# dinos = list(dinosaurs.find({}))
# lld = len(dinos)
# a = 0
# for dino in dinos:
#     a += 1
#     print(a, 'dinos', lld)
#     dino: dict
#     dino_data = get_dino_data(dino['data_id'])

#     power, dexterity, intelligence, charisma = set_standart_specifications(dino_data['class'], dino['quality'])

#     dinosaurs.update_one({
#         '_id': dino['_id']
#     }, {
#         "$set": {
#             'stats.power': power,
#             'stats.dexterity': dexterity,
#             'stats.intelligence': intelligence,
#             'stats.charisma': charisma,
#             'stats.heal': 100,
#             'stats.energy': 100,
#             'stats.eat': 100,
#             'memory.action': []
#         }
#     })

print('start langs')
users_data = list(users.find({}))
a = 0 
col = 0
lld = len(users_data)
for i in users_data:
    a += 1
    print(a, 'users', lld)
    llg = list(langs.find({'userid': i['userid']}))

    if len(llg) == 0:
        langs.insert_one({'userid': i['userid'], 'lang': 'en'})

    elif len(llg) != 1:
        main_lang = llg[0]['lang']
        langs.delete_many({'userid': i['userid']})

        langs.insert_one({'userid': i['userid'], 'lang': main_lang})
        col += len(llg) - 1

print('end', col)


# dinosaurs.update_many({'profile.background_type': 'custom'}, {
#     "$set": {'profile.background_type': "standart",
#              'profile.background_id': 0
#         }
# })

# sellers.update_many({}, {
#     "$set": {'custom_image': ''}
# })