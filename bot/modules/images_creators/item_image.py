

from PIL import Image
from bot.modules.data_format import pil_image_to_file
from bot.modules.images import trans_paste

def create_item_image(item_path: str | None, 
                      background_path: str, 
                      element_path: str | None
                      ):
    """
    Создаёт изображение предмета на основе заднего фона и среднего элемента.
    :param item_path: Путь к изображению предмета
    :param background_path: Путь к изображению заднего фона
    :param element_path: Путь к изображению элемента
    :return: Объект PIL.Image итогового изображения
    """
    path = 'images/items'

    # Открываем изображения
    background = Image.open(path + '/items-bg/' + background_path + '.png').convert("RGBA")
    bg_w, bg_h = background.size

    if item_path:
        item_image = Image.open(path + '/items-icons/' + item_path + '.png').convert("RGBA")

    if element_path:
        middle_element = Image.open(path + '/items-elements/' + element_path + '.png').convert("RGBA")

    # Накладываем средний элемент на фон
    combined = trans_paste(middle_element, background)
    combined = trans_paste(item_image, combined, 1,
                           (bg_w // 2 - item_image.width // 2,
                            bg_h // 2 - item_image.height // 2)
                           )
    combined = combined.convert("RGB")

    buf =  pil_image_to_file(combined, quality='maximum')
    buf.filename = f'{item_path}_{background_path}_{element_path}.png'

    return buf