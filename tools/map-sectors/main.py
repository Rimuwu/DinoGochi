from typing import Optional
from PIL import Image, ImageDraw
import os
from PIL import ImageFont

def create_grid_with_labels(
    image_filename: str,
    output_filename: str,
    cell_size: int = 100,
    cell_width: int = 4,
    line_color: tuple = (0, 0, 0, 100),
    text_color: tuple = (0, 0, 0, 255),
    font=None,
    cell_list: Optional[list] = None
):
    """
    Создаёт пустое изображение с сеткой и координатами клеток в центре каждой клетки.
    Если cell_list не передан или пуст, рисует все клетки.
    Если cell_list передан, рисует только клетки из списка (список [x, y]).
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
        # Рисуем только выбранные клетки
        for cell in cell_list:
            x, y = cell
            left = x * cell_size
            top = y * cell_size
            right = left + cell_size
            bottom = top + cell_size
            # Границы клетки
            draw_grid.line([(left, top), (right, top)], fill=line_color, width=cell_width)      # верх
            draw_grid.line([(left, bottom), (right, bottom)], fill=line_color, width=cell_width)  # низ
            draw_grid.line([(left, top), (left, bottom)], fill=line_color, width=cell_width)    # левый
            draw_grid.line([(right, top), (right, bottom)], fill=line_color, width=cell_width)  # правый

    # Накладываем сетку на изображение
    result = Image.alpha_composite(blank_img, grid_layer)
    result.save(os.path.join(current_dir, output_filename))

    # Открываем изображение с сеткой
    grid_img = Image.open(os.path.join(current_dir, output_filename)).convert("RGBA")
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

    for x, y in cells_to_draw:
        text = f"{x},{y}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        center_x = x * cell_size + cell_size // 2 - text_bbox[2] // 2
        center_y = y * cell_size + cell_size // 2 - text_bbox[3] // 2
        draw.text((center_x, center_y), text, fill=text_color, font=font)

    grid_img.save(os.path.join(current_dir, output_filename))

def draw_grid_on_image(
    image_filename: str,
    output_filename: str,
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
        # Только выбранные клетки
        for cell in cells:
            x, y = cell
            left = x * cell_size
            top = y * cell_size
            right = left + cell_size
            bottom = top + cell_size
            # Рисуем границы клетки
            draw.line([(left, top), (right, top)], fill=line_color, width=cell_width)      # верх
            draw.line([(left, bottom), (right, bottom)], fill=line_color, width=cell_width)  # низ
            draw.line([(left, top), (left, bottom)], fill=line_color, width=cell_width)    # левый
            draw.line([(right, top), (right, bottom)], fill=line_color, width=cell_width)  # правый

    result = Image.alpha_composite(img, grid_layer)
    result.save(os.path.join(current_dir, output_filename))

def draw_colored_cells_on_image(
    image_filename: str,
    output_filename: str,
    cells: list,
    cell_size: int = 100
    ):
    """
    Накладывает закрашенные квадраты на изображение на основе данных в cells.
    cells: список словарей вида {"cell": [x, y], "color": (R, G, B, A), "text": str (опционально)}
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, image_filename)
    img = Image.open(image_path).convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Используем стандартный шрифт PIL
    try:
        font = ImageFont.truetype("arial.ttf", cell_size // 4)
    except:
        font = ImageFont.load_default()

    def wrap_text(text, font, max_width):
        """Разбивает текст на строки, чтобы он помещался в max_width."""
        lines = []
        for paragraph in text.split('\n'):
            line = ""
            for word in paragraph.split():
                test_line = f"{line} {word}".strip()
                left, top, right, bottom = draw.textbbox((0, 0), test_line, font=font)
                w = right - left
                if w <= max_width:
                    line = test_line
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
        return lines

    for cell_info in cells:
        x, y = cell_info["cell"]
        color = cell_info["color"]
        left = x * cell_size
        top = y * cell_size
        right = left + cell_size
        bottom = top + cell_size
        draw.rectangle([left, top, right, bottom], fill=color)

        # Если есть текст, рисуем его по центру клетки, с переносом строк
        if "text" in cell_info and cell_info["text"]:
            text = str(cell_info["text"])
            max_text_width = cell_size - 8  # небольшой отступ
            lines = wrap_text(text, font, max_text_width)
            total_text_height = sum([draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines])
            y_offset = top + (cell_size - total_text_height) // 2
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                x_offset = left + (cell_size - line_width) // 2
                draw.text((x_offset, y_offset), line, fill=(255, 255, 255, 255), font=font)
                y_offset += bbox[3] - bbox[1]

    result = Image.alpha_composite(img, overlay)
    result.save(os.path.join(current_dir, output_filename))

def get_colored_cells_from_image(
    image_filename: str,
    cell_size: int = 100,
    color_threshold: int = 10,
    fill_percent_threshold: float = 0.1
    ) -> list:
    """
    Возвращает список [x, y] координат клеток, в которых есть цвет (не белый и не прозрачный).
    color_threshold — минимальная сумма отличий от белого (255,255,255) для учета пикселя как цветного.
    fill_percent_threshold — минимальная доля цветных пикселей в клетке (от 0 до 1), чтобы считать клетку цветной.
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
            pixels = cell.getdata()
            color_pixel_count = 0
            total_pixel_count = len(pixels)
            for px in pixels:
                r, g, b, a = px
                if a > 0 and (abs(r-255) + abs(g-255) + abs(b-255)) > color_threshold:
                    color_pixel_count += 1
            if total_pixel_count > 0 and (color_pixel_count / total_pixel_count) >= fill_percent_threshold:
                colored_cells.append([x, y])
    return colored_cells

if __name__ == "__main__":
    
    grid_lst = get_colored_cells_from_image(
        image_filename="null_map.png",
        cell_size=100,
        color_threshold=10
    )

    create_grid_with_labels(
        image_filename="Остров 1.png",
        output_filename="sector_map.png",
        cell_size=100,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        text_color=(0, 0, 0, 255),
        cell_list=grid_lst
    )

    draw_grid_on_image(
        image_filename="Остров 1.png",
        output_filename="sector_map_with_grid.png",
        cell_size=100,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        cells=grid_lst
    )

    draw_colored_cells_on_image(
        image_filename="sector_map_with_grid.png",
        output_filename="sector_map_colored_cells.png",
        cells=[
            {"cell": [3, 2], "color": (255, 0, 0, 100), "text": "Привет, это я"},
            {"cell": [2, 3], "color": (255, 0, 0, 100)},
            {"cell": [3, 3], "color": (255, 0, 0, 100)},
            {"cell": [4, 3], "color": (255, 0, 0, 100)},
            {"cell": [4, 2], "color": (255, 0, 0, 100)},
            # Добавьте другие клетки по необходимости
        ],
        cell_size=100
    )