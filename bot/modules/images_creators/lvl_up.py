


import io
from typing import Any
from PIL import Image
from PIL import ImageDraw, ImageFont, ImageFilter

from bot.exec import bot
from bot.modules.data_format import pil_image_to_file
from bot.modules.images import async_open, trans_paste

from aiogram.types import BufferedInputFile
from bot.exec import bot

back_file = 'images/lvl_up/bg.png'
upper_file = 'images/lvl_up/upper.png'

def crop_circle(img: Image.Image, size: int) -> Image.Image:
    """Обрезает изображение по кругу с качественным сглаживанием."""
    with img.resize((size, size), Image.LANCZOS).convert("RGBA") as img_rgba:
        with Image.new('L', (size, size), 0) as mask:
            draw = ImageDraw.Draw(mask)
            # Нарисуем эллипс чуть меньше, чтобы избежать резких краёв
            inset = 2
            draw.ellipse((inset, inset, size - inset, size - inset), fill=255)
            # Применим лёгкое размытие только по краю
            with mask.filter(ImageFilter.GaussianBlur(radius=1)) as mask_blurred:
                result = Image.new('RGBA', (size, size))
                result.paste(img_rgba, (0, 0), mask_blurred)
                return result

async def lvl_up_image(avatar_file: str | BufferedInputFile = ''):
    # Открываем фоновое изображение
    with Image.open(back_file) as back_orig:
        img = back_orig.convert("RGBA")

    avatar_is_pil = False
    imageStream = None
    if isinstance(avatar_file, str) and avatar_file:
        try:
            file_info = await bot.get_file(avatar_file)
            if file_info and file_info.file_path:
                imageBinaryBytes = await bot.download_file(file_info.file_path)
                if imageBinaryBytes:
                    imageStream = io.BytesIO(imageBinaryBytes.read())
                    avatar = Image.open(imageStream).convert('RGBA')
                    avatar_is_pil = True
            else:
                avatar = await async_open('images/remain/dinogochi_user.png')
                avatar_is_pil = True
        except Exception:
            avatar = await async_open('images/remain/dinogochi_user.png')
            avatar_is_pil = True
    else:
        # Handle both BufferedInputFile (with .data) and file-like objects (e.g. BufferedReader)
        if avatar_file and hasattr(avatar_file, "data"):
            imageStream = io.BytesIO(avatar_file.data)
            avatar = Image.open(imageStream).convert('RGBA')
            avatar_is_pil = True
        elif avatar_file:
            avatar = Image.open(avatar_file).convert('RGBA')
            avatar_is_pil = True
        else:
            avatar = await async_open('images/remain/dinogochi_user.png')
            avatar_is_pil = True

    try:
        # Открываем и обрезаем аватар
        with crop_circle(avatar, 100) as avatar_cropped:
            # Открываем изображение upper.png
            with Image.open(upper_file) as upper_orig:
                with upper_orig.convert("RGBA") as upper:
                    # Накладываем upper.png на аватар
                    with avatar_cropped.copy() as avatar_with_upper:
                        # Вставляем аватар с upper на итоговое изображение
                        img = trans_paste(avatar_with_upper, img, alpha=1.0, box=(55, 65))
                        img = trans_paste(upper, img, alpha=1.0, box=(0, 0))

        # Убираем прозрачность: заменяем прозрачные пиксели на чёрные
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        with Image.new("RGBA", img.size, (0, 0, 0, 255)) as background:
            background.paste(img, mask=img.split()[3])  # Используем альфа-канал как маску
            img_no_alpha = background.convert("RGB")  # Убираем альфа-канал
    finally:
        if avatar_is_pil:
            try:
                avatar.close()
            except Exception: pass
        if imageStream:
            try:
                imageStream.close()
            except Exception: pass
        try:
            img.close()
        except Exception: pass
        if avatar_file and hasattr(avatar_file, "close"):
            try:
                avatar_file.close()
            except Exception: pass

    return pil_image_to_file(img_no_alpha, quality='maximum')