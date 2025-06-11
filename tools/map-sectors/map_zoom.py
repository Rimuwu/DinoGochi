from PIL import Image
import io
import os


def zoom_map_on_cell(image_input, cell, cell_size, zoom_factor, images_folder=None, radius_x=0, radius_y=0):
    """
    Вырезает область вокруг клетки из карты и увеличивает её.

    :param image_input: bytes изображения или имя файла (str)
    :param cell: (x, y) — координаты клетки
    :param cell_size: размер клетки в пикселях (int)
    :param zoom_factor: во сколько раз увеличить клетку (float или int)
    :param images_folder: путь к папке с изображениями (если image_input — имя файла)
    :param radius_x: радиус по горизонтали (в клетках)
    :param radius_y: радиус по вертикали (в клетках)
    :return: PIL.Image с увеличенной областью
    """
    # Получаем изображение
    if isinstance(image_input, bytes):
        image = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, str):
        path = image_input if images_folder is None else os.path.join(images_folder, image_input)
        image = Image.open(path)
    else:
        raise ValueError("image_input должен быть байтами или строкой (именем файла)")

    x, y = cell
    left = (x - radius_x) * cell_size
    upper = (y - radius_y) * cell_size
    right = (x + radius_x + 1) * cell_size
    lower = (y + radius_y + 1) * cell_size

    # Ограничиваем координаты рамками изображения
    left = max(left, 0)
    upper = max(upper, 0)
    right = min(right, image.width)
    lower = min(lower, image.height)

    cell_img = image.crop((left, upper, right, lower))
    new_size = (int((right - left) * zoom_factor), int((lower - upper) * zoom_factor))
    zoomed_img = cell_img.resize(new_size, Image.NEAREST)
    return zoomed_img

# Пример использования:
# Зумим область вокруг клетки (3, 2), радиус 1 по x и 2 по y, размер клетки 100, увеличить в 4 раза
zoomed = zoom_map_on_cell("sector_map_colored_cells.png", 
                          (6, 6), 100, 4, images_folder=".", 
                          radius_x=2, radius_y=1)

zoomed.save("zoomed_cell.png")  # Сохраняем результат