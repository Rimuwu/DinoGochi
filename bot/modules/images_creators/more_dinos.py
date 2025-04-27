from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bot.modules.data_format import crop_text, pil_image_to_file
from bot.modules.images import async_open, centre_var, trans_paste
from bot.const import DINOS

from bot.modules.images import FONTS

small = FONTS['line20']

async def MiniGame_image(dinosaurs: list[dict], back_file: str):
    """
    
    dinosaurs: {"dino_id": int, "name": str}
    
    """

    # Фон
    img = await async_open(f'images/{back_file}')
    idraw = ImageDraw.Draw(img)

    sz = 365
    y = -80
    margin = 5  # отступ от краев
    offset_y = 50  # смещение по y для нижних динозавров
    offset_x = 70  # смещение по x для нижних динозавров
    img_width, img_height = img.size

    positions = [
        (margin, y),  # левый верхний
        (img_width - margin - sz, y),  # правый верхний
        (margin + offset_x, y + offset_y),  # левый нижний
        (img_width - margin - sz - offset_x, y + offset_y)  # правый нижний
    ]

    for ind in range(len(dinosaurs)):
        dino_id = dinosaurs[ind]['dino_id']

        dino_data = DINOS['elements'][str(dino_id)]

        dino_image = await async_open(f'images/{dino_data["image"]}')
        dino_image = dino_image.resize((sz, sz), Image.Resampling.LANCZOS)

        x, y = positions[ind]
        if ind % 2 == 0:
            dino_image = dino_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        img = await trans_paste(dino_image, img, alpha=1, box=(x, y))

        # Технический вывод
        # idraw.rectangle((x, y, x+sz, y+sz), outline=(255, 0, 0))
        # idraw.text((x + 5, y + 90), str(ind), 'white', font=l, stroke_width=0)

        #Координаты текста
        text = crop_text(dinosaurs[ind]['name'], 15)
        center_x = centre_var(img, small, text, x, x + sz)
        text_y = y + 150

        if ind in (2, 3): text_y += 190

        # Получаем размеры текста
        draw = ImageDraw.Draw(img)
        text_bbox = draw.textbbox((center_x, text_y), text, font=small)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1] + 10

        # Создаём полупрозрачный чёрный прямоугольник с закруглёнными краями
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        rect_x0 = center_x - 5
        rect_y0 = text_y - 2
        rect_x1 = center_x + text_w + 5
        rect_y1 = text_y + text_h + 2
        rect_color = (0, 0, 0, int(255 * 0.6))  # 60% прозрачности
        radius = 10  # радиус скругления

        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=radius, fill=rect_color)

        # Применяем фильтр размытия к краям прямоугольника
        # Для этого создаём маску только для прямоугольника
        mask = Image.new('L', img.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=radius, fill=255)
        blurred_overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2))
        # Смешиваем размытую и обычную часть
        overlay = Image.composite(blurred_overlay, overlay, mask)

        img = Image.alpha_composite(img.convert('RGBA'), overlay)

        # Рисуем текст поверх прямоугольника
        idraw = ImageDraw.Draw(img)
        idraw.text((center_x, text_y), text, font=small)

    return pil_image_to_file(img, 'png', 'maximum')