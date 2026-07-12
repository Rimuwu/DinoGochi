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
    if dinosaurs:
        sz = 365
        y_init = -80
        margin = 5  # отступ от краев
        offset_y = 50  # смещение по y для нижних динозавров
        offset_x = 70  # смещение по x для нижних динозавров
        img_width, img_height = img.size

        positions = [
            (margin, y_init),  # левый верхний
            (img_width - margin - sz, y_init),  # правый верхний
            (margin + offset_x, y_init + offset_y),  # левый нижний
            (img_width - margin - sz - offset_x, y_init + offset_y)  # правый нижний
        ]

        for ind in range(len(dinosaurs)):
            dino_id = dinosaurs[ind]['dino_id']
            dino_data = DINOS['elements'][str(dino_id)]

            x, y = positions[ind]
            with await async_open(f'images/{dino_data["image"]}') as dino_image_orig:
                with dino_image_orig.resize((sz, sz), Image.Resampling.LANCZOS) as dino_image:
                    if ind % 2 == 0:
                        with dino_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT) as dino_image_flipped:
                            img = trans_paste(dino_image_flipped, img, alpha=1, box=(x, y))
                    else:
                        img = trans_paste(dino_image, img, alpha=1, box=(x, y))

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
            rect_x0 = center_x - 5
            rect_y0 = text_y - 2
            rect_x1 = center_x + text_w + 5
            rect_y1 = text_y + text_h + 2
            rect_color = (0, 0, 0, int(255 * 0.6))  # 60% прозрачности
            radius = 10  # радиус скругления

            with Image.new('RGBA', img.size, (0, 0, 0, 0)) as overlay:
                draw_overlay = ImageDraw.Draw(overlay)
                draw_overlay.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=radius, fill=rect_color)

                # Применяем фильтр размытия к краям прямоугольника
                with Image.new('L', img.size, 0) as mask:
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=radius, fill=255)
                    with overlay.filter(ImageFilter.GaussianBlur(radius=2)) as blurred_overlay:
                        # Смешиваем размытую и обычную часть
                        with Image.composite(blurred_overlay, overlay, mask) as overlay_composite:
                            with img.convert('RGBA') as img_rgba:
                                old_img = img
                                img = Image.alpha_composite(img_rgba, overlay_composite)
                                old_img.close()

            # Рисуем текст поверх прямоугольника
            idraw = ImageDraw.Draw(img)
            idraw.text((center_x, text_y), text, font=small)

    return pil_image_to_file(img, 'png', 'maximum')