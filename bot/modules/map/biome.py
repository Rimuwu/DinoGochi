


from bot.const import MAP



class Biome:

    def __init__(self, island: str, name: str) -> None:
        """
        Инициализация объекта биома.
        """

        self.island: str = island
        self.name: str = name
        self.cells: list[str] = []

        self.color: list[int] = [0, 0, 0]  # RGB color
        self.icon: str = ''

        self.mobs: list[str] = []

        self.from_data()  # Загружаем данные биома из глобальной карты

    def __repr__(self) -> str:
        return f"Biome(name={self.name}, island={self.island})"

    def from_data(self):
        """
        Загружает данные биома из глобальной карты.
        """
        if self.island in MAP:
            if self.name in MAP[self.island]['biomes']:

                for key, value in MAP[self.island]['biomes'][self.name].items():
                    setattr(self, key, value)

            else:
                raise ValueError(f"Biome '{self.name}' not found on island '{self.island}'.")
        else:
            raise ValueError(f"Island '{self.island}' not found in map data.")



def fast_biomes_load():
    """
    Загружает биомы в кэш для быстрого доступа. 
    Возвращает словарь с путём - остров - клетка: биом
    """
    fast_biomes = {}

    for island, data in MAP.items():
        for biome, data in data['biomes'].items():
            for cell in data['cells']:
                if island not in fast_biomes:
                    fast_biomes[island] = {}
                fast_biomes[island][cell] = Biome(island, biome)

    return fast_biomes

def get_biome_on_cell(island: str, cell: str) -> Biome:
    """
    Получает биом на указанной клетке острова.
    
    :param island: Название острова.
    :param cell: Координаты клетки в формате 'x.y'.
    :return: Название биома или 'unknown' если не найден.
    """

    if island in fast_biomes:
        if cell in fast_biomes[island]:
            return fast_biomes[island][cell]
        else:
            raise ValueError(f"Cell '{cell}' not found on island '{island}'.")
    else:
        raise ValueError(f"Island '{island}' not found in fast biomes data.")

fast_biomes: dict[str, dict[str, Biome]] = fast_biomes_load()