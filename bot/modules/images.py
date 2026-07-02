import io
from random import choice, randint

from PIL import Image, ImageDraw, ImageFont
from bot.modules.data_format import pil_image_to_file

from bot.exec import main_router, bot
from bot.const import DINOS, GAME_SETTINGS
from bot.modules.data_format import seconds_to_str
from bot.modules.localization import get_data, t
import asyncio

from bot.modules.logs import log
from bot.models.other import Event

# from concurrent.futures import ThreadPoolExecutor
# POOL = ThreadPoolExecutor()


FONTS = {
    'line30': ImageFont.truetype('fonts/Aqum.otf', size=30),
    'line25': ImageFont.truetype('fonts/Aqum.otf', size=25),
    'line20': ImageFont.truetype('fonts/Aqum.otf', size=20),
    'line35': ImageFont.truetype('fonts/Aqum.otf', size=35),
    'line45': ImageFont.truetype('fonts/Aqum.otf', size=45),
    'line55': ImageFont.truetype('fonts/Aqum.otf', size=55),
    'comf35': ImageFont.truetype('fonts/Comfortaa.ttf', size=35)
}

positions = {
    1: {
        'heal': (518, 93),
        'eat': (518, 170),
        'game': (718, 93),
        'mood': (718, 170),
        'energy': (718, 247),
        'age_resizing': (400, 75, -60),
        'line': 'line30'
    },
    2: {
        'heal': (157, 280),
        'eat': (298, 280),
        'energy': (440, 280),
        'game': (585, 280),
        'mood': (730, 280),
        'age_resizing': (450, 385, -180),
        'line': 'line25'
    },
    3: {
        'heal': (157, 50),
        'eat': (298, 50),
        'energy': (440, 50),
        'game': (585, 50),
        'mood': (730, 50),
        'age_resizing': (450, 275, -80),
        'line': 'line25'
    }
}

img_dates = {
    'random': (207, 70, 204),
    'com': (108, 139, 150),
    'unc': (68, 235, 90),
    'rar': (68, 143, 235),
    'mys': (230, 103, 175),
    'leg': (255, 212, 59)
}


def clown_nose(image, radius=15):
    if radius > 15: radius = 15
    
    alpha = image.getchannel("A")

    non_transparent_pixels = [
        (x, y) for y in range(alpha.height) for x in range(alpha.width) 
        if alpha.getpixel((x, y)) > 0 and y < alpha.height - alpha.height // 8
    ]

    # Поиск самого левого и верхнего непрозрачного пикселя
    if non_transparent_pixels:
        top_left_pixel = min(non_transparent_pixels, key=lambda p: (p[0], p[1]))  # Сначала сортируем по X, затем по Y
        x, y = top_left_pixel

        # Создание объекта для рисования
        draw = ImageDraw.Draw(image)

        # Рисование красного круга радиусом 2
        draw.rectangle((x - radius, y - radius, x + radius, y + radius), outline="red", fill="red")

    return image


def centre_var(image, font, message, start_var=0, end_var=250):
    """ Возвращает координату середины для текста 
    """
    draw = ImageDraw.Draw(image)
    _, _, w, h = draw.textbbox((0, 0), message, font=font)
    var = (end_var - start_var - w) / 2 + start_var

    return var

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

async def async_open(image_path, to_file: bool = False):
    loop = asyncio.get_running_loop()

    try:
        img = await loop.run_in_executor(None, Image.open, image_path)
        if to_file:
            return pil_image_to_file(img, quality='maximum')
        return img
    except Exception as err:
        print(f"Error loading image at path {image_path} with exception: {err}")

    if to_file:
        return open(image_path, 'rb')
    return open(image_path)


def age_size(age, max_size, days): return age * ((max_size-150) // days) + 150

def vertical_resizing(age: int, max_size, max_x, max_y, days = 30):
    if age > days: age = days
    f = age_size(age, max_size, days)
    x = int(age * ((max_x) / days))
    y = int(age * ((max_y-150) / days)+150)
    return f, x, y

def horizontal_resizing(age: int, max_size, max_x, max_y, days = 30):
    f = age_size(age, max_size, days)
    x = int(age * ((max_x-250) / days)+250)
    y = int(age * ((max_y-100) / days)+100)
    return f, x, y

def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=1.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img

def create_eggs_image_pst(eggs: list[int]):
    """Создаёт изображение выбора яиц.
    """
    bg_p = Image.open(
        f'images/remain/egg_ask/{choice(GAME_SETTINGS["egg_ask_backs"])}.png'
    ) #Случайный фон

    for i in range(3):
        rid = str(eggs[i])
        image = Image.open('images/' + str(DINOS['elements'][rid]['image']))
        bg_p = trans_paste(image, bg_p, 1.0, (i * 512, 0)) #Накладываем изображение

    return pil_image_to_file(bg_p, quality='maximum')

async def create_eggs_image(eggs: list[int]):
    """Создаёт изображение выбора яиц.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_eggs_image_pst, eggs)

def create_egg_image_pst(egg_id: int, rare: str='random', 
                              seconds: int=0, lang: str='en'):
    """Создаёт изображение инкубации яйца
       Args:
       egg_id - id яйца
       rare - редкость (от этого зависит цвет надписи)
       seconds - секунды до конца инкубации
       lang - язык текста
    """
    rares = get_data('rare', lang)
    time_end = seconds_to_str(seconds, lang, mini=True)
    text_dict = get_data('p_profile', lang)

    quality_text = rares[rare][1]
    fill = img_dates[rare]

    bg_p = Image.open(f'images/remain/egg_profile.png')
    egg = Image.open(f'images/{DINOS["elements"][str(egg_id)]["image"]}')
    egg = egg.resize((290, 290), Image.Resampling.LANCZOS)
    img = trans_paste(egg, bg_p, 1.0, (-50, 40))
    idraw = ImageDraw.Draw(img)

    idraw.text((310, 120), text_dict['text_info'], 
            font=FONTS['line55'],
            stroke_width=1)
    idraw.text((210, 210), text_dict['text_ost'], 
            font=FONTS['line45'])
    idraw.text(text_dict['time_position'], time_end, 
            font=FONTS['line35'], )
    idraw.text((210, 270), text_dict['rare_name'],
            font=FONTS['line45'])
    idraw.text(text_dict['rare_position'], quality_text, 
            font=FONTS['line35'], fill=fill)

    return pil_image_to_file(img, quality='maximum')

async def create_egg_image(egg_id: int, rare: str='random', 
                           seconds: int=0, lang: str='en'):
    """Создаёт изобраение инкубации яйца
       Args:
       egg_id - id яйца
       rare - редкость (от этого зависит цвет надписи)
       seconds - секунды до конца инкубации
       lang - язык текста
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_egg_image_pst, 
                                        egg_id, rare, seconds, lang)

def create_dino_centered_image_pst(dino_id: int):
    """Генерирует изображение динозавра, расположенного по центру стандартного фона."""
    dino_data = DINOS['elements'][str(dino_id)]
    bg_img = Image.open(f'images/remain/backgrounds/{dino_data["class"].lower()}.png')
    bg_img = bg_img.convert("RGBA")
    bg_width, bg_height = bg_img.size

    dino_img = Image.open(f'images/{dino_data["image"]}')
    dino_img = dino_img.resize((1024, 1024), Image.Resampling.LANCZOS)

    sz = min(bg_width, bg_height)
    dino_img = dino_img.resize((sz, sz), Image.Resampling.LANCZOS)

    x = (bg_width - sz) // 2
    y = (bg_height - sz) // 2 - 50

    result_img = trans_paste(dino_img, bg_img, 1.0, (x, y, x + sz, y + sz))
    return pil_image_to_file(result_img, quality='maximum')

async def create_dino_centered_image(dino_id: int):
    """
    Генерирует изображение динозавра, расположенного по центру стандартного фона по классу динозавра.
    Args:
        dino_id: id картинки динозавра
    Returns:
        Файл изображения в формате, пригодном для отправки
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_dino_centered_image_pst, dino_id)

def create_dino_image_pst(dino_id: int, stats: dict, quality: str='com', profile_view: int=1, age: int = 30, custom_image_bytes: bytes = None, is_april_1: bool = False):
    """Создание изображения динозавра
       Args:
       dino_id - id картинки динозавра
       stats - словарь с харрактеристиками динозавра ( {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0} )
    """
    dino_data = DINOS['elements'][str(dino_id)]
    
    if custom_image_bytes:
        try:
            imageStream = io.BytesIO(custom_image_bytes)
            img = Image.open(imageStream).resize((900, 350)).convert('RGBA')
        except Exception as err:
            log(f'Error loading custom image from bytes: {err}')
            img = Image.open(f'images/remain/backgrounds/{dino_data["class"].lower()}.png')
    else:
        img = Image.open(f'images/remain/backgrounds/{dino_data["class"].lower()}.png')

    if profile_view != 4:
        panel_i = Image.open(f'images/remain/panels/v{profile_view}_{quality}.png')
        img = trans_paste(panel_i, img, 1.0)

    dino_image = Image.open(f'images/{dino_data["image"]}')
    dino_image = dino_image.resize((1024, 1024), Image.Resampling.LANCZOS)
    idraw = ImageDraw.Draw(img)

    if profile_view != 4:
        p_data = positions[profile_view]
        line = FONTS[p_data['line']]
        if profile_view == 1:
            sz, x, y = vertical_resizing(age, *p_data['age_resizing'])
        else:
            sz, x, y = horizontal_resizing(age, *p_data['age_resizing'])

        for char in ['heal', 'eat', 'game', 'mood', 'energy']:
            idraw.text(p_data[char], f'{stats[char]}%', font = line)

    elif profile_view == 4:
        sz, x, y = horizontal_resizing(age, 450, randint(170, 550), randint(-180, -100))
        if randint(0, 1):
            dino_image = dino_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)

    if is_april_1:
        dino_image = clown_nose(dino_image, age // 4)

    img = trans_paste(dino_image, img, 1.0, (y + x, y, sz + y + x, sz + y))

    return pil_image_to_file(img, quality='maximum')

async def create_dino_image(dino_id: int, stats: dict, quality: str='com', profile_view: int=1, age: int = 30, custom_url: str=''):
    """Создание изображения динозавра
       Args:
       dino_id - id картинки динозавра
       stats - словарь с харрактеристиками динозавра ( {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0} )
    """
    custom_image_bytes = None
    if custom_url:
        try:
            file_info = await bot.get_file(custom_url)
            if file_info and file_info.file_path:
                downloaded_file = await bot.download_file(file_info.file_path)
                if downloaded_file:
                    custom_image_bytes = downloaded_file.read()
        except Exception as err:
            log(f'Error downloading custom image {custom_url}: {err}')

    is_april_1 = await Event.check_event('april_1')

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        create_dino_image_pst,
        dino_id,
        stats,
        quality,
        profile_view,
        age,
        custom_image_bytes,
        is_april_1
    )

def dino_game_pst(dino_id: int, add_dino_id: int = 0):
    n_img = randint(1, 2)
    img = Image.open(f"images/actions/game/{n_img}.png")

    if not add_dino_id:
        sz, x, y = 412, randint(120, 340), randint(-65, -35)
    else:
        sz, x, y = 350, 20, -5
        x2, y2 = 420, -15

        dino_data = DINOS['elements'][str(add_dino_id)]
        dino_image = Image.open(f'images/{dino_data["image"]}')
        dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
        img = trans_paste(dino_image, img, 1.0, 
                        (x2 + y2, y2, sz + x2 + y2, sz + y2))

    dino_data = DINOS['elements'][str(dino_id)]
    dino_image = Image.open(f'images/{dino_data["image"]}')

    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
    dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

    img = trans_paste(dino_image, img, 1.0, 
                      (x + y, y, sz + x + y, sz + y))
    return pil_image_to_file(img, quality='maximum')

async def dino_game(dino_id: int, add_dino_id: int = 0):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, dino_game_pst, 
            dino_id, add_dino_id)

def dino_journey_pst(dino_id: int, journey_way: str, add_dino_id: int = 0):
    assert journey_way in ['desert', 'forest', 'magic-forest', 'mountains', 'lost-islands'], f'Путь путешествия {journey_way} не найден'

    n_img, sz = randint(1, 12), 350

    bg_p = Image.open(f"images/actions/journey/{journey_way}/{n_img}.png")
    bg_p = bg_p.resize((900, 350), Image.Resampling.LANCZOS)

    dino_image = Image.open("images/" + 
                        str(DINOS['elements'][str(dino_id)]['image']))
    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
    dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

    x, y = 80, 25
    img = trans_paste(dino_image, bg_p, 1.0, (x + y, y, sz + x + y, sz + y))

    if add_dino_id:
        sz = 320
        dino_image = Image.open("images/" + str(
            DINOS['elements'][str(add_dino_id)]['image']))
        dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)

        x, y = 450, 35
        img = trans_paste(dino_image, bg_p, 1.0, (x + y, y, sz + x + y, sz + y))

    return pil_image_to_file(img, quality='maximum')

async def dino_journey(dino_id: int, journey_way: str, add_dino_id: int = 0):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, dino_journey_pst, 
            dino_id, journey_way, add_dino_id)

def dino_collecting_pst(dino_id: int, col_type: str):
    img = Image.open(f"images/actions/collecting/{col_type}.png")

    dino_data = DINOS['elements'][str(dino_id)]
    dino_image = Image.open(f'images/{dino_data["image"]}')

    sz, x, y = 350, 50, 10

    dino_image = dino_image.resize((sz, sz), Image.Resampling.BILINEAR)
    dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

    img = trans_paste(dino_image, img, 1.0, 
                      (x + y, y, sz + x + y, sz + y))
    return pil_image_to_file(img, quality='maximum')

async def dino_collecting(dino_id: int, col_type: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, dino_collecting_pst, 
            dino_id, col_type)

bar_position = {
    'power': 83,
    'dexterity': 151,
    'intelligence': 220,
    'charisma': 289
}

def create_skill_image_pst(dino_id, age, lang, chars: dict):
    img = Image.open('images/skills/bg.png')
    idraw = ImageDraw.Draw(img)

    font = FONTS['comf35']
    dino_data = DINOS['elements'][str(dino_id)]
    
    p_data = positions[1]
    dino_image = Image.open(f'images/{dino_data["image"]}')
    dino_image = dino_image.resize((1024, 1024), Image.Resampling.LANCZOS)

    sz, x, y = vertical_resizing(age, *p_data['age_resizing'])
    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
    img = trans_paste(dino_image, img, 1.0, (y + x, y, sz + y + x, sz + y))

    y, x = 43, 467
    y_plus = 68

    a = -1
    for char in ['power', 'dexterity', 'intelligence', 'charisma']:
        if lang not in ['ru', 'en']: lang = 'en'
        text = t(f'skills_profile.chars.{char}', lang)
        a += 1

        x = centre_var(img, font, text, 467, 754)
        idraw.text(
            (x, y + (y_plus * a)), text, 'white', font=font, stroke_width=0
        )

        percent = chars[char] * 5
        char_fill = replace_right_with_transparency(
                        f'images/skills/{char}.png',  100 - percent)
        mask = Image.open('images/skills/progress_mask.png')

        bar = apply_mask(mask, char_fill)
        width, height = bar.size
        bar = bar.resize((width // 2, height // 2))

        img = trans_paste(bar, img, 1, (450, bar_position[char]) )

    return pil_image_to_file(img, quality='maximum')

async def create_skill_image(dino_id, age, lang, chars: dict):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_skill_image_pst, dino_id, age, lang, chars)

def create_combat_image_pst(dino_id: int, stats: dict, custom_image_bytes: bytes = None):
    dino_data = DINOS['elements'][str(dino_id)]
    
    if custom_image_bytes:
        try:
            imageStream = io.BytesIO(custom_image_bytes)
            img = Image.open(imageStream).resize((900, 350)).convert('RGBA')
        except Exception as err:
            log(f'Error loading custom image from bytes: {err}')
            img = Image.open(f'images/remain/backgrounds/{dino_data["class"].lower()}.png').convert('RGBA')
    else:
        img = Image.open(f'images/remain/backgrounds/{dino_data["class"].lower()}.png').convert('RGBA')

    idraw = ImageDraw.Draw(img)

    dino_image = Image.open(f'images/{dino_data["image"]}')
    dino_image = dino_image.resize((180, 180), Image.Resampling.LANCZOS)
    
    cx, cy = 450, 175
    img = trans_paste(dino_image, img, 1.0, (cx - 90, cy - 90, cx + 90, cy + 90))

    idraw = ImageDraw.Draw(img)

    r = 145
    width = 15
    bbox = [cx - r, cy - r, cx + r, cy + r]

    hp_pct = max(0.0, min(1.0, stats.get('heal', 100) / 100.0))
    str_pct = max(0.0, min(1.0, stats.get('power', 0.0) / 20.0))
    dex_pct = max(0.0, min(1.0, stats.get('dexterity', 0.0) / 20.0))

    bg_color = (80, 80, 80, 255)
    
    idraw.arc(bbox, 95, 205, fill=bg_color, width=width)
    idraw.arc(bbox, 215, 325, fill=bg_color, width=width)
    idraw.arc(bbox, 335, 85, fill=bg_color, width=width)

    if hp_pct > 0:
        hp_end = 95 + int(110 * hp_pct)
        idraw.arc(bbox, 95, hp_end, fill=(46, 204, 113, 255), width=width)
        
    if str_pct > 0:
        str_end = 215 + int(110 * str_pct)
        idraw.arc(bbox, 215, str_end, fill=(231, 76, 60, 255), width=width)

    if dex_pct > 0:
        dex_end = 335 + int(110 * dex_pct)
        idraw.arc(bbox, 335, dex_end, fill=(52, 152, 219, 255), width=width)

    return pil_image_to_file(img, quality='maximum')

async def create_combat_image(dino_id: int, stats: dict, custom_url: str = ''):
    custom_image_bytes = None
    if custom_url:
        from PIL import Image
        if isinstance(custom_url, Image.Image):
            try:
                img_byte_arr = io.BytesIO()
                custom_url.save(img_byte_arr, format='PNG')
                custom_image_bytes = img_byte_arr.getvalue()
            except Exception as err:
                log(f'Error converting PIL Image to bytes: {err}')
        elif isinstance(custom_url, str) and custom_url.startswith('images/'):
            try:
                with open(custom_url, 'rb') as f:
                    custom_image_bytes = f.read()
            except Exception as err:
                log(f'Error reading local custom image file {custom_url}: {err}')
        else:
            try:
                file_info = await bot.get_file(custom_url)
                if file_info and file_info.file_path:
                    downloaded_file = await bot.download_file(file_info.file_path)
                    if downloaded_file:
                        custom_image_bytes = downloaded_file.read()
            except Exception as err:
                log(f'Error downloading custom image {custom_url}: {err}')

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        create_combat_image_pst,
        dino_id,
        stats,
        custom_image_bytes
    )