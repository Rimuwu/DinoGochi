from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

l = ImageFont.truetype('fonts/Aqum.otf', size=15)
b = ImageFont.truetype('fonts/Aqum.otf', size=100)

def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=10.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img


def create_point_image(color_rgb = (221, 173, 175), size = 250):
    point = Image.new('RGBA', (size, size))
    im1 = Image.new('RGBA', (size, size), color_rgb)

    mask_im = Image.open('point_mask.png').convert('L').resize(point.size)
    mask_im = mask_im.filter(ImageFilter.BoxBlur(0.5))
    # mask_im = mask_im.filter(ImageFilter.GaussianBlur(radius=0.5))

    point = Image.composite(im1, point, mask_im)
    point.alpha_composite(point)
    return point

def add_point(holst, point, cords: tuple = (100, 100), triangle = None):
    new_cords = (cords[0], holst.size[1] - cords[1])
    img = trans_paste(point, holst, 1, new_cords)
    
    if triangle:
        new_cords = [new_cords[0] - 5, new_cords[1] - 50]
        img = trans_paste(triangle, holst, 1, new_cords)

    return img

def create(holst, start_cord, end_cord, zero_y, color = 'blue'):
    start_cord = (start_cord[0], holst.size[1] - start_cord[1])
    end_cord = (end_cord[0], holst.size[1] - end_cord[1])

    one_cord = (start_cord[0], zero_y)
    two_cord = (end_cord[0], zero_y)

    alp = Image.new('RGBA', holst.size)
    mask_dr = ImageDraw.Draw(alp)
    mask_dr.polygon(xy=[start_cord, end_cord, two_cord, one_cord], fill = color)

    holst = trans_paste(alp, holst, 0.7)
    return holst

def create_graf(holst, point, point_cords: list, data: list, zero_x: int = 123, polyg_color: tuple = (0, 255, 255)):
    # Холст
    idraw = ImageDraw.Draw(holst)
    triangle = Image.open('triangle.png').resize((25, 25))

    add_crd = point.size[0] // 2
    ots = 71

    # # Линии
    # rep = 0
    # lines_cord = []
    # for cord_y in point_cords:
    #     text = data[rep]
    #     y_cord = holst.size[1] - cord_y
        
    #     if y_cord not in lines_cord: 
    #         lines_cord.append(y_cord)
    #         idraw.polygon([(zero_x - ots, y_cord + 7), (zero_x + (ots * 6) + 6, y_cord + 7)], fill=(255, 255, 255, 128))
    #     rep += 1

    # Полигоны
    rep, ind = 1, 0
    for cord_y in point_cords:
        if ind != 0:
            minus_y = point_cords[ind-1]
            minus_x = zero_x + ots * (rep - 1)

            cord_x = zero_x + ots * rep
            rep += 1

            point2_cords_panel = (cord_x + add_crd, cord_y - add_crd)
            point1_cords_panel = (minus_x + add_crd, minus_y - add_crd)

            holst = create(holst, point1_cords_panel, point2_cords_panel, 449, polyg_color) # type: ignore
        ind += 1

    # Точки
    rep = 0
    for cord_y in point_cords:
        cord_x = zero_x + ots * rep
        rep += 1
        
        if len(point_cords) == rep:
            holst = add_point(holst, point, (cord_x, cord_y), triangle)
        else:
            holst = add_point(holst, point, (cord_x, cord_y))

    # Текст
    rep = 0
    for cord_y in point_cords:
        text = data[rep]
        cord_x = zero_x + ots * rep

        idraw.text((cord_x, 470), str(text), font=l)
        rep += 1

    return holst


data_list = []
for i in range(7): data_list.append(random.randint(0, 100))
# data_list.sort()

# print(data_list)

# Цвета
blue_point = create_point_image((127, 255, 212), 15)
green_point = create_point_image((127, 255, 212), 15)
white_point = create_point_image((255, 255, 255), 15)

# cord_list = [80, 180, 220, 300, 400, 380, 440] # высота для размещения  360 пикселей от 80 до 440

cord_list = []
for i in range(7): cord_list.append(random.randint(80, 440))

np_list = []
for i in range(4): np_list.append(random.randint(80, 440))

two_list = []
for i in range(1): two_list.append(random.randint(80, 440))

img = Image.open('bg.png')

img = create_graf(img, white_point, cord_list, cord_list, 101, (0, 255, 255))
img = create_graf(img, white_point, two_list, cord_list, 681, (173, 255, 47))
img = create_graf(img, white_point, np_list, cord_list, 1260, (148, 0, 211))

img.show()
img.save('img.png')