
from bot.modules.logs import log
from bot.const import DINOS

def count_unique_names():
    """ Считает семейства динозавров по уникальным именам """
    elements = DINOS.get('elements', [])
    unique_names = set(
        element['name'] for key, element in elements.items() if element['type'] == 'dino'
    )
    return len(unique_names)

families = count_unique_names()
log(f"Количество уникальных семейств динозавров: {families}")

def count_all_dinos():
    """ Считает общее количество динозавров """
    return len(DINOS['data']['dino'])

all_dinos = count_all_dinos()
log(f"Общее количество динозавров: {all_dinos}")
