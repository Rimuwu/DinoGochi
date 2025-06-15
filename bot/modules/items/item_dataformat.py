



from random import choices, shuffle
from typing import Optional
from bot.modules.items.item import GetItem

standart_rarity_chances = {
    "common": 50,
    "uncommon": 25,
    "rare": 15,
    "mystical": 9,
    "legendary": 1,
    "mythical": 0.1
}

def rare_random(items: list[str], count: int = 1, 
                chances_add: Optional[dict[str, int]] = None,
                special_chances: Optional[dict[str, int]] = None,
                rarity_chances: Optional[dict[str, int]] = None,
                advanced_rank_for_items: Optional[dict[str, list[str]]] = None
                ) -> list[str]:
    """Функция выбирает случайные предметы из списка на основе их редкости.
       chances_add - словарь с шансами, которые нужно добавить к основным шансам
       special_chances - словарь с шансами, которые нужно использовать вместо основных для определённых предметов (0-100)
    """
    shuffle(items)

    if not rarity_chances:
        # Если не переданы шансы редкости, используем стандартные
        rarity_chances = standart_rarity_chances.copy()
    
    if not advanced_rank_for_items:
        # Если не переданы продвинутые редкости, используем пустой словарь
        advanced_rank_for_items = {}

    if chances_add:
        # Добавляем шансы из переданного словаря
        # Если ключ уже существует, то изменяем его значение
        for key, value in chances_add.items():
            if key in rarity_chances:
                rarity_chances[key] += value
            else:
                rarity_chances[key] = value

    # Получаем данные о редкости предметов
    item_chances = []
    for item in items:
        # Проверяем, есть ли предмет в каком-либо списке значений advanced_rank_for_items
        rank = None
        if advanced_rank_for_items:
            for adv_rank, adv_items in advanced_rank_for_items.items():
                if item in adv_items:
                    rank = adv_rank
                    break
        if not rank:
            rank = GetItem(item).rank

        if special_chances and item in special_chances:
            # Используем специальные шансы, если они указаны для предмета
            item_chances.append(special_chances[item])
        else:
            # Используем стандартные шансы
            item_chances.append(rarity_chances[rank])

    # Нормализуем шансы
    total_chance = sum(item_chances)
    weights = [chance / total_chance for chance in item_chances]

    # Выбираем случайные предметы
    selected_items = choices(items, weights=weights, k=count)
    return selected_items

rarity_to_int = {
    "common": 0, "uncommon": 1, 
    "rare": 2, "mystical": 3,
    "legendary": 4, "mythical": 5
}

def sort_f(item_id: str):
    """ Функция сортирует список с id предметов по их редкости
    """
    dt = GetItem(item_id)
    return rarity_to_int[dt.rank]

def rare_sort(items: list[str]):
    """ Функция сортирует список с id предметов по их редкости. От обычного к легендарному
    """

    new_list = items.copy()
    new_list.sort(key=lambda x: sort_f(x))

    return new_list

def add_to_rare_sort(items: list[str], item_id: str):
    new_list = items.copy()
    
    dt = GetItem(item_id)
    if not dt: return items

    rarity = rarity_to_int[dt.rank]
    for i, item in enumerate(new_list):
        if rarity_to_int[GetItem(item).rank] >= rarity:
            new_list.insert(i, item_id)
            break

    return new_list