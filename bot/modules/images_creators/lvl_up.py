


import io
from PIL import Image
from PIL import ImageDraw, ImageFilter

from bot.exec import bot
from bot.modules.data_format import pil_image_to_file
from bot.modules.images import async_open, trans_paste

from aiogram.types import BufferedInputFile
from bot.exec import bot

back_file = 'images/lvl_up/bg.png'
upper_file = 'images/lvl_up/upper.png'

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

async def lvl_up_image(avatar_file: str | BufferedInputFile = ''):
    # Открываем фоновое изображение
    img = Image.open(back_file).convert("RGBA")

    if isinstance(avatar_file, str):
        file_info = await bot.get_file(avatar_file)
        if file_info and file_info.file_path:
            imageBinaryBytes = await bot.download_file(file_info.file_path)
            if imageBinaryBytes:
                imageStream = io.BytesIO(imageBinaryBytes.read())
                avatar = Image.open(imageStream).convert('RGBA')
        else:
            avatar = await async_open('images/remain/dinogochi_user.png')
    else:
        # Если avatar_file — это BufferedInputFile, читаем его содержимое и открываем как изображение
        imageStream = io.BytesIO(avatar_file.data)
        avatar = Image.open(imageStream).convert('RGBA')

    # Открываем и обрезаем аватар
    # avatar = Image.open(avatar_file).convert("RGBA")
    avatar_cropped = crop_circle(avatar, 100)  # 100 - размер аватара

    # Открываем изображение upper.png
    upper = Image.open(upper_file).convert("RGBA")

    # Накладываем upper.png на аватар
    avatar_with_upper = avatar_cropped.copy()

    # Вставляем аватар с upper на итоговое изображение
    img = await trans_paste(avatar_with_upper, img, alpha=1.0, box=(55, 65))

    img = await trans_paste(upper, img, alpha=1.0, box=(0, 0))

    # Убираем прозрачность: заменяем прозрачные пиксели на чёрные
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    background = Image.new("RGBA", img.size, (0, 0, 0, 255))
    background.paste(img, mask=img.split()[3])  # Используем альфа-канал как маску
    img_no_alpha = background.convert("RGB")  # Убираем альфа-канал

    return pil_image_to_file(img_no_alpha, quality='maximum')