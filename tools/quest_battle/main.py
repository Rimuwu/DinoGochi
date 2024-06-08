from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import json

images_dir = 'images/quest_battle/'
back_file = 'back1.png'
MAX_HP = 100

l = ImageFont.truetype('fonts/edosz.ttf', size=18)
small = ImageFont.truetype('fonts/edosz.ttf', size=20)
b = ImageFont.truetype('fonts/emoji.ttf', size=15)

with open('bot/json/dino_data.json', encoding='utf-8') as f: 
    DINOS = json.load(f) # type: dict

def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=1.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img

def crop_text(text: str, unit: int=10, postfix: str='...'):
    """Обрезает текст и добавляет postfix в конце, 
       если текст больше чем unit + len(postfix)
    """
    if len(text) > unit + len(postfix):
        return text[:unit] + postfix
    else: return text

def generate(data_player_1, data_player_2, game_data):
    """ 
    data_player_1: {
        "name": "as1",
        "points": 12,
        "heal": 60,
        "dino_id": 100
    }

    data_player_2: {
        "name": "cat",
        "points": 56,
        "heal": 60,
        "dino_id": 100
    }

    game_data: {
        "stage": 2,
        "tasks": []
    }

    """

    # Фон
    img = Image.open(images_dir + back_file)

    # Таблица
    tb = Image.open(images_dir + 'table.png')
    img = trans_paste(tb, img)

    # Заполнение таблицы
    idraw = ImageDraw.Draw(img)

    #    Имя
    name1 = crop_text(data_player_1['name'], 8, '..')
    name2 = crop_text(data_player_2['name'], 8, '..')
    idraw.text((67, 29), name1, font = l)
    idraw.text((67, 62), name2, font = l)

    #    Поинты
    line_len = int(max([len(name1), len(name2)])) * 10
    idraw.line((43, 57, 67 + line_len + 45, 57), fill='white', width=2)

    idraw.text((67 + line_len + 25, 29), str(data_player_1['points']), font = l)
    idraw.text((67 + line_len + 25, 62), str(data_player_2['points']), font = l)

    # Колечки заданий
    circle_white = Image.open(images_dir + 'neutral.png')
    circle_red = Image.open(images_dir + 'notaken.png')
    circle_green = Image.open(images_dir + 'taken.png').resize((45, 45), Image.Resampling.LANCZOS)

    for i in range(1, 6):
        if i in game_data['wins']:
            # img = trans_paste(circle_green, img, box=(306, 10))
            
            x, y = 306, 32.5
            r = 22.5
            
            leftUpPoint = (x-r, y-r)
            rightDownPoint = (x+r, y+r)
            twoPointList = [leftUpPoint, rightDownPoint]
            idraw.ellipse(twoPointList, outline=(255,0,0,255), width=2)
    

    # Дино
    sz, a = 365, 0
    dat_l = [data_player_1, data_player_2]

    for ind in (0, 1):
        dino_id = dat_l[ind]['dino_id']
        hp = dat_l[ind]['heal']

        dino_data = DINOS['elements'][str(dino_id)]
        dino_image = Image.open(f'images/{dino_data["image"]}')
        dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)

        x, y = 52 + a * 490, -28
        if not a:
            dino_image = dino_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        img = trans_paste(dino_image, img, box=((y + x, y, sz + y + x, sz + y)))

        idraw.text((150 - 500 * (a-1), 317), '🖤', font = b, fill='red')
        idraw.text((175 - 500 * (a-1), 309), f'{hp}/{MAX_HP}', font = small)
        
        a += 1




    img.show()

data_player_1 = {'name': 'as1', "points": 12, 'dino_id': 19988, 'heal': 100}
data_player_2 = {'name': 'unknown_artist', "points": 56, 'dino_id': 903, 'heal': 32}
game_data = {"stage": 2, "tasks": ['fishing', 'battle', 'quest', 'communication', 'hunting'],
             "wins": [1]
             }

generate(data_player_1, data_player_2, game_data)