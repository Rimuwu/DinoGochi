
import json
from PIL import ImageFont
from main import draw_grid_on_image, draw_colored_cells_on_image, draw_sector_names_on_image, get_colored_cells_from_image



with open('map.json', encoding='utf-8') as f: 
    map_data = json.load(f)['shark_island'] # type: dict


def string_cell_to_list(cell_str):
    """
    Преобразует строку вида '1,2' в список [1, 2].
    """
    return [int(x) for x in cell_str.split('.')]

if __name__ == "__main__":
    cell_size = 100
    
    # Используем более жирный шрифт, если доступен
    try:
        bold_font = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        bold_font = ImageFont.truetype("arial.ttf", 24)
    
    grid_lst = get_colored_cells_from_image(
        image_filename="null_map.png",
        cell_size=cell_size,
        fill_percent_threshold=0.43
        # color_threshold=10
    )
    
    result_img = draw_grid_on_image(
        image_filename="Остров 1.png",
        # output_filename="sector_map_with_grid.png",
        cell_size=cell_size,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        cells=grid_lst,
        fill_alpha=0
    )
    
    cells = [
        # {"cell": [3, 2], "color": (255, 0, 0, 100),
        #  "icon": "flag"},
        # {"cell": [2, 4], "color": (255, 0, 0, 100)},
    ]

    biomes = []

    for biome_name, biome in map_data['biomes'].items():
        if 'cells' in biome:
            if 'color' in biome:
                if isinstance(biome['color'], list):
                    color = tuple(biome['color'])
                else:
                    color = biome['color']
            else:
                color = (0, 0, 0, 0)

            for cell in biome['cells']:
                icon = None
                if 'icon' in biome:
                    icon = biome['icon']

                cell_coords = string_cell_to_list(cell)
                # Определяем стены: [лево, верх, право, низ]

                walls = [0, 0, 0, 0]
                directions = [(-1, 0), (0, -1), (1, 0), (0, 1)]

                for i, (dx, dy) in enumerate(directions):
                    neighbor = [cell_coords[0] + dx, cell_coords[1] + dy]
                    neighbor_str = f"{neighbor[0]}.{neighbor[1]}"

                    if neighbor_str not in biome['cells']:
                        # Стенка есть
                        wall_key = tuple(sorted([
                            (cell_coords[0], cell_coords[1], i),
                            (neighbor[0], neighbor[1], (i + 2) % 4)
                        ]))
                        walls[i] = 1

                biomes.append({
                    "cell": cell_coords,
                    "color": "#0009003B",
                    "icon": icon,
                    "walls": walls,
                    "wall_color": color, #'white'
                    "wall_margin": 0,
                    "wall_width": 4
                })

    cells += biomes

    result1_img = draw_colored_cells_on_image(
        result_img,
        # output_filename="sector_map_colored_cells.png",
        cells=cells,
        cell_size=cell_size
    )

    result1_img = draw_sector_names_on_image(
        result1_img,
        grid_lst,
        cell_size=cell_size,
        font=bold_font,
        color_cell_names='white',
        color_table_names='white',
        font_size=24,
        letter_mode=True  # Используем числа для координат
    )
    
    result1_img.save("visual1.png", "PNG")

    cells_vis = []
    captured_cells = [
        '7.5', '7.6', '7.7', '7.8', '8.5', '8.6', '8.7', '8.8',
        '9.9'
    ]
    my_zones = [
        '9.9'
    ]

    for safe_cell in map_data['safe_cells']:
        cell_coords = string_cell_to_list(safe_cell['cell'])
        radius = safe_cell.get('radius', 0)
        if radius > 0:
            # Добавляем все клетки в радиусе (включая центральную), только если они существуют в сетке
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    new_cell = [cell_coords[0] + dx, cell_coords[1] + dy]
                    if new_cell in grid_lst:
                        cells_vis.append({
                            "cell": new_cell,
                            "color": (0, 255, 0, 80),  # Зеленый цвет для безопасных клеток
                            "icon": 'shield'
                        })
        else:
            if cell_coords in grid_lst:
                cells_vis.append({
                    "cell": cell_coords,
                    "color": (0, 255, 0, 80),  # Зеленый цвет для безопасных клеток
                    "icon": 'shield'
                })
    
    for cell_str in captured_cells:
        cell_coords = string_cell_to_list(cell_str)
        color = (255, 0, 0, 120)  # Красный
        icon = 'flag'
        if cell_str in my_zones:
            color = (0, 0, 255, 120)  # Синий
        if cell_coords in grid_lst:
            cells_vis.append({
                "cell": cell_coords,
                "color": color,
                "icon": icon
            })
    

    result2_img = draw_colored_cells_on_image(
        result_img,
        # output_filename="sector_map_colored_cells.png",
        cells=cells_vis,
        cell_size=cell_size
    )

    result2_img = draw_sector_names_on_image(
        result2_img,
        grid_lst,
        cell_size=cell_size,
        font=bold_font,
        color_cell_names='white',
        color_table_names='white',
        font_size=24,
        letter_mode=True  # Используем числа для координат
    )

    result2_img.save("visual2.png", "PNG")

    result_img = draw_grid_on_image(
        image_filename="Остров 1.png",
        # output_filename="sector_map_with_grid.png",
        cell_size=cell_size,
        cell_width=4,
        line_color=(0, 0, 0, 100),
        cells=grid_lst,
        fill_alpha=80
    )
    
    cells_vis = []
    for cell_key, cell_data in map_data['cells'].items():
        cell_coords = string_cell_to_list(cell_key)
        icon = None

        if 'town' in cell_data:
            icon = 'town'

        elif 'dungeon' in cell_data:
            icon = 'cave'

        elif 'tower' in cell_data:
            icon = 'tower'

        if icon:
            cells_vis.append({
                "cell": cell_coords,
                "color": 0,
                "icon": icon
            })
    
    events_cells = [
        '10.7', '10.7', '10.8', '10.9', '11.7', '11.8', '11.9',
    ]
    
    events_cells = list(set(events_cells))

    for cell_str in events_cells:
        cell_coords = string_cell_to_list(cell_str)
        if cell_coords in grid_lst:
            cells_vis.append({
                "cell": cell_coords,
                "color": 0, 
                "icon": 'exclamation'
            })
    
    dino_cells = [
        '6.6', '17.7', '11.4', '10.8', '3.4'
    ]
    
    dino_cells = list(set(dino_cells))

    for cell_str in dino_cells:
        cell_coords = string_cell_to_list(cell_str)
        if cell_coords in grid_lst:
            cells_vis.append({
                "cell": cell_coords,
                "color": 0, 
                "icon": 'dino'
            })

    # Тележка с товаром
    cells_vis.append({
        "cell": string_cell_to_list('9.6'),
        "color": 0, 
        "icon": 'wagon'
    })
    
    # Дом
    cells_vis.append({
        "cell": string_cell_to_list('9.6'),
        "color": 0, 
        "icon": 'home'
    })

    result3_img = draw_colored_cells_on_image(
        result_img,
        # output_filename="sector_map_colored_cells.png",
        cells=cells_vis,
        cell_size=cell_size
    )

    result3_img = draw_sector_names_on_image(
        result3_img,
        grid_lst,
        cell_size=cell_size,
        font=bold_font,
        color_cell_names='white',
        color_table_names='white',
        font_size=24,
        letter_mode=True  # Используем числа для координат
    )

    result3_img.save("visual3.png", "PNG")