import json
import random
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter
import sys

sys.path.append("../bot")
from functions import functions

with open('../images/dino_data.json') as f:
    json_f = json.load(f)

def trans_paste(fg_img,bg_img,alpha=10,box=(0,0)):
    fg_img_trans = Image.new("RGBA",fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans,fg_img,alpha)
    bg_img.paste(fg_img_trans,box,fg_img_trans)
    return bg_img

def egg_profile():
    egg_id = '352'
    lang = 'ru'
    time = 600000
    time_end = functions.time_end(time, True)
    if len(time_end) >= 18:
        time_end = time_end[:-6]

    bg_p = Image.open(f"remain/egg_profile_{lang}.png")
    egg = Image.open(str(json_f['elements'][egg_id]['image']))
    sz = 290
    egg = egg.resize((sz, sz), Image.ANTIALIAS)

    bg_img = bg_p
    fg_img = egg
    img = trans_paste(fg_img, bg_img, 1.0, (-50, 40))

    idraw = ImageDraw.Draw(img)
    line1 = ImageFont.truetype("../fonts/Comic Sans MS.ttf", size = 35)

    idraw.text((430, 220), time_end, font = line1)

    print(len(time_end))

    img.show()

# egg_profile()

def dino_profile():
    egg_id = '364'
    lang = 'en'
    if lang != 'ru':
        lang = 'en'

    dino = json_f['elements'][egg_id]
    if 'class' in list(dino.keys()):
        bg_p = Image.open(f"remain/{dino['class']}_icon.png")
    else:
        bg_p = Image.open(f"remain/None_icon.png")

    class_ = dino['image'][5:8]

    panel_i = Image.open(f"remain/{class_}_profile_{lang}.png")

    img = trans_paste(panel_i, bg_p, 1.0)

    dino_image = Image.open(str(json_f['elements'][egg_id]['image']))

    sz = 412
    dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)

    xy = -80
    x2 = 80
    img = trans_paste(dino_image, img, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))


    idraw = ImageDraw.Draw(img)
    line1 = ImageFont.truetype("../fonts/Comic Sans MS.ttf", size = 45)

    idraw.text((530, 100), "100", font = line1)
    idraw.text((530, 185), "100", font = line1)

    idraw.text((750, 100), "100", font = line1)
    idraw.text((750, 185), "100", font = line1)
    idraw.text((750, 265), "100", font = line1)


    img.show()
    # img.save('profile.png')

dino_profile()
