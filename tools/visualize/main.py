import json
import uuid
import os
from copy import deepcopy


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


# Загрузка локализации
localization_data = {}
localization_path = r"C:\Папки\коды\Telegram DinoGochi\DinoGochi\bot\localization\ru.json"
with open(localization_path, "r", encoding="utf-8") as loc_file:
    localization_data = json.load(loc_file)
localization_data = localization_data['ru']['items_names']

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

directory_path = r"C:\Папки\коды\Telegram DinoGochi\DinoGochi\bot\json\items"
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

def generate_recipes_canvas(recipes_data, output_file):
    nodes = []
    edges = []

    def add_node(item_id, label, x, y):
        """
        Добавляет узел, если он ещё не существует.
        """
        node_id = str(uuid.uuid4())
        nodes.append({
            "id": node_id,
            "type": "text",
            "x": x,
            "y": y,
            "width": 200,
            "height": 80,
            "text": label
        })
        return node_id

    def add_edge(from_id, to_id):
        """
        Добавляет связь между узлами.
        """
        edges.append({
            "id": str(uuid.uuid4()),
            "fromNode": from_id,
            "toNode": to_id
        })

    def process_material(material_id, x, y):
        """
        Рекурсивно обрабатывает материал, добавляя его к графу.
        """
        material_label = get_item_name(material_id)
        material_node_id = add_node(material_id, material_label, x, y)

        # Проверяем, если материал сам является результатом другого крафта
        for recipe_id, recipe in recipes_data.items():
            for created_item in recipe.get("create", {}).get("main", []):
                if created_item["item"] == material_id:
                    # Добавляем связь от рецепта к материалу
                    recipe_node_id = process_recipe(recipe_id, x - 400, y)
                    add_edge(recipe_node_id, material_node_id)

        return material_node_id

    def process_recipe(recipe_id, x, y):
        """
        Обрабатывает рецепт, добавляя его и связанные материалы к графу.
        """
        recipe_label = get_item_name(recipe_id)
        recipe_node_id = add_node(recipe_id, recipe_label, x, y)

        # Добавляем материалы рецепта
        y_offset = y
        for material in recipes_data[recipe_id].get("materials", []):
            material_id = material["item"]
            material_node_id = process_material(material_id, x - 400, y_offset)
            add_edge(material_node_id, recipe_node_id)
            y_offset += 200

        # Добавляем создаваемые предметы
        y_offset = y
        for created_item in recipes_data[recipe_id].get("create", {}).get("main", []):
            created_item_id = created_item["item"]
            created_item_label = get_item_name(created_item_id)
            created_item_node_id = add_node(created_item_id, created_item_label, x + 400, y_offset)
            add_edge(recipe_node_id, created_item_node_id)
            y_offset += 200

        return recipe_node_id

    # Обрабатываем все рецепты
    x_offset = 0
    y_offset = 0
    for recipe_id in recipes_data.keys():
        process_recipe(recipe_id, x_offset, y_offset)
        y_offset += 400  # Смещаемся вниз для следующего рецепта

    # Формируем данные для Canvas
    canvas_data = {
        "type": "canvas",
        "version": "0.1.6",
        "nodes": nodes,
        "edges": edges
    }

    # Сохраняем в файл
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(canvas_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    recipes_file = r"C:\Папки\коды\Telegram DinoGochi\DinoGochi\tools\visualize\items\recipes.json"
    output_canvas = r"C:\Папки\коды\Telegram DinoGochi\DinoGochi\tools\visualize\bot-value\recipes_canvas.canvas"

    with open(recipes_file, "r", encoding="utf-8") as f:
        recipes_data = json.load(f)

    generate_recipes_canvas(recipes_data, output_canvas)
