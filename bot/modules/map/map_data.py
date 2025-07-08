
import string
from typing import Any, Union
from bot.const import MAP

def get_island_cells(island_name: str) -> list[tuple[int, int]]:
    """
    Получает список координат клеток острова в виде кортежей (x, y).

    :param island_name: Название острова.
    :return: Список кортежей с координатами клеток (x, y).
    """
    island_data = MAP.get(island_name, {})
    cells = []

    for cell in island_data['cells'].keys():
        x, y = map(int, cell.split('.'))
        cells.append((x, y))

    return cells

def get_island_cells_letter(island_name: str) -> list[str]:
    """
    Получает список координат клеток острова в виде строк (например, 'A6').

    :param island_name: Название острова.
    :return: Список строк с координатами клеток.
    """
    island_data = MAP.get(island_name, {})
    cells = []

    for cell in island_data['cells'].keys():
        x, y = map(int, cell.split('.'))
        letter = string.ascii_uppercase[x - 1]
        cells.append(f"{letter}{y}")

    return cells

def letter_to_number(letter: str):
    """
        A6 -> (1, 6)
    """

    column = string.ascii_uppercase.index(letter[0]) + 1
    row = int(letter[1:])
    return (column, row)

def string_cell_to_list(cell_str):
    """
    Преобразует строку вида '1.2' в список [1, 2].
    """
    return [int(x) for x in cell_str.split('.')]

def cell_to_string(cell: Union[tuple[int, int], list[int]]) -> str:
    """
    Преобразует координаты клетки в строку формата 'x.y'.
    
    :param cell: Кортеж или список с координатами клетки (x, y).
    :return: Строка с координатами клетки.
    """
    return f"{cell[0]}.{cell[1]}"

def get_island_image(island_name: str) -> str:
    """
    Получает имя файла фона для указанного острова.
    
    :param island_name: Название острова.
    :return: Имя файла фона.
    """
    island_data = MAP.get(island_name, {})
    standart = island_data.get('background', 'default_background.png')
    way = 'images/world/' + standart
    return way

async def get_events_for_island(island_name: str) -> list[tuple[int, int]]:
    """
    Получает список событий для указанного острова.
    
    :param island_name: Название острова.
    :return: Список событий.
    """
    
    events_cells = []
    # Пример
    events_cells = [(1, 2), (3, 4), (5, 6)]

    # Тут код получения из бд
    return events_cells

async def get_wagon_for_island(island_name: str):
    """
    :param island_name: Название острова.
    :return: Кортеж с координатами где находится вагон и список ячеек с путями.
    """

    wagon_cords: list[int] | None = []
    wey_cells: list[tuple[int, int]] = []

    # Тут код получения из бд
    return wagon_cords, wey_cells

async def get_user_home(user_id: int):
    
    cords = (3, 5)  # Пример координат дома
    island = 'shark_island'  # Пример острова, где находится дом
    
    return cords, island

async def data_object_on_map(island_name: str,
                             wagon: bool, 
                             objects: bool, events: bool,
                             user_home: int | None = None):
    """
    """

    island_objects = []
    islands_ways = []
    
    if wagon:
        wagon_cords, wey_cells = await get_wagon_for_island('shark_island')
        if wagon_cords and wey_cells:
            island_objects.extend([
                {
                    "cell": [*wagon_cords],
                    "color": 0, 
                    "icon": 'wagon'
                }
            ])

            islands_ways.append(wey_cells)

    if objects:
        for cell_key, cell_data in MAP[island_name]['cells'].items():
            cell_coords = string_cell_to_list(cell_key)
            icon = None

            if 'town' in cell_data:
                icon = 'town'

            elif 'dungeon' in cell_data:
                icon = 'cave'

            elif 'tower' in cell_data:
                icon = 'tower'

            if icon:
                island_objects.append({
                    "cell": cell_coords,
                    "color": 0,
                    "icon": icon
                })

    if events:
       events_cords = await get_events_for_island(island_name)
       for event in events_cords:
           island_objects.append({
               "cell": [*event],
               "color": 0,
               "icon": 'exclamation'
           })

    if user_home:
        home_coords, home_island = await get_user_home(user_home)
        if home_island == island_name:
            island_objects.append({
                "cell": [*home_coords],
                "color": 0,
                "icon": 'home'
            })

    return island_objects, islands_ways

def get_safe_cells(island: str) -> list[list[str]]:
    """
    Получает список безопасных ячеек для указанного острова.
    :param island: Название острова.
    :return: Список безопасных ячеек в формате x.y
    """
    safe_cells = []

    for cell in MAP.get(island, {}).get('safe_cells', []):
        cell: dict[str, Any] = cell

        safe_cells.append(cell['cell'])
        if cell['radius'] > 1:
            it_cell = string_cell_to_list(cell['cell'])
            
            for dx in range(-cell['radius'], cell['radius'] + 1):
                for dy in range(-cell['radius'], cell['radius'] + 1):
                    new_cell = f"{it_cell[0] + dx}.{it_cell[1] + dy}"
                    if new_cell not in safe_cells:
                        safe_cells.append(new_cell)

    return safe_cells