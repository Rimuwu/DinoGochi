import json
import os
import pathlib
import uuid
from copy import deepcopy


LANGUAGE = 'ru'  # Укажите язык локализации, который вы хотите использовать

localization_data = {}
base_path = pathlib.Path(__file__).parent.parent.parent
localization_path = base_path / "bot"  / "localization" / f"{LANGUAGE}.json"
with open(localization_path, "r", encoding="utf-8") as loc_file:
    localization = json.load(loc_file)

localization_data = localization[LANGUAGE]['items_names']
loc_group_data = localization[LANGUAGE]['groups']

def gather_json_files(directory):
    json_data = {}

    # Перебираем все файлы в заданной директории
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                items = json.load(file)

                for key, value in items.items():
                    json_data[key] = value

    return json_data

directory_path = base_path / "bot" / "json" / "items"
ITEMS = gather_json_files(directory_path)

def get_all_items() -> dict: 
    return deepcopy(ITEMS)  # type: ignore

def load_items_names() -> dict:
    """Загружает все имена предметов из локализации в один словарь."""
    items_names = {}
    loc_items_names = localization_data

    for item_key in ITEMS:
        if item_key not in items_names:
            items_names[item_key] = {}

        for loc_key in loc_items_names.keys():
            loc_name = loc_items_names[loc_key].get(item_key)
            if loc_name:
                items_names[item_key][loc_key] = loc_name
            else:
                items_names[item_key][loc_key] = item_key
    return items_names

def get_item_name(item_key) -> str:
    """
    Получает имя предмета из локализационного файла по ключу.
    """
    if isinstance(item_key, list):
        item_key = item_key[0]  # Берем первый элемент, если это список
    if isinstance(item_key, dict):
        return str(item_key)  # Преобразуем словарь в строку
    item_info = localization_data.get(item_key, {})
    return item_info.get("name", str(item_key))

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

def find_item_in_ns_craft(item_id, items):
    """
    Ищет предмет с указанным item_id в ns_craft других предметов.

    :param item_id: ID предмета, который нужно найти.
    :param items: Словарь всех предметов.
    :return: Список предметов-источников, создающих данный предмет.
    """
    sources = []
    for source_item_id, source_item_data in items.items():
        if "ns_craft" in source_item_data:
            for craft_id, craft_data in source_item_data["ns_craft"].items():
                if "create" in craft_data and item_id in craft_data["create"]:
                    sources.append((source_item_id, craft_id))
    return sources

def check_recipes_for_item(item_id, recipes_data, localization_data, x_offset, y_offset, add_node, add_edge, item_node_id):
    """
    Проверяет рецепты, создающие указанный предмет, и добавляет их на холст.

    :param item_id: ID предмета, который нужно проверить.
    :param recipes_data: Словарь всех рецептов.
    :param localization_data: Данные локализации для отображения имен.
    :param x_offset: Смещение по оси X для узлов.
    :param y_offset: Смещение по оси Y для узлов.
    :param add_node: Функция для добавления узлов на холст.
    :param add_edge: Функция для добавления связей на холст.
    :param item_node_id: ID узла предмета, для которого проверяются рецепты.
    """
    for recipe_id, recipe_data in recipes_data.items():
        for create_category, create_items in recipe_data.get("create", {}).items():
            for created_item in create_items:
                if created_item.get("item") == item_id:
                    recipe_name = localization_data.get(recipe_id, {}).get("name", recipe_id)
                    recipe_node_id = add_node(f"Рецепт: {recipe_name}", x_offset - 500, y_offset + 200, color="#a1c4fd")
                    add_edge(recipe_node_id, item_node_id, color="#0000ff", label="Создано в рецепте")

def generate_items_sources_canvas(items, items_groups, recipes_data, localization_data, output_file):
    """
    Генерирует Canvas, где для каждого предмета указывается, где он найден (группы, рецепты, настольные крафты).
    """
    nodes = []
    edges = []
    occupied_positions = set()
    
    def add_edge(from_id, to_id, from_side=None, to_side=None, color=None, label=None):
        """
        Добавляет связь между узлами с учётом смещения начала и конца стрелки, поддержкой цвета и текста.
        """
        
        # Проверяем, есть ли уже связь между узлами
        for edge in edges:
            if edge["fromNode"] == from_id and edge["toNode"] == to_id:
                return  # Если связь уже существует, ничего не делаем
            else:
                # Проверяем, есть ли связь в обратном направлении
                if edge["fromNode"] == to_id and edge["toNode"] == from_id:
                    return

        edge = {
            "id": str(uuid.uuid4()),
            "fromNode": from_id,
            "toNode": to_id,
            "fromSide": from_side,
            "toSide": to_side,
            # "color": color,
            # 'label': label
        }

        edges.append(edge)

    def find_free_position(x, y):
        while (x, y) in occupied_positions:
            y += 100
        occupied_positions.add((x, y))
        return x, y

    def add_node(label, x, y, color=None):
        x, y = find_free_position(x, y)
        node_id = str(uuid.uuid4())
        nodes.append({
            "id": node_id,
            "type": "text",
            "x": x,
            "y": y,
            "width": 200,
            "height": 80,
            "text": label,
            "color": color
        })
        return node_id

    x_offset, y_offset = 0, 0
    for item_id, item_data in items.items():
        item_name = localization_data.get(item_id, {}).get("name", item_id)
        item_node_id = add_node(item_name, x_offset, y_offset, color="#ff7538")

        # Проверяем группы
        group_y_offset = y_offset
        for group_id, group_items in items_groups.items():
            if item_id in group_items:
                group_name = localization_data.get(group_id, {}).get("name", group_id)
                group_node_id = add_node(f"Группа: {group_name}", x_offset - 300, y_offset, color="#f5d033")
                add_edge(group_node_id, item_node_id, color="#00ff00", label="Принадлежит группе")

        # Добавляем ноду с проверкой type_groups
        for type_group, group_items in type_groups.items():
            if item_id in group_items:
                type_group_name = localization_data.get(type_group, {}).get("name", type_group)
                type_group_node_id = add_node(f"Тип: {type_group_name}", x_offset, y_offset - 100, color="#d3d3d3")
                add_edge(type_group_node_id, item_node_id, color="#808080", label="Принадлежит типу")

        # Проверяем рецепты
        recipe_y_offset = y_offset
        for recipe_id, recipe_data in recipes_data.items():
            for created_item in recipe_data.get("create", []):
                if isinstance(created_item, dict) and created_item.get("item") == item_id:
                    recipe_name = localization_data.get(recipe_id, recipe_id)
                    add_node(f"Рецепт: {recipe_name}", x_offset - 400, recipe_y_offset, color="#a1c4fd")
                    recipe_y_offset += 100

        # Проверяем настольные крафты
        craft_y_offset = y_offset
        # Используем функцию find_item_in_ns_craft для поиска источников
        sources = find_item_in_ns_craft(item_id, items)
        for source_item_id, craft_id in sources:
            craft_source_name = localization_data.get(source_item_id, {}).get("name", source_item_id)
            craft_node_id = add_node(f"Крафт из {craft_source_name}", x_offset - 550, y_offset, color="#e0b3ff")
            add_edge(craft_node_id, item_node_id, color="#ff00ff", label="Создано в крафте")

        check_recipes_for_item(item_id, recipes_data, localization_data, x_offset, y_offset - 300, add_node, add_edge, item_node_id)

        y_offset += 500
        if y_offset > 5000:
            y_offset = 0
            x_offset += 1000

    canvas_data = {
        "type": "canvas",
        "version": "0.1.6",
        "nodes": nodes,
        "edges": edges
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(canvas_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    base_path = pathlib.Path(__file__).parent.parent.parent
    items_file = base_path / "tools" / "visualize" / "bot-value" / "items_canvas.canvas"
    items_sources_file = base_path / "tools" / "visualize" / "bot-value" / "items_canvas.canvas"
    
    generate_items_sources_canvas(ITEMS, items_groups, ITEMS, localization_data, items_sources_file)
    print(f"Canvas saved to {items_sources_file}")
