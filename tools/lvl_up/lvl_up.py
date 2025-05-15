from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import json


back_file = 'bg.png'
MAX_HP = 100

l = ImageFont.truetype('../../fonts/edosz.ttf', size=18)
small = ImageFont.truetype('../../fonts/Aqum.otf', size=20)
b = ImageFont.truetype('../../fonts/emoji.ttf', size=15)

with open('../../bot/json/dino_data.json', encoding='utf-8') as f: 
    DINOS = json.load(f) # type: dict

def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=1.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img

def crop_circle(img: Image.Image, size: int) -> Image.Image:
    """Обрезает изображение по кругу с качественным сглаживанием."""
    img = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    # Нарисуем эллипс чуть меньше, чтобы избежать резких краёв
    inset = 2
    draw.ellipse((inset, inset, size - inset, size - inset), fill=255)
    # Применим лёгкое размытие только по краю
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1))
    result = Image.new('RGBA', (size, size))
    result.paste(img, (0, 0), mask)
    return result

def lvl_up_image(avatar_file: str = 'avatar.png') -> Image.Image:
    # Открываем фоновое изображение
    img = Image.open(back_file).convert("RGBA")

    # Открываем и обрезаем аватар
    avatar = Image.open(avatar_file).convert("RGBA")
    avatar_cropped = crop_circle(avatar, 100)  # 100 - размер аватара

    # Открываем изображение upper.png
    upper = Image.open('upper.png').convert("RGBA")

    # Накладываем upper.png на аватар
    avatar_with_upper = avatar_cropped.copy()

    # Вставляем аватар с upper на итоговое изображение
    img = trans_paste(avatar_with_upper, img, alpha=1.0, box=(55, 65))

    img = trans_paste(upper, img, alpha=1.0, box=(0, 0))

    # Убираем прозрачность: заменяем прозрачные пиксели на чёрные
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    background = Image.new("RGBA", img.size, (0, 0, 0, 255))
    background.paste(img, mask=img.split()[3])  # Используем альфа-канал как маску
    img_no_alpha = background.convert("RGB")  # Убираем альфа-канал

    return img_no_alpha

img = lvl_up_image(avatar_file='avatar.png')
img.save('output.png', format='PNG')