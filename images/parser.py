import requests
import fake_useragent
from bs4 import BeautifulSoup
import json
import os

#json {"elements": {}, "number": 1, "page": 1, "lz": [0, 0, 0, 0, 0, 0]}

with open('dino_data.json') as f:
    json_f = json.load(f)

com_i = json_f["lz"][0]
unc_i = json_f["lz"][1]
rar_i = json_f["lz"][2]
myt_i = json_f["lz"][3]
leg_i = json_f["lz"][4]
egg_i = json_f["lz"][5]

def consol_write(json_f):
    global com_i,unc_i,rar_i,myt_i,leg_i,egg_i
    os.system('cls')
    print("Парсинг...")
    print(f"Страница: {json_f['page']} | Картинок: {json_f['number']}\n" + f"{com_i} {unc_i} {rar_i} {myt_i} {leg_i} {egg_i}")


def item_create(element, type, dr):
    global items
    item = {}

    image_number = element.find('div', class_ = 'dino-item-top').find('div', class_ = "dino-item-top-id").text[1:]
    if int(image_number) > int(last_number):
        json_f['number'] = int(image_number)

    item['type'] = type

    image_bytes = requests.get(element.find('img').get('src')).content
    direct = f"{dr}/{item['type']}_{image_number}.png"
    item['image'] = direct
    with open(direct, 'wb') as file:
        file.write(image_bytes)

    if type == 'dino':
        item['name'] = element.find('span').text
        clel = element.find('div', class_ = 'dino-item-top').find_all('div')[2].get('class')[1]
        if clel == 'dino-class-UNKNOWN':
            item['class'] = None
        else:
            item['class'] = clel[11:]
    else:
        pass

    items[str(image_number)] = item

def parse():
    global json_f, last_number, items
    global com_i,unc_i,rar_i,myt_i,leg_i, egg_i


    for i in range(int(json_f['page']),701):
        if egg_i == 100 and com_i == 100 and unc_i == 100 and rar_i == 100 and myt_i == 100 and leg_i == 100:
            break

        storage_number = int(i)
        last_number = json_f['number']
        link = f'https://dinox.io/dinos/?page={storage_number}'

        response = requests.get(link).text
        soup = BeautifulSoup(response, features= "html.parser")
        block = soup.find('div', class_ = 'page').find('div', class_ = 'portal-content-wrapper').find('div', class_ = 'portal-content-basic portal-content-container').find('div', class_ = 'dino-list')

        if egg_i < 100:
            egg_item = block.find_all('div', class_ = 'dino-item dino-item-rarity-UNKNOWN')

        if com_i < 100:
            common_item = block.find_all('div', class_ = 'dino-item dino-item-rarity-Common')
        if unc_i < 100:
            uncommon_item = block.find_all('div', class_ = 'dino-item dino-item-rarity-Uncommon')
        if rar_i < 100:
            rare_item = block.find_all('div', class_ = 'dino-item dino-item-rarity-Rare')
        if myt_i < 100:
            mythic_item = block.find_all('div', class_ = 'dino-item dino-item-rarity-Mythic')
        if leg_i < 100:
            legendary_item = block.find_all('div', class_ = 'dino-item dino-item-rarity-Legendary')

        items = {}
        if egg_i < 100:
            for element in egg_item:
                if egg_i < 100:
                    item_create(element, 'egg', 'egg')
                    egg_i += 1
        if com_i < 100:
            for element in common_item:
                if com_i < 100:
                    item_create(element, 'dino', 'dino-com')
                    com_i += 1
        if unc_i < 100:
            for element in uncommon_item:
                if unc_i < 100:
                    item_create(element, 'dino', 'dino-unc')
                    unc_i += 1
        if rar_i < 100:
            for element in rare_item:
                if rar_i < 100:
                    item_create(element, 'dino', 'dino-rar')
                    rar_i += 1
        if myt_i < 100:
            for element in mythic_item:
                if myt_i < 100:
                    item_create(element, 'dino', 'dino-myt')
                    myt_i += 1
        if leg_i < 100:
            for element in legendary_item:
                if leg_i < 100:
                    item_create(element, 'dino', 'dino-leg')
                    leg_i += 1


        json_f['elements'] = json_f['elements'] | items
        json_f['page'] = storage_number

        json_f["lz"][0] =com_i
        json_f["lz"][1] =unc_i
        json_f["lz"][2] =rar_i
        json_f["lz"][3] =myt_i
        json_f["lz"][4] =leg_i
        json_f["lz"][5] =egg_i

        save(json_f)
        consol_write(json_f)

def save(json_f):

    with open('dino_data.json', 'w') as f:
        json.dump(json_f, f)

consol_write(json_f)
parse()
