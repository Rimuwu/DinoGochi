from pprint import pprint
from typing import Optional, Union
from PIL import Image, ImageDraw
import os
from PIL import ImageFont
from PIL.ImageFont import FreeTypeFont
import string

def draw_grid_func(draw, cells, cell_size, cell_width, line_color): 
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

def draw_cell_name(draw, cells_to_draw, cell_size, 
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
            text = f"{x},{y}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        if centered:
            pos_x = x * cell_size + cell_size // 2 - text_bbox[2] // 2
            pos_y = y * cell_size + cell_size // 2 - text_bbox[3] // 2
        else:
            pos_x = x * cell_size + 4  # небольшой отступ от левого края
            pos_y = y * cell_size + 4  # небольшой отступ от верхнего края
        draw.text((pos_x, pos_y), text, fill=text_color, font=font)

def draw_rows_and_columns_names(draw, cols, rows, cell_size, font, text_color, 
                                letter_mode=False):
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
    draw_cell_name(draw, cells_to_draw, cell_size, 
                   font, text_color, 
                   letter_mode, centered=False)

    # Рисуем подписи для строк и столбцов
    draw_rows_and_columns_names(
        draw, cols, rows, cell_size, font, text_color, letter_mode
    )

    # grid_img.save(os.path.join(current_dir, output_filename))
    return grid_img  # Возвращаем изображение с сеткой и координатами

def draw_grid_on_image(
    image_filename: str,
    # output_filename: str,
    cell_size: int = 100,
    cell_width: int = 4,
    line_color: tuple = (0, 0, 0, 100),
    cells: Optional[list] = None
    ):
    """
    Накладывает сетку на изображение.
    Если cells не передан или пуст, рисует полную сетку.
    Если cells передан, рисует сетку только в указанных клетках (список [x, y]).
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
    else:
        draw_grid_func(draw, cells, cell_size, cell_width, line_color)

    result = Image.alpha_composite(img, grid_layer)
    # result.save(os.path.join(current_dir, output_filename))
    return result

def draw_colored_cells_on_image(
    image_filename: str,
    # output_filename: str,
    cells: list,
    cell_size: int = 100,
    margin: int = 2  # отступ от краёв клетки, чтобы не касаться обводки
    ):
    """
    Накладывает закрашенные квадраты на изображение на основе данных в cells.
    cells: список словарей вида {"cell": [x, y], "color": (R, G, B, A), "text": str (опционально)}
    margin: отступ пикселей от краёв клетки (по умолчанию 6)
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, image_filename)
    img = Image.open(image_path).convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for cell_info in cells:
        x, y = cell_info["cell"]
        color = cell_info["color"]
        left = x * cell_size + margin
        top = y * cell_size + margin
        right = (x + 1) * cell_size - margin
        bottom = (y + 1) * cell_size - margin
        draw.rectangle([left+1, top+1, right, bottom], fill=color)

        # Если есть ключ icon, накладываем иконку из папки icons
        if "icon" in cell_info:
            icon_name = cell_info["icon"]
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", f"{icon_name}.png")
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path).convert("RGBA")
                # Масштабируем иконку под размер клетки с учетом margin
                icon_size = ((right - left) // 2, (bottom - top) // 2)
                icon_img = icon_img.resize(icon_size, Image.LANCZOS)
                icon_left = left + ((right - left) - icon_size[0]) // 2
                icon_top = top + ((bottom - top) - icon_size[1]) // 2
                overlay.paste(icon_img, (icon_left, icon_top), icon_img)

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
    font_size: int = 20
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
    draw_cell_name(draw, cells, cell_size, font, 
                   color_cell_names, True, centered=False)

    cols = width // cell_size
    rows = height // cell_size

    # Рисуем подписи для строк и столбцов
    draw_rows_and_columns_names(draw, cols, rows, cell_size, 
                                font, color_table_names, True)

    return img

if __name__ == "__main__":
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    grid_lst = get_colored_cells_from_image(
        image_filename="null_map.png",
        cell_size=100,
        # color_threshold=10
    )

    result_img = create_grid_with_labels(
        image_filename="Остров 1.png",
        # output_filename="sector_map.png",
        cell_size=100,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        text_color=(0, 0, 0, 255),
        cell_list=grid_lst,
        letter_mode=True  # Используем буквы для координат
    )
    
    result_img.save(os.path.join(current_dir, 
                                 "sector_map.png"))

    result_img = draw_grid_on_image(
        image_filename="Остров 1.png",
        # output_filename="sector_map_with_grid.png",
        cell_size=100,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        cells=grid_lst
    )

    result_img.save(os.path.join(current_dir, 
                                 "sector_map_with_grid.png"))

    result_img = draw_colored_cells_on_image(
        image_filename="sector_map_with_grid.png",
        # output_filename="sector_map_colored_cells.png",
        cells=[
            {"cell": [3, 2], "color": (255, 0, 0, 100),
             "icon": "flag"},
            {"cell": [2, 4], "color": (255, 0, 0, 100)},
            {"cell": [3, 4], "color": (255, 0, 0, 100),
             "icon": "flag"},
            {"cell": [4, 4], "color": (255, 0, 0, 100),
             "icon": "battle"},
            {"cell": [3, 3], "color": (255, 0, 0, 100)},
            {"cell": [4, 3], "color": (255, 0, 0, 100)},
            {"cell": [4, 2], "color": (255, 0, 0, 100)},
            # Добавьте другие клетки по необходимости
        ],
        cell_size=100
    )
    # Используем более жирный шрифт, если доступен
    try:
        bold_font = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        bold_font = ImageFont.truetype("arial.ttf", 24)

    result_img = draw_sector_names_on_image(
        result_img,
        grid_lst,
        cell_size=100,
        font=bold_font,
        color_cell_names='white',
        color_table_names='white',
        font_size=24
    )
    result_img.save(os.path.join(current_dir, "sector_map_colored_cells.png"))