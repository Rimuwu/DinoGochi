

from bot.const import MAP
from bot.modules.map.biome import Biome, get_biome_on_cell
from bot.modules.map.map_data import get_safe_cells

class Location:

    def __init__(self, island: str, x: int, y: int) -> None:
        self.island = island
        self.x = x
        self.y = y

        self.weight: list[int] = [1, 1, 1, 1] # [up, down, left, right]

        # Загрузка данных из памяти 
        self.location_data = {}
        self.from_data()
        self.objects: list[str] = self.objects_collect()

        self.biome: Biome = get_biome_on_cell(island, f'{x}.{y}')
        self.is_safe: bool = f'{x}.{y}' in safe_cells_on_islands.get(
                                             island, [])

    def objects_collect(self):
        objects_set = {'town', 'dungeon', 'tower'}
        return list(set(self.location_data.keys()) & objects_set)

    def from_data(self):
        """
        Загружает данные локации из глобальной карты.
        """
        str_cords = f'{self.x}.{self.y}'

        if self.island in MAP:
            if str_cords in MAP[self.island]['cells']:
                location_data = MAP[self.island]['cells'][str_cords]
                for key, value in location_data.items():
                    setattr(self, key, value)

                self.location_data = location_data

            else:
                raise ValueError(f"Location '{self.x}, {self.y}' not found on island '{self.island}'.")
        else:
            raise ValueError(f"Island '{self.island}' not found in map data.")
    
    def __eq__(self, other):
        """
            Проверка на равенство двух локаций.
        """
        if not isinstance(other, Location):
            return NotImplemented

        return (self.x, self.y, self.island) == (other.x, other.y, other.island)


def is_within_tolerance(a: int, b: int, tolerance: int = 30) -> bool:
    """
    Проверяет, что разница между a и b не превышает tolerance.
    """
    return abs(a - b) <= tolerance


def fast_safe_cells_load():
    safe_cells_on_islands = {}

    for island in MAP.keys():
        safe_cells_on_islands[island] = get_safe_cells(island)
    return safe_cells_on_islands

safe_cells_on_islands: dict[str, list[str]] = fast_safe_cells_load()

