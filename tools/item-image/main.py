from math import comb
from PIL import Image



def trans_paste(fg_img: Image.Image, bg_img: Image.Image, 
                alpha=1.0, box=(0, 0)):
    """Накладывает одно изображение на другое.
    """
    fg_img_trans = Image.new('RGBA', fg_img.size)
    fg_img_trans = Image.blend(fg_img_trans, fg_img, alpha)
    bg_img.paste(fg_img_trans, box, fg_img_trans)

    return bg_img

def create_item_image(item_path: str, background_path: str, middle_element_path: str
                      ) -> Image.Image:
    """
    Создаёт изображение предмета на основе заднего фона и среднего элемента.
    :param item_path: Путь к изображению предмета
    :param background_path: Путь к изображению заднего фона
    :param middle_element_path: Путь к изображению среднего элемента
    :return: Объект PIL.Image итогового изображения
    """
    path = '../../images/items/'

    # Открываем изображения
    item_image = Image.open(path + '/items-icons/' + item_path + '.png').convert("RGBA")
    background = Image.open(path + '/items-bg/' + background_path + '.png').convert("RGBA")
    bg_w, bg_h = background.size

    middle_element = Image.open(path + '/items-elements/' + middle_element_path + '.png').convert("RGBA")

    # Накладываем средний элемент на фон
    combined = trans_paste(middle_element, background)
    combined = trans_paste(item_image, combined,
                           1,
                           (bg_w // 2 - item_image.width // 2,
                            bg_h // 2 - item_image.height // 2)
                           )
    combined = combined.convert("RGB")
    return combined

# Пример использования:
img = create_item_image("axe", "orange", "circle")
img.show()