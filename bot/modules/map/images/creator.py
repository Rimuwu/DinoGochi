
from collections import defaultdict
from typing import Optional, Union
from PIL import Image, ImageDraw
import os
from PIL import ImageFont
import string

font = ImageFont.truetype('fonts/Aqum.otf', size=24)

def draw_grid_func(draw, cells, cell_size, 
                   cell_width, line_color): 
    
    """
        Рисует сетку на изображении по заданным ячейкам.
        Параметры:
            draw: Объект для рисования (например, ImageDraw).
            cells: Список координат ячеек в виде кортежей (x, y).
            cell_size: Размер стороны ячейки в пикселях.
            cell_width: Толщина линии сетки.
            line_color: Цвет линий сетки.
    """

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
    img = Image.open(image_filename).convert("RGBA")

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

def draw_cell_name(image, draw, cells_to_draw,
                   cell_size, 
                   text_color, 
                   letter_mode=False,
                   centered=False
                ):
    """
        Рисует подписи ячеек на изображении.
        Аргументы:
            image: Объект изображения PIL, на котором рисовать.
            draw: Объект ImageDraw для рисования текста.
            cells_to_draw: Список координат ячеек (x, y), для которых требуется подпись.
            cell_size: Размер одной ячейки в пикселях.
            font: Объект шрифта PIL для текста.
            text_color: Цвет текста (строка или кортеж RGB(A)).
            letter_mode (bool): Если True, подписи в формате "A1", иначе "x:y".
            centered (bool): Если True, текст центрируется в ячейке.
        Особенности:
            - Автоматически выбирает цвет текста (белый/чёрный) для лучшей читаемости на светлом фоне.
            - Поддерживает подписи в виде букв и цифр (A1, B2 и т.д.) или координат (x:y).
    """

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
        draw, cols, rows, 
        cell_size, text_color,
        letter_mode=False
    ):
    """
        Рисует подписи для строк и столбцов сетки на изображении.
        Аргументы:
            image: Объект изображения PIL.
            draw: Объект ImageDraw для рисования.
            cols (int): Количество столбцов.
            rows (int): Количество строк.
            cell_size (int): Размер одной ячейки сетки в пикселях.
            font: Объект шрифта PIL для текста.
            text_color: Цвет текста.
            letter_mode (bool, по умолчанию False): Если True, для столбцов используются буквы, для строк — числа с 1.
    """
    
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

    # Открываем изображение с сеткой
    draw = ImageDraw.Draw(grid_img)

    # Рисуем координаты в центре каждой клетки
    if not cell_list:
        cells_to_draw = [(x, y) for y in range(rows) for x in range(cols)]
    else:
        cells_to_draw = cell_list

    # Рисуем имена клеток
    draw_cell_name(grid_img, draw, cells_to_draw,
                   cell_size, text_color,
                   letter_mode, centered=True)

    # Рисуем подписи для строк и столбцов
    draw_rows_and_columns_names(draw,
        cols, rows, cell_size, text_color, letter_mode
    )

    return grid_img  # Возвращаем изображение с сеткой и координатами


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
                icon_path = f"images/world/icons/{icon_name}.png"

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


def draw_sector_names_on_image(
    img: Image.Image,
    cells: list,
    cell_size: int = 100,
    color_cell_names: Union[tuple, str] = (0, 0, 0, 255),
    color_table_names: Union[tuple, str] = (0, 0, 0, 255),
    letter_mode: bool = True
    ):
    """
    Рисует имена секторов (буквенно-числовые) на указанных клетках и подписи строк/столбцов.
    """

    width, height = img.size

    draw = ImageDraw.Draw(img)

    # Рисуем имена клеток
    draw_cell_name(img, draw, cells, cell_size,
                   color_cell_names, letter_mode, centered=False)

    cols = width // cell_size
    rows = height // cell_size

    # Рисуем подписи для строк и столбцов
    draw_rows_and_columns_names(draw, cols, rows, cell_size, 
                                color_table_names, letter_mode)

    return img