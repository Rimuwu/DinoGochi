import json
import uuid
import os
from copy import deepcopy
import pathlib

# Загрузка локализации
# https://jsoncanvas.org - документация

localization_data = {}
base_path = pathlib.Path(__file__).parent.parent.parent
localization_path = base_path / "bot"  / "localization" / "ru.json"
with open(localization_path, "r", encoding="utf-8") as loc_file:
    localization = json.load(loc_file)

localization_data = localization['ru']['items_names']
loc_group_data = localization['ru']['groups']

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

def get_group(group: str):
    """Возвращает список с id всех предметов в ней
    """
    result = []

    if group in items_groups:
        result = items_groups[group].copy()
    if group in type_groups:
        result = list(set(result) | set(type_groups[group]))

    return result

def generate_recipes_canvas(recipes_data, output_file):
    nodes = []
    edges = []
    node_positions = {}  # Для отслеживания координат узлов
    occupied_positions = set()  # Для предотвращения наложений

    def find_free_position(x, y):
        """
        Находит свободные координаты, если текущие заняты.
        """
        while (x, y) in occupied_positions:
            y += 100  # Сдвигаем вниз
        occupied_positions.add((x, y))
        return x, y
    
    def add_node(item_id, label, x, y, color=None):
        """
        Добавляет узел, если он ещё не существует.
        Если узел с таким же текстом уже существует в радиусе 100 пикселей, возвращает его ID.
        """
        # Проверяем, есть ли уже узел с таким текстом в радиусе 100 пикселей
        for node in nodes:
            node_x, node_y = node["x"], node["y"]
            if node["text"] == label and abs(node_x - x) <= 100 and abs(node_y - y) <= 100:
                return node["id"]

        # Если узел не найден, создаём новый
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
        node_positions[item_id] = (x, y)
        return node_id

    def add_edge(from_id, to_id, from_side=None, to_side=None, color=None, label=None):
        """
        Добавляет связь между узлами с учётом смещения начала и конца стрелки, поддержкой цвета и текста.
        """

        edge = {
            "id": str(uuid.uuid4()),
            "fromNode": from_id,
            "toNode": to_id,
            "fromSide": from_side,
            "toSide": to_side,
            "color": color,
            'label': label
        }

        edges.append(edge)

    def process_material(material_id, x, y, count):
        """
        Рекурсивно обрабатывает материал, добавляя его к графу.
        """
        material_label = f"{get_item_name(material_id)} x{count}"  # Добавлено количество материала
        material_node_id = add_node(material_id, material_label, x, y, color='#ff7538')

        # Проверяем, если материал сам является результатом другого крафта
        for recipe_id, recipe in recipes_data.items():
            for created_item in recipe.get("create", {}).get("main", []):
                if created_item["item"] == material_id:
                    # Добавляем связь от рецепта к материалу
                    recipe_node_id = process_recipe(recipe_id, x - 400, y)
                    add_edge(recipe_node_id, material_node_id)  # Стрелка справа

        return material_node_id

    def process_group(group_id, x, y, count):
        """
        Рекурсивно обрабатывает группу, добавляя предметы из неё к графу.
        """
        y_offset = y
        x_offset = x
        group_items = get_group(group_id)
        group_name = loc_group_data.get(group_id, group_id)

        y_offset += 200
        # x_offset -= 50
        group_node_id = add_node(group_id, group_name + ' (GROUP)', x_offset, y_offset, '#f5d033')

        # Добавляем предметы из группы
        col, max_col = 0, 2
        for item in group_items:
            col += 1

            if col <= max_col:
                
                item_node_id = process_material(item, x_offset - 400, y_offset, count)
                add_edge(item_node_id, group_node_id, to_side='left', from_side='right')  # Стрелка вниз
                y_offset += 200

        if col > max_col:
            # Если предметов больше max_col, добавляем стрелку к группе
            res = add_node(f'group_{group_id}_more', 
                     f'И ещё {col - max_col} предметов', 
                     x_offset, y + 380, color='#00ff00')
            add_edge(res, group_node_id, to_side='bottom')  # Стрелка вниз

        return group_node_id

    def process_recipe(recipe_id, x, y):
        """
        Обрабатывает рецепт, добавляя его и связанные материалы к графу.
        """
        recipe_label = get_item_name(recipe_id)
        recipe_node_id = add_node(recipe_id, recipe_label, x, y)

        # Добавляем материалы рецепта
        y_offset = y
        x_offset = x
        for material in recipes_data[recipe_id].get("materials", []):

            material_id = material["item"]
            count = material.get("count", 1)  # Получаем количество материала, если указано

            if isinstance(material_id, str):
                material_label = f"{get_item_name(material_id)} x{count}"  # Добавлено количество материала
                material_node_id = add_node(material_id, material_label, x_offset - 400, y_offset, color='#ffc261')
                material_id_str = str(material_id)
                
                add_edge(material_node_id, recipe_node_id, from_side='right')  # Стрелка справа

            elif isinstance(material_id, list):
                # Создаем общий узел для группы материалов
                y_offset += 200
                group_label = "Выбор 1-го из:"
                group_node_id = add_node(f"group_{recipe_id}_{material_id}", group_label, x_offset - 300, y_offset, color='#a1c4fd')

                for single_material_id in material_id:
                    single_material_node_id = process_material(single_material_id, x_offset - 600, y_offset, count)
                    add_edge(single_material_node_id, group_node_id, from_side='right')  # Стрелка справа
                    y_offset += 100

                # Добавляем связь от общего узла группы к рецепту
                add_edge(group_node_id, recipe_node_id, from_side='right', to_side='bottom')  # Стрелка справа

            elif isinstance(material_id, dict):
                # Создаем общий узел для группы материалов
                group_id = material_id['group']

                # Если материал является группой, то обрабатываем группу
                if group_id in items_groups:
                    # group_items = get_group(group_id)
                    # group_name = loc_group_data.get(group_id, group_id)

                    # group_node_id = add_node(group_id, group_name + ' (GROUP)', x - 200, y + 200, '#f5d033')

                    # add_edge(group_node_id, recipe_node_id, from_offset_x=200)  # Стрелка справа
                    # y_offset += 200
                    
                    group_node_id = process_group(group_id, x_offset - 400, y_offset, count)
                    # Добавляем предметы из группы
                    
                    add_edge(group_node_id, recipe_node_id, from_side='right')  # Стрелка справа

        # Добавляем создаваемые предметы из всех ключей в "create"
        y_offset = y
        x_offset = x 
        for create_key, created_items in recipes_data[recipe_id].get("create", {}).items():
            for created_item in created_items:
                created_item_id = created_item["item"]
                created_item_label = f"{get_item_name(created_item_id)} x{created_item['count']}"  # Добавлено количество создаваемого предмета
                created_item_node_id = add_node(created_item_id, created_item_label, x_offset + 400, y_offset)
                add_edge(recipe_node_id, created_item_node_id, from_side='right', to_side='left')  # Стрелка по умолчанию
                y_offset += 100
                # x_offset += 200

        return recipe_node_id

    # Обрабатываем все рецепты
    x_offset = 0
    y_offset = 0
    for recipe_id in recipes_data.keys():
        process_recipe(recipe_id, x_offset, y_offset)
        y_offset += 700  # Смещаемся вниз для следующего рецепта

        # Если достигли y равного 5000, обнуляем y и смещаемся по x
        if y_offset >= 5000:
            y_offset = 0
            x_offset += 2000

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
    recipes_file = base_path / "bot" / "json" / "items" / "recipes.json"
    output_canvas = base_path / "tools" / "visualize" / "bot-value" / "recipes_canvas.canvas"

    with open(recipes_file, "r", encoding="utf-8") as f:
        recipes_data = json.load(f)

    generate_recipes_canvas(recipes_data, output_canvas)

