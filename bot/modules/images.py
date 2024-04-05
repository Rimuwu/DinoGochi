import io
from random import choice, randint

import requests
from PIL import Image, ImageDraw, ImageFont
from telebot.util import pil_image_to_file

from bot.const import DINOS, GAME_SETTINGS
from bot.modules.data_format import seconds_to_str
from bot.modules.localization import get_data
import asyncio

# from concurrent.futures import ThreadPoolExecutor
# POOL = ThreadPoolExecutor()


FONTS = {
    'line30': ImageFont.truetype('fonts/Aqum.otf', size=30),
    'line25': ImageFont.truetype('fonts/Aqum.otf', size=25),
    'line35': ImageFont.truetype('fonts/Aqum.otf', size=35),
    'line45': ImageFont.truetype('fonts/Aqum.otf', size=45),
    'line55': ImageFont.truetype('fonts/Aqum.otf', size=55),
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
        'game': (440, 280),
        'mood': (585, 280),
        'energy': (730, 280),
        'age_resizing': (450, 385, -180),
        'line': 'line25'
    },
    3: {
        'heal': (157, 50),
        'eat': (298, 50),
        'game': (440, 50),
        'mood': (585, 50),
        'energy': (730, 50),
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

async def async_open(image_path, to_file: bool = False):
    loop = asyncio.get_running_loop()

    try:
        img = await loop.run_in_executor(None, Image.open, image_path)
        if to_file:
            return pil_image_to_file(img)
        return img
    except Exception as err:
        print(f"Error loading image at path {image_path} with exception: {err}")

    return Image.new('RGB', (100, 100))


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

async def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=10.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img

async def create_eggs_image_pst():
    """Создаёт изображение выбора яиц.
    """
    id_l = [] #Хранит id яиц
    bg_p = await async_open(
        f'images/remain/egg_ask/{choice(GAME_SETTINGS["egg_ask_backs"])}.png'
        ) #Случайный фон

    for i in range(3):
        rid = str(choice(list(DINOS['data']['egg']))) #Выбираем рандомное яйцо
        image = await async_open('images/' + str(DINOS['elements'][rid]['image']))
        bg_p = await trans_paste(image, bg_p, 1.0, (i * 512, 0)) #Накладываем изображение
        id_l.append(rid)

    return pil_image_to_file(bg_p), id_l

async def create_eggs_image():
    """Создаёт изображение выбора яиц.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, create_eggs_image_pst)

    rss = await result
    return rss

async def create_egg_image_pst(egg_id: int, rare: str='random', 
                               seconds: int=0, lang: str='en'):
    """Создаёт изобраение инкубации яйца
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

    bg_p = await async_open(f'images/remain/egg_profile.png')
    egg = await async_open(f'images/{DINOS["elements"][str(egg_id)]["image"]}')
    egg = egg.resize((290, 290), Image.Resampling.LANCZOS)
    img = await trans_paste(egg, bg_p, 1.0, (-50, 40))
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

    return pil_image_to_file(img)

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
    result = await loop.run_in_executor(None, create_egg_image_pst, 
                                        egg_id, rare, seconds, lang)

    rss = await result
    return rss

async def create_dino_image_pst(dino_id: int, stats: dict, quality: str='com', profile_view: int=1, age: int = 30, custom_url: str=''):
    """Создание изображения динозавра
       Args:
       dino_id - id картинки динозавра
       stats - словарь с харрактеристиками динозавра ( {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0} )
    """

    # Получение данных
    dino_data = DINOS['elements'][str(dino_id)]
    img = await async_open(
            f'images/remain/backgrounds/{dino_data["class"].lower()}.png')

    # Получение кастом картинки
    if custom_url:
        try:
            response = requests.get(custom_url, stream = True)
            response = await async_open(io.BytesIO(response.content))
            response = response.convert("RGBA")
            img = response.resize((900, 350), Image.Resampling.LANCZOS)
        except: custom_url = ''

    if profile_view != 4:
        panel_i = await async_open(
            f'images/remain/panels/v{profile_view}_{quality}.png')
        img = await trans_paste(panel_i, img, 1.0)

    dino_image = await async_open(f'images/{dino_data["image"]}')
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

    # Рисует квадрат границы динозавра
    # idraw.rectangle((y + x, y, sz + y + x, sz + y), outline=(255, 0, 0))

    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
    img = await trans_paste(dino_image, img, 1.0, (y + x, y, sz + y + x, sz + y))

    return pil_image_to_file(img)

async def create_dino_image(dino_id: int, stats: dict, quality: str='com', profile_view: int=1, age: int = 30, custom_url: str=''):
    """Создание изображения динозавра
       Args:
       dino_id - id картинки динозавра
       stats - словарь с харрактеристиками динозавра ( {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0} )
    """

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, create_dino_image_pst, dino_id, stats, quality, profile_view, age, custom_url)

    return await result

async def dino_game_pst(dino_id: int, add_dino_id: int = 0):
    n_img = randint(1, 2)
    img = await async_open(f"images/actions/game/{n_img}.png")

    if not add_dino_id:
        sz, x, y = 412, randint(120, 340), randint(-65, -35)
    else:
        sz, x, y = 350, 20, -5
        x2, y2 = 420, -15

        dino_data = DINOS['elements'][str(add_dino_id)]
        dino_image = await async_open(f'images/{dino_data["image"]}')
        dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
        img = await trans_paste(dino_image, img, 1.0, 
                        (x2 + y2, y2, sz + x2 + y2, sz + y2))

    dino_data = DINOS['elements'][str(dino_id)]
    dino_image = await async_open(f'images/{dino_data["image"]}')

    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
    dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

    img = await trans_paste(dino_image, img, 1.0, 
                      (x + y, y, sz + x + y, sz + y))
    return pil_image_to_file(img)

async def dino_game(dino_id: int, add_dino_id: int = 0):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, dino_game_pst, 
            dino_id, add_dino_id)

    rss = await result
    return rss

async def dino_journey_pst(dino_id: int, journey_way: str, add_dino_id: int = 0):
    assert journey_way in ['desert', 'forest', 'magic-forest', 'mountains', 'lost-islands'], f'Путь путешествия {journey_way} не найден'

    n_img, sz = randint(1, 12), 350

    bg_p = await async_open(f"images/actions/journey/{journey_way}/{n_img}.png")
    bg_p = bg_p.resize((900, 350), Image.Resampling.LANCZOS)

    dino_image = await async_open("images/" + 
                        str(DINOS['elements'][str(dino_id)]['image']))
    dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)
    dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

    x, y = 80, 25
    img = await trans_paste(dino_image, bg_p, 1.0, (x + y, y, sz + x + y, sz + y))

    if add_dino_id:
        sz = 320
        dino_image = await async_open("images/" + str(
            DINOS['elements'][str(add_dino_id)]['image']))
        dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)

        x, y = 450, 35
        img = await trans_paste(dino_image, bg_p, 1.0, (x + y, y, sz + x + y, sz + y))

    return pil_image_to_file(img)

async def dino_journey(dino_id: int, journey_way: str, add_dino_id: int = 0):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, dino_journey_pst, 
            dino_id, journey_way, add_dino_id)

    rss = await result
    return rss

async def dino_collecting_pst(dino_id: int, col_type: str):
    img = await async_open(f"images/actions/collecting/{col_type}.png")

    dino_data = DINOS['elements'][str(dino_id)]
    dino_image = await async_open(f'images/{dino_data["image"]}')

    sz, x, y = 350, 50, 10

    dino_image = dino_image.resize((sz, sz), Image.Resampling.BILINEAR)
    dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

    img = await trans_paste(dino_image, img, 1.0, 
                      (x + y, y, sz + x + y, sz + y))
    return pil_image_to_file(img)

async def dino_collecting(dino_id: int, col_type: str):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, dino_collecting_pst, 
            dino_id, col_type)

    rss = await result
    return rss

async def market_image_pst(custom_url, status):
    try:
        response = requests.get(custom_url, stream = True)
        response = await async_open(io.BytesIO(response.content))
        response = response.convert("RGBA")
        img = response.resize((900, 350), Image.Resampling.LANCZOS)
        img = pil_image_to_file(img)
    except: 
        img = await async_open(f'images/remain/market/{status}.png', True)
    return img

async def market_image(custom_url, status):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, market_image_pst, 
            custom_url, status)

    rss = await result
    return rss