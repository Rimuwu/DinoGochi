
import json
from typing import Optional, Union
from PIL import Image, ImageDraw
import os
from PIL import ImageFont
from PIL.ImageFont import FreeTypeFont
import string
import math



with open('../../bot/json/dino_data.json', encoding='utf-8') as f: 
    DINOS = json.load(f)['elements'] # type: dict

def draw_grid_func(draw, cells, cell_size, 
                   cell_width, line_color): 
    for cell in cells:
        x, y = cell
        left = x * cell_size
        top = y * cell_size
        right = left + cell_size
        bottom = top + cell_size
        # Рисуем границы клетки
        draw.line([(left, top), (right, top)], fill=line_color, width=cell_width) # верх
        draw.line([(left, bottom), (right, bottom)], fill=line_color, width=cell_width)  # низ
        draw.line([(left, top), (left, bottom)], fill=line_color, width=cell_width)  # левый
        draw.line([(right, top), (right, bottom)], fill=line_color, width=cell_width)  # правый

def draw_cell_name(image, draw, cells_to_draw,
                   cell_size, 
                   font, text_color, 
                   letter_mode=False,
                   centered=False):
    for x, y in cells_to_draw:
        if letter_mode:
            # Ограничим буквы латинским алфавитом (A-Z)
            letter = string.ascii_uppercase[x % 26]
            number = str(y + 1)
            text = f"{letter}{number}"
        else:
            text = f"{x}:{y}"

        text_bbox = draw.textbbox((0, 0), text, font=font)
        if centered:
            pos_x = x * cell_size + cell_size // 2 - text_bbox[2] // 2
            pos_y = y * cell_size + cell_size // 2 - text_bbox[3] // 2
        else:
            pos_x = x * cell_size + 4  # небольшой отступ от левого края
            pos_y = y * cell_size + 4  # небольшой отступ от верхнего края

        # Определяем, больше ли половины пикселей под текстом белые для адаптации цвета текста
        text_w, text_h = text_bbox[2], text_bbox[3]
        # Ограничиваем область, чтобы не выйти за границы изображения
        left = max(0, min(pos_x, image.width - text_w))
        top = max(0, min(pos_y, image.height - text_h))
        right = min(left + text_w, image.width)
        bottom = min(top + text_h, image.height)
        # Получаем пиксели под текстом
        region = image.crop((left, top, right, bottom))
        pixels = list(region.getdata())
        if pixels:
            white_count = sum(1 for px in pixels if px[0] > 240 and px[1] > 240 and px[2] > 240)
            white_ratio = white_count / len(pixels)
        else:
            white_ratio = 0

        if text_color == 'white' or text_color == (255, 255, 255, 255):
            if white_ratio > 0.3:
                draw.text((pos_x, pos_y), text, fill='black', font=font)
            else:
                draw.text((pos_x, pos_y), text, fill=text_color, font=font)
        else:
            draw.text((pos_x, pos_y), text, fill=text_color, font=font)

def draw_rows_and_columns_names(
    image, draw, cols, rows, cell_size, font, text_color,
    letter_mode=False
):
    # Рисуем подписи для первой строки (x-координаты)
    for x in range(cols):
        if letter_mode:
            label = string.ascii_uppercase[x % 26]
        else:
            label = str(x)
        label_bbox = draw.textbbox((0, 0), label, font=font)
        label_x = x * cell_size + cell_size // 2 - label_bbox[2] // 2
        label_y = 10  # небольшой отступ сверху
        draw.text((label_x, label_y), label, fill=text_color, font=font)

    # Рисуем подписи для первого столбца (y-координаты)
    for y in range(rows):
        if letter_mode:
            label = str(y + 1)
        else:
            label = str(y)
        label_bbox = draw.textbbox((0, 0), label, font=font)
        label_x = 10  # небольшой отступ слева
        label_y = y * cell_size + cell_size // 2 - label_bbox[3] // 2
        draw.text((label_x, label_y), label, fill=text_color, font=font)

def create_grid_with_labels(
    image_filename: str,
    # output_filename: str,
    cell_size: int = 100,
    cell_width: int = 4,
    line_color: tuple = (0, 0, 0, 100),
    text_color: tuple = (0, 0, 0, 255),
    font=None,
    cell_list: Optional[list] = None,
    letter_mode: bool = False  # Новый параметр для режима букв
    ):
    """
    Создаёт пустое изображение с сеткой и координатами клеток в центре каждой клетки.
    Если cell_list не передан или пуст, рисует все клетки.
    Если cell_list передан, рисует только клетки из списка (список [x, y]).
    letter_mode: если True, первая координата — буква (A, B, ...), вторая — число (без запятой).
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, image_filename)
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    # Создаём пустое изображение
    blank_img = Image.new("RGBA", (width, height), (255, 255, 255, 255))

    # Рисуем сетку
    grid_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_grid = ImageDraw.Draw(grid_layer)

    cols = width // cell_size
    rows = height // cell_size

    if not cell_list:
        # Рисуем полную сетку
        for x in range(0, width, cell_size):
            draw_grid.line([(x, 0), (x, height)], fill=line_color, width=cell_width)
        for y in range(0, height, cell_size):
            draw_grid.line([(0, y), (width, y)], fill=line_color, width=cell_width)
    else:
        draw_grid_func(draw_grid, cell_list, cell_size, cell_width, line_color)

    # Накладываем сетку на изображение
    grid_img = Image.alpha_composite(blank_img, grid_layer)
    # result.save(os.path.join(current_dir, output_filename))

    # Открываем изображение с сеткой
    # grid_img = Image.open(os.path.join(current_dir, output_filename)).convert("RGBA")
    draw = ImageDraw.Draw(grid_img)

    # Используем стандартный шрифт PIL, если не передан
    if font is None:
        try:
            font = ImageFont.truetype("arial.ttf", cell_size // 4)
        except:
            font = ImageFont.load_default()

    # Рисуем координаты в центре каждой клетки
    if not cell_list:
        cells_to_draw = [(x, y) for y in range(rows) for x in range(cols)]
    else:
        cells_to_draw = cell_list

    # Рисуем имена клеток
    draw_cell_name(grid_img, draw, cells_to_draw,
                   cell_size, font, text_color,
                   letter_mode, centered=True)

    # Рисуем подписи для строк и столбцов
    draw_rows_and_columns_names(grid_img, draw,
        cols, rows, cell_size, font, text_color, letter_mode
    )

    # grid_img.save(os.path.join(current_dir, output_filename))
    return grid_img  # Возвращаем изображение с сеткой и координатами

def draw_grid_on_image(
    image_filename: str,
    # output_filename: str,
    cell_size: int = 100,
    cell_width: int = 4,
    line_color: tuple = (0, 0, 0, 100),
    cells: Optional[list] = None,
    fill_alpha: Optional[int] = None  # Новый параметр: прозрачность заливки (0-255)
    ):
    """
    Накладывает сетку на изображение.
    Если cells не передан или пуст, рисует полную сетку.
    Если cells передан, рисует сетку только в указанных клетках (список [x, y]).
    fill_alpha: если задано (0-255), заливает внутренность клетки полупрозрачным чёрным.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, image_filename)
    img = Image.open(image_path).convert("RGBA")

    width, height = img.size

    grid_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(grid_layer)

    if not cells:
        # Полная сетка
        for x in range(0, width, cell_size):
            draw.line([(x, 0), (x, height)], fill=line_color, width=cell_width)
        for y in range(0, height, cell_size):
            draw.line([(0, y), (width, y)], fill=line_color, width=cell_width)
        if fill_alpha is not None:
            # Затемняем все клетки
            for y in range(height // cell_size):
                for x in range(width // cell_size):
                    left = x * cell_size
                    top = y * cell_size
                    right = left + cell_size
                    bottom = top + cell_size
                    draw.rectangle([left, top, right, bottom], fill=(0, 0, 0, fill_alpha))
    else:
        if fill_alpha is not None:
            for x, y in cells:
                left = x * cell_size
                top = y * cell_size
                right = left + cell_size
                bottom = top + cell_size
                draw.rectangle([left, top, right, bottom], fill=(0, 0, 0, fill_alpha))
        draw_grid_func(draw, cells, cell_size, cell_width, line_color)

    result = Image.alpha_composite(img, grid_layer)
    # result.save(os.path.join(current_dir, output_filename))
    return result

def draw_colored_cells_on_image(
    img: Image.Image,
    # output_filename: str,
    cells: list,
    cell_size: int = 100,
    margin: int = 2  # отступ от краёв клетки, чтобы не касаться обводки
    ):
    """
    Накладывает закрашенные квадраты на изображение на основе данных в cells.
    img: PIL.Image.Image — изображение, на которое накладываются клетки.
    cells: список словарей вида {"cell": [x, y], "color": (R, G, B, A), "text": str (опционально)}
    margin: отступ пикселей от краёв клетки (по умолчанию 6)
    """

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Группируем все элементы по клеткам
    cell_map = defaultdict(list)
    for cell_info in cells:
        cell_tuple = tuple(cell_info["cell"])
        cell_map[cell_tuple].append(cell_info)

    for cell, cell_items in cell_map.items():
        x, y = cell
        left = x * cell_size + margin
        top = y * cell_size + margin
        right = (x + 1) * cell_size - margin
        bottom = (y + 1) * cell_size - margin

        # Рисуем цвет фона, если есть хотя бы один с color
        for cell_info in cell_items:
            if 'color' in cell_info:
                color = cell_info["color"]
                draw.rectangle([left+1, top+1, right, bottom], fill=color)
                break  # только один раз

        # Рисуем текст, если есть
        for cell_info in cell_items:
            if 'text' in cell_info:
                text = cell_info["text"]
                try:
                    font = ImageFont.truetype("arialbd.ttf", 24)
                except Exception:
                    font = ImageFont.truetype("arial.ttf", 24)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_x = left + (right - left - text_bbox[2]) // 2
                text_y = top + (bottom - top - text_bbox[3]) // 2
                draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

        # Собираем все иконки для этой клетки
        icons = []
        for cell_info in cell_items:
            if "icon" in cell_info:
                icons.append(cell_info["icon"])

        # Рисуем иконки, если есть
        if icons:
            icon_paths = []
            for icon_name in icons:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", f"{icon_name}.png")
                if os.path.exists(icon_path):
                    icon_paths.append(icon_path)
            n = len(icon_paths)

            if n == 1:
                icon_img = Image.open(icon_paths[0]).convert("RGBA")
                icon_size = ((right - left) // 2, (bottom - top) // 2)
                icon_img = icon_img.resize(icon_size, Image.LANCZOS)
                icon_left = left + ((right - left) - icon_size[0]) // 2
                icon_top = top + ((bottom - top) - icon_size[1]) // 2
                overlay.paste(icon_img, (icon_left, icon_top), icon_img)

            elif n == 2:
                # Две иконки: уменьшить и поставить рядом по центру
                icon_size = ((right - left) // 2 - 10, (bottom - top) // 2 - 10)

                for i, icon_path in enumerate(icon_paths):
                    icon_img = Image.open(icon_path).convert("RGBA")
                    icon_img = icon_img.resize(icon_size, Image.LANCZOS)
                    # Слева и справа
                    icon_left = left + (right - left) // 4 - icon_size[0] // 2 if i == 0 else left + 3 * (right - left) // 4 - icon_size[0] // 2
                    icon_top = top + ((bottom - top) - icon_size[1]) // 2
                    overlay.paste(icon_img, (icon_left, icon_top), icon_img)

            elif n == 3:
                # Три иконки: перевёрнутый треугольник
                icon_size = ((right - left) // 3 - 2, (bottom - top) // 3 - 2)
                positions = [
                    (left + 3 * (right - left) // 4 - icon_size[0] // 2, top + 3 * (bottom - top) // 4 - icon_size[1] // 2),
                    (left + 3 * (right - left) // 4 - icon_size[0] // 2, top + (bottom - top) // 4 - icon_size[1] // 2),
                    (left + (right - left) // 4 - icon_size[0] // 2, top + 3 * (bottom - top) // 4 - icon_size[1] // 2)
                ]

                for i, icon_path in enumerate(icon_paths):
                    icon_img = Image.open(icon_path).convert("RGBA")
                    icon_img = icon_img.resize(icon_size, Image.LANCZOS)
                    overlay.paste(icon_img, positions[i], icon_img)

        # Если есть ключ dino, накладываем картинку динозавра из DINOS
        for cell_info in cell_items:
            if "dino" in cell_info:
                dino_name = cell_info["dino"]
                dino_path = DINOS.get(dino_name, {}).get('image')
                if dino_path and os.path.exists(r'../../images/' + dino_path):
                    dino_img = Image.open(r'../../images/' + dino_path).convert("RGBA")
                    dino_scale = cell_info.get("dino_scale", 1.1)
                    dino_w = int((right - left) * dino_scale)
                    dino_h = int((bottom - top) * dino_scale)
                    dino_size = (dino_w, dino_h)
                    dino_img = dino_img.resize(dino_size, Image.LANCZOS)
                    dino_left = left + ((right - left) - dino_size[0]) // 2
                    vertical_shift = int(((dino_scale - 1) * (bottom - top)) * 0.5)
                    dino_top = top + ((bottom - top) - dino_size[1]) // 2 - vertical_shift
                    overlay.paste(dino_img, (dino_left, dino_top), dino_img)
                else:
                    print(f"Warning: Dino image for '{dino_name}' not found in DINOS data or file path is incorrect.")

        # Если есть стены
        for cell_info in cell_items:
            if 'walls' in cell_info:
                x, y = cell_info["cell"]
                left0 = x * cell_size
                top0 = y * cell_size
                right0 = left0 + cell_size
                bottom0 = top0 + cell_size

                walls = cell_info['walls']
                wall_color = cell_info.get('wall_color', (255, 255, 255, 255))
                wall_width = cell_info.get('wall_width', 3)
                if len(walls) == 4:
                    margin0 = cell_info.get('wall_margin', 0)
                    if walls[0]:
                        draw.line(
                            [(left0 + margin0, top0 + margin0), (left0 + margin0, bottom0 - margin0)],
                            fill=wall_color, width=wall_width
                        )
                    if walls[1]:
                        draw.line(
                            [(left0 + margin0, top0 + margin0), (right0 - margin0, top0 + margin0)],
                            fill=wall_color, width=wall_width
                        )
                    if walls[2]:
                        draw.line(
                            [(right0 - margin0, top0 + margin0), (right0 - margin0, bottom0 - margin0)],
                            fill=wall_color, width=wall_width
                        )
                    if walls[3]:
                        draw.line(
                            [(left0 + margin0, bottom0 - margin0), (right0 - margin0, bottom0 - margin0)],
                            fill=wall_color, width=wall_width
                        )

    result = Image.alpha_composite(img, overlay)
    # result.save(os.path.join(current_dir, output_filename))
    return result

def get_colored_cells_from_image(
    image_filename: str,
    cell_size: int = 100,
    # color_threshold: int = 10,
    fill_percent_threshold: float = 0.4
    ) -> list:
    """
    Возвращает список [x, y] координат клеток, в которых есть непрозрачные пиксели.
    Учитываются любые непрозрачные пиксели, независимо от цвета.
    fill_percent_threshold — минимальная доля непрозрачных пикселей в клетке (от 0 до 1), чтобы считать клетку цветной.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, image_filename)
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    cols = width // cell_size
    rows = height // cell_size
    colored_cells = []

    for y in range(rows):
        for x in range(cols):
            left = x * cell_size
            top = y * cell_size
            right = min(left + cell_size, width)
            bottom = min(top + cell_size, height)
            cell = img.crop((left, top, right, bottom))
            pixels = list(cell.getdata())
            if pixels:
                non_transparent_count = sum(1 for px in pixels if px[3] > 0)
                total_pixel_count = len(pixels)
                if total_pixel_count > 0 and (non_transparent_count / total_pixel_count) >= fill_percent_threshold:
                    colored_cells.append([x, y])

    return colored_cells


def draw_sector_names_on_image(
    img: Image.Image,
    cells: list,
    cell_size: int = 100,
    font: Optional[FreeTypeFont] = None,
    color_cell_names: Union[tuple, str] = (0, 0, 0, 255),
    color_table_names: Union[tuple, str] = (0, 0, 0, 255),
    font_size: int = 20,
    letter_mode: bool = True
    ):
    """
    Рисует имена секторов (буквенно-числовые) на указанных клетках и подписи строк/столбцов.
    """

    width, height = img.size

    draw = ImageDraw.Draw(img)

    if font is None:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            # Fallback to a default truetype font if arial.ttf is not available
            font = ImageFont.truetype(ImageFont._default_font, font_size)

    # Рисуем имена клеток
    draw_cell_name(img, draw, cells, cell_size, font, 
                   color_cell_names, letter_mode, centered=False)

    cols = width // cell_size
    rows = height // cell_size

    # Рисуем подписи для строк и столбцов
    draw_rows_and_columns_names(img, draw, cols, rows, cell_size, 
                                font, color_table_names, letter_mode)

    return img

def draw_dotted_arc_on_cells(
    img: Image.Image,
    cells: list,
    cell_size: int = 100,
    color: Union[tuple, str] = (0, 0, 0, 255),
    width: int = 4,
    dot_length: int = 10,
    gap_length: int = 10,
    cell_points: list = None  # Новый параметр: список словарей {"cell": [x, y], "percent": float (0..1)}
    ):
    """
    Рисует сглаженную пунктирную дугу по центрам указанных ячеек.
    cells: список [x, y] координат ячеек (дуга идет по порядку).
    color: цвет дуги.
    width: толщина дуги.
    dot_length: длина штриха.
    gap_length: длина промежутка между штрихами.
    cell_points: список {"cell": [x, y], "percent": float (0..1)} — для каждой клетки рисует точку на соответствующем проценте прохода этой клетки.
    """

    draw = ImageDraw.Draw(img)

    # Получаем список центров ячеек
    centers = [
        (
            x * cell_size + cell_size // 2,
            y * cell_size + cell_size // 2
        )
        for x, y in cells
    ]

    if len(centers) < 2:
        return img  # нечего рисовать

    # Используем сглаженную кривую Catmull-Rom для плавности
    def catmull_rom_spline(P, n_points=500):
        """P - список точек, n_points - сколько точек на кривой"""
        if len(P) < 2:
            return P

        # Добавляем фиктивные точки в начало и конец для плавности
        points = [P[0]] + P + [P[-1]]
        curve = []
        for i in range(1, len(points) - 2):
            p0, p1, p2, p3 = points[i-1], points[i], points[i+1], points[i+2]
            for t in [j / n_points for j in range(n_points)]:
                t2 = t * t
                t3 = t2 * t
                x = 0.5 * (
                    (2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    (2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
                )
                curve.append((x, y))
        curve.append(P[-1])
        return curve

    if len(centers) == 2:
        arc_points = [centers[0], centers[1]]
    else:
        arc_points = catmull_rom_spline(centers, n_points=100)

    # Теперь рисуем пунктир по дуге
    # Сначала вычисляем длину всей дуги и создаём список сегментов
    segments = []
    for i in range(len(arc_points) - 1):
        p1 = arc_points[i]
        p2 = arc_points[i + 1]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        segments.append((p1, p2, seg_len))

    total_len = sum(seg[2] for seg in segments)
    if total_len == 0:
        return img

    # Для поиска позиции точки внутри клетки
    def get_cell_arc_range(cells, arc_points):
        """
        Возвращает список (start_idx, end_idx) для каждой клетки,
        где start_idx - индекс первой точки дуги внутри клетки,
        end_idx - индекс последней точки дуги внутри клетки.
        """
        cell_ranges = []
        for idx, (x, y) in enumerate(cells):
            left = x * cell_size
            top = y * cell_size
            right = (x + 1) * cell_size
            bottom = (y + 1) * cell_size
            indices = [i for i, (px, py) in enumerate(arc_points)
                        if left <= px < right and top <= py < bottom]
            if indices:
                cell_ranges.append((min(indices), max(indices)))
            else:
                cell_ranges.append((None, None))
        return cell_ranges

    # Теперь идём по дуге, чередуя dot_length и gap_length
    pos_on_curve = 0
    seg_idx = 0
    seg_pos = 0

    while pos_on_curve < total_len:
        # Рисуем штрих
        draw_len = min(dot_length, total_len - pos_on_curve)
        start = None
        end = None
        draw_left = draw_len
        curr_pos = pos_on_curve

        # Найти начальную точку
        while seg_idx < len(segments):
            p1, p2, seg_len = segments[seg_idx]
            if seg_pos + draw_left <= seg_len:
                # В пределах текущего сегмента
                ratio_start = seg_pos / seg_len if seg_len != 0 else 0
                ratio_end = (seg_pos + draw_left) / seg_len if seg_len != 0 else 0
                start = (
                    p1[0] + (p2[0] - p1[0]) * ratio_start,
                    p1[1] + (p2[1] - p1[1]) * ratio_start
                )
                end = (
                    p1[0] + (p2[0] - p1[0]) * ratio_end,
                    p1[1] + (p2[1] - p1[1]) * ratio_end
                )
                draw.line([start, end], fill=color, width=width)
                seg_pos += draw_left
                if seg_pos >= seg_len:
                    seg_idx += 1
                    seg_pos = 0
                break
            else:
                # Заканчиваем сегмент, переходим к следующему
                if seg_len - seg_pos > 0:
                    ratio_start = seg_pos / seg_len if seg_len != 0 else 0
                    start = (
                        p1[0] + (p2[0] - p1[0]) * ratio_start,
                        p1[1] + (p2[1] - p1[1]) * ratio_start
                    )
                    end = p2
                    draw.line([start, end], fill=color, width=width)
                    draw_left -= (seg_len - seg_pos)
                seg_idx += 1
                seg_pos = 0

        pos_on_curve += draw_len

        # Пропускаем gap
        gap_left = gap_length
        while gap_left > 0 and seg_idx < len(segments):
            p1, p2, seg_len = segments[seg_idx]
            if seg_pos + gap_left <= seg_len:
                seg_pos += gap_left
                gap_left = 0
                if seg_pos >= seg_len:
                    seg_idx += 1
                    seg_pos = 0
            else:
                gap_left -= (seg_len - seg_pos)
                seg_idx += 1
                seg_pos = 0
        pos_on_curve += gap_length

    # --- Добавляем точки с процентом прохода клетки ---
    if cell_points:
        # Получаем диапазоны индексов дуги для каждой клетки
        cell_ranges = get_cell_arc_range(cells, arc_points)
        for cp in cell_points:
            cell = cp.get("cell")
            percent = cp.get("percent", 0.5)
            if not cell or percent is None:
                continue
            try:
                idx = cells.index(cell)
            except ValueError:
                continue
            start_idx, end_idx = cell_ranges[idx]
            if start_idx is None or end_idx is None or end_idx <= start_idx:
                continue
            arc_idx = int(start_idx + (end_idx - start_idx) * percent)
            arc_idx = max(start_idx, min(end_idx, arc_idx))
            px, py = arc_points[arc_idx]
            # Рисуем точку (круг)
            r = width * 2  # радиус точки (можно настроить)
            r = max(6, width * 2)
            draw.ellipse(
                [px - r, py - r, px + r, py + r],
                fill=color if isinstance(color, tuple) else (255, 0, 0, 255)
            )

    return img

def draw_weight_map_on_card(
    img: Image.Image,
    weight_map: dict,
    cell_size: int = 100,
    font: Optional[FreeTypeFont] = None,
    font_size: int = 18,
    color: Union[tuple, str] = (0, 0, 0, 255)
    ):
    """
    weight_map: {'x.y': [left, top, right, bottom]}
    Рисует веса на каждой ячейке: left (слева), top (сверху), right (справа), bottom (снизу).
    Если значение -1, 0, 1, 2, 3 — рисует линию по стороне соответствующего цвета:
    -1: красный, 0: зелёный, 1: синий, 2: оранжевый, 3: фиолетовый.
    """
    draw = ImageDraw.Draw(img)
    if font is None:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    # Цвета для линий
    color_map = {
        -1: "#CF2F07",      # красный
        0: '#00C800',      # зелёный
        1: "#FFFFFF",      # синий
        2: '#FF8C00',    # оранжевый
        3: "#560768",    # фиолетовый
    }

    # Смещения для размещения текста внутри клетки
    text_offsets = {
        0: (cell_size * 0.18, cell_size // 2),  # left
        1: (cell_size // 2, cell_size * 0.18),  # top
        2: (cell_size * 0.82, cell_size // 2),  # right
        3: (cell_size // 2, cell_size * 0.82),  # bottom
    }
    
    margin_line = 0.1

    for key, weights in weight_map.items():
        # Преобразуем ключ 'x.y' в x, y
        try:
            x_str, y_str = key.split('.')
            x, y = int(x_str), int(y_str)
        except Exception:
            continue

        left = x * cell_size
        top = y * cell_size
        right = left + cell_size
        bottom = top + cell_size

        # Для каждой стороны
        for idx, w in enumerate(weights):
            if w is None:
                continue
            # Координаты для текста внутри клетки
            tx, ty = text_offsets.get(idx, (cell_size // 2, cell_size // 2))
            tx = int(left + tx)
            ty = int(top + ty)
            if w in color_map:
                # Рисуем линию внутри клетки, не на границе
                margin = int(cell_size * margin_line)
                if idx == 0:  # left
                    draw.line(
                        [(left + margin, top + margin), (left + margin, bottom - margin)],
                        fill=color_map[w], width=4
                    )
                elif idx == 1:  # top
                    draw.line(
                        [(left + margin, top + margin), (right - margin, top + margin)],
                        fill=color_map[w], width=4
                    )
                elif idx == 2:  # right
                    draw.line(
                        [(right - margin, top + margin), (right - margin, bottom - margin)],
                        fill=color_map[w], width=4
                    )
                elif idx == 3:  # bottom
                    draw.line(
                        [(left + margin, bottom - margin), (right - margin, bottom - margin)],
                        fill=color_map[w], width=4
                    )
            else:
                text = str(w)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_x = tx - bbox[2] // 2
                text_y = ty - bbox[3] // 2
                draw.text(
                    (text_x, text_y),
                    text, fill=color, font=font
                )
    return img

from navigate import find_fastest_path, weight_map
from collections import defaultdict

def main():
    cell_size = 100
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    grid_lst = get_colored_cells_from_image(
        image_filename="null_map.png",
        cell_size=cell_size,
        fill_percent_threshold=0.43
        # color_threshold=10
    )

    result_img = create_grid_with_labels(
        image_filename="Остров 1.png",
        # output_filename="sector_map.png",
        cell_size=cell_size,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        text_color=(0, 0, 0, 255),
        cell_list=grid_lst,
        letter_mode=False  # Используем буквы для координат
    )
    
    result_img = draw_weight_map_on_card(
        result_img,
        weight_map=weight_map,
        cell_size=cell_size,
        font=None,  # Используем стандартный шрифт PIL
        font_size=18,
        color=(0, 0, 0, 255)  # Чёрный цвет для весов
    )
    
    result_img.save(os.path.join(current_dir, 
                                 "sector_map.png"))

    result_img = draw_grid_on_image(
        image_filename="Остров 1.png",
        # output_filename="sector_map_with_grid.png",
        cell_size=cell_size,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        cells=grid_lst,
        fill_alpha=100
    )
    
    draw_cell_name(
        result_img, 
        draw=ImageDraw.Draw(result_img), 
        cells_to_draw=grid_lst,
        cell_size=cell_size,
        font=ImageFont.truetype("arial.ttf", 36),  # Используем стандартный шрифт PIL
        text_color='white',
        letter_mode=False,  # Используем буквы для координат
        centered=True
    )
    
    result_img = draw_weight_map_on_card(
        result_img,
        weight_map=weight_map,
        cell_size=cell_size,
        font=None,
        font_size=18,
        color=(0, 0, 0, 255)  # Чёрный цвет для весов
    )

    result_img.save(os.path.join(current_dir, 
                                 "sector_map_with_grid.png"))


    result1_img = draw_grid_on_image(
        image_filename="Остров 1.png",
        # output_filename="sector_map_with_grid.png",
        cell_size=cell_size,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        cells=grid_lst,
        fill_alpha=0
    )

    result1_img = draw_colored_cells_on_image(
        result1_img,
        # output_filename="sector_map_colored_cells.png",
        cells=[
            {"cell": [3, 2], "color": (255, 0, 0, 100),
             "icon": "flag"},
            {"cell": [2, 4], "color": (255, 0, 0, 100)},
            {"cell": [2, 4], "text": '5', "icon": 'circle'},
            {"cell": [6, 6], 'dino': '16948'},
            {"cell": [7, 6], 'dino': '16948'},
            # {"cell": [3, 4], "color": (255, 0, 0, 100),
            #  "icon": "flag"},
            # {"cell": [4, 4], "color": (255, 0, 0, 100),
            #  "icon": "battle"},
            # {"cell": [3, 3], "color": (255, 0, 0, 100)},
            # {"cell": [4, 3], "color": (255, 0, 0, 100)},
            # {"cell": [4, 2], "color": (255, 0, 0, 100)},
            # Добавьте другие клетки по необходимости
        ],
        cell_size=cell_size
    )
    
    # Используем более жирный шрифт, если доступен
    try:
        bold_font = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        bold_font = ImageFont.truetype("arial.ttf", 24)

    result1_img = draw_sector_names_on_image(
        result1_img,
        grid_lst,
        cell_size=cell_size,
        font=bold_font,
        color_cell_names='white',
        color_table_names='white',
        font_size=24,
        letter_mode=True  # Используем числа для координат
    )
    
    # result_img = draw_weight_map_on_card(
    #     result_img,
    #     weight_map=weight_map,
    #     cell_size=100,
    #     font=None,  # Используем стандартный шрифт PIL
    #     font_size=32,
    #     color='red'  # Чёрный цвет для весов
    # )
    
    lst = find_fastest_path(
        start=[10, 8],
        goal=[12, 6]
    )

    if lst: 
        result1_img = draw_dotted_arc_on_cells(
            result1_img,
            cells=lst,
            width=5,
            dot_length=20,
            cell_size=cell_size,
            gap_length=10,
            color='red',  # Цвет дуги
            cell_points=[
                {"cell": [9, 7], "percent": 0.0},  # Точка в середине первой клетки
                {"cell": [12, 6], "percent": 0.5}   # Точка в середине последней клетки
            ]
        )
    
    result1_img.save(os.path.join(current_dir, "sector_map_colored_cells.png"))

if __name__ == "__main__":
    main()
