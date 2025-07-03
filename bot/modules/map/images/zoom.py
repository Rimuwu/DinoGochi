from PIL import Image

def zoom_map_on_cell(image: Image.Image, 
                     cell: tuple, zoom_factor: float, 
                     radius_x = 0, radius_y = 0,
                     cell_size: int = 100):
    """
    Вырезает область вокруг клетки из карты и увеличивает её.

    :param image: PIL.Image — изображение
    :param cell: (x, y) — координаты клетки
    :param cell_size: размер клетки в пикселях (int)
    :param zoom_factor: во сколько раз увеличить клетку (float или int)
    :param images_folder: путь к папке с изображениями (если image_input — имя файла)
    :param radius_x: радиус по горизонтали (в клетках)
    :param radius_y: радиус по вертикали (в клетках)
    :return: PIL.Image с увеличенной областью
    """

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
    new_size = (int((right - left) * zoom_factor), 
                int((lower - upper) * zoom_factor)
                )
    zoomed_img = cell_img.resize(new_size, Image.NEAREST)
    return zoomed_img
