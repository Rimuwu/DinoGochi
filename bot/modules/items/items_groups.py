from bot.modules.items.collect_items import get_all_items
ITEMS = get_all_items()

def load_groups():
    """ Загружает и формирует группы
    """
    items_groups, type_groups = {}, {}

    for key, item in ITEMS.items():
        typ = item['type']
        if 'groups' in item.keys():
            for group in item['groups']:
                items_groups[group] = items_groups.get(group, [])

                if key not in items_groups[group]:
                    items_groups[group].append(key)

        type_groups[typ] = type_groups.get(typ, [])
        if key not in type_groups[typ]:
            type_groups[typ].append(key)

    return items_groups, type_groups

items_groups, type_groups = load_groups()

def get_group(group: str):
    """Возвращает список с id всех предметов в ней
    """
    result = []

    if group in items_groups:
        result = items_groups[group].copy()
    if group in type_groups:
        result = list(set(result) | set(type_groups[group]))

    return result

def get_custom_groups():
    """ Возвращает весь словарь кастомных групп
    """
    return items_groups

def get_type_groups():
    """ Возвращает весь словарь групп по типу
    """
    return type_groups

def get_all_groups():
    """ Возвращает оба словаря групп\n
        items_groups | type_groups
    """
    return items_groups | type_groups