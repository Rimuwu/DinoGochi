from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import json

comf = ImageFont.truetype('fonts/Comfortaa.ttf', size=35)

with open('bot/json/dino_data.json', encoding='utf-8') as f: 
        DINOS = json.load(f) # type: dict

def trans_paste(fg_img, bg_img, 
                alpha=10.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img


def centre_var(image, font, message, start_var=0, end_var=250):
        draw = ImageDraw.Draw(image)
        _, _, w, h = draw.textbbox((0, 0), message, font=font)
        var = (end_var - start_var - w) / 2 + start_var

        return var

def text_on_image():
    def centre_var(image, font, message, start_var=0, end_var=250):
        draw = ImageDraw.Draw(image)
        _, _, w, h = draw.textbbox((0, 0), message, font=font)
        var = (end_var - start_var - w) / 2 + start_var

        return var

    img = Image.open('images/skills/bg.png')
    idraw = ImageDraw.Draw(img)
    y = 43
    x = 467
    y_plus = 68

    a = -1
    for text in ['Power', 'Dexterity', 'Intelligence', 'Charisma']:
        a += 1
        x = centre_var(img, comf, text, 467, 754)

        idraw.text(
            (x, y + (y_plus * a)), text, 'white', font=comf, stroke_width=0
        )


    return img

from PIL import Image

def crop_right(image_path, crop_percentage):
    """
    Обрезает изображение с правой стороны на заданное количество процентов (X%).

    :param image_path: Путь к исходному изображению.
    :param crop_percentage: Процент от ширины изображения, который нужно обрезать.
    :return: Обрезанное изображение.
    """
    # Открываем изображение
    image = Image.open(image_path)
    
    # Получаем размеры изображения
    width, height = image.size
    
    # Вычисляем количество пикселей для обрезки
    crop_width = int(width * (crop_percentage / 100))
    
    # Обрезаем изображение
    cropped_image = image.crop((0, 0, width - crop_width, height))
    
    return cropped_image


def apply_mask(mask, image):
    # Открываем оригинальное изображение и маску
    image = image.convert("RGBA")
    mask = mask.convert('L')  # Конвертируем маску в градации серого

    # Создаём новый пустой RGBA-изображение с теми же размерами
    transparent_image = Image.new("RGBA", image.size, (0, 0, 0, 0))

    # Применяем маску к изображению
    masked_image = Image.composite(image, transparent_image, mask)

    return masked_image

def replace_right_with_transparency(image_path, replace_percentage):
    """
    Заменяет X% области изображения справа на прозрачность.
    
    :param image_path: Путь к исходному изображению.
    :param replace_percentage: Процент от ширины изображения, который нужно заменить на прозрачность.
    :return: Изображение с заменённой областью.
    """
    # Открываем изображение
    image = Image.open(image_path).convert("RGBA")  # Конвертируем в RGBA для поддержки альфа-канала

    # Получаем размеры изображения
    width, height = image.size

    # Вычисляем количество пикселей для замены
    replace_width = int(width * (replace_percentage / 100))

    # Создаем новый массив пикселей для изображения с прозрачностью
    data = image.getdata()

    # Создаем новое изображение с прозрачным слоем
    new_data = []
    for i, item in enumerate(data):
        # Заменяем пиксели из правой части на прозрачные
        if (i % width) >= (width - replace_width):
            new_data.append((0, 0, 0, 0))  # Прозрачный пиксель
        else:
            new_data.append(item)  # Оригинальный пиксель
    
    # Создаем новое изображение с обновленными данными
    new_image = Image.new("RGBA", image.size)
    new_image.putdata(new_data)

    return new_image

def generate_bar(p):
    img = replace_right_with_transparency('images/skills/power.png', p)
    mask = Image.open('images/skills/progress_mask.png')
    ret = apply_mask(mask, img)

    return ret



# img = replace_right_with_transparency('images/skills/power.png', 34)
# mask = Image.open('images/skills/progress_mask.png')

# bar = apply_mask(mask, img)
# width, height = bar.size
# bar = bar.resize((width // 2, height // 2))

# ret = text_on_image()

# ret = trans_paste(bar, ret, 1, (450, 86 - 3))

# bar_position = {
#     'power': 83,
#     'dexterity': 151,
#     'intelligence': 220,
#     'charisma': 289
# }

# ret = text_on_image()
# a = -1
# for i in ['Power', 'Dexterity', 'Intelligence', 'Charisma']:
#     a += 1

#     img = replace_right_with_transparency(f'images/skills/{i.lower()}.png', random.randint(0, 100))
#     mask = Image.open('images/skills/progress_mask.png')

#     bar = apply_mask(mask, img)
#     width, height = bar.size
#     bar = bar.resize((width // 2, height // 2))

#     ret = trans_paste(bar, ret, 1, (450, bar_position[i.lower()]) )

# ret.show()

def t(text: str, lang): return text.capitalize()

bar_position = {
    'power': 83,
    'dexterity': 151,
    'intelligence': 220,
    'charisma': 289
}

def create_skill_image(dino_id, lang, chars: dict):
    img = Image.open('images/skills/bg.png')
    idraw = ImageDraw.Draw(img)

    dino_data = DINOS['elements'][str(dino_id)]

    y, x = 43, 467
    y_plus = 68

    a = -1
    for char in ['power', 'dexterity', 'intelligence', 'charisma']:
        text = t(char, lang)
        a += 1

        x = centre_var(img, comf, text, 467, 754)
        idraw.text(
            (x, y + (y_plus * a)), text, 'white', font=comf, stroke_width=0
        )

        percnet = chars[char] * 5
        char_fill = replace_right_with_transparency(f'images/skills/{char}.png', 
                                              100 - percnet)
        mask = Image.open('images/skills/progress_mask.png')

        bar = apply_mask(mask, char_fill)
        width, height = bar.size
        bar = bar.resize((width // 2, height // 2))

        img = trans_paste(bar, img, 1, (450, bar_position[char]) )

    return img

chars = {
    'power': 1,
    'dexterity': 10,
    'intelligence': 20,
    'charisma': 18
}

img = create_skill_image(1, 'lang', chars)
img.show()