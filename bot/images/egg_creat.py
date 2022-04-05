import json
import random
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter

with open('../images/dino_data.json') as f:
    json_f = json.load(f)

def trans_paste(fg_img,bg_img,alpha=10,box=(0,0)):
    fg_img_trans = Image.new("RGBA",fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans,fg_img,alpha)
    bg_img.paste(fg_img_trans,box,fg_img_trans)
    return bg_img

bg_p = Image.open(f"remain/{random.choice(['back', 'back2'])}.png")
eg_l = []

for i in range(3):
    rid = str(random.choice(list(json_f['data']['egg'])))
    image = Image.open(str(json_f['elements'][rid]['image']))
    eg_l.append(image)

for i in range(3):
    bg_img = bg_p
    fg_img = eg_l[i]
    img = trans_paste(fg_img, bg_img, 1.0, (i*512,0))


# image_d = str(json_f['elements'][rid]['image'])
# photo = open(f"../images/{image_d}", 'rb')
