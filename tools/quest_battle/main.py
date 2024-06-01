from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

images_dir = 'images/quest_battle/'
back_file = 'back1.png'

l = ImageFont.truetype('fonts/edosz.ttf', size=18)
b = ImageFont.truetype('fonts/emoji.ttf', size=100)

def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=10.0, box=(0, 0)):
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

def generate(data_player_1, data_player_2):
    """ 
    data_player_1: {
        "name": "as1",
        "points": 12
    }
    
    data_player_2: {
        "name": "cat",
        "points": 56
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




    img.show()

data_player_1 = {'name': 'as1', "points": 12}
data_player_2 = {'name': 'unknown_artist', "points": 56}

generate(data_player_1, data_player_2)