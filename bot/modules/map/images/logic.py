


import os
from PIL import Image


def get_colored_cells_from_image(
    image_filename: str,
    cell_size: int = 100,
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