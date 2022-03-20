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

egg_id = '352'
lang = 'en'
time = 600
time_end = functions.time_end(time, True)

bg_p = Image.open(f"remain/egg_profile_{lang}.png")
egg = Image.open(str(json_f['elements'][egg_id]['image']))

bg_img = bg_p
fg_img = egg
img = trans_paste(fg_img, bg_img, 1.0, (-95,-50))

idraw = ImageDraw.Draw(img)
line1 = ImageFont.truetype("../fonts/FloraC.ttf", size = 35)

idraw.text((390,100), time_end, font = line1)

img.show()
