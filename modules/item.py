import json
from pprint import pprint

from modules.localization import Localization
localization = Localization()

from modules.functions import DataFormat

with open('json/items.json', encoding='utf-8') as f: items_data = json.load(f)['items']

def get_data(itemid:str) -> dict:
    """Получение данных из json"""

    # Проверяем еть ли предмет с таким ключём в items.json
    if itemid in items_data.keys():
        return items_data[itemid]

    else: # Иначе вызываем ошибку 
        raise Exception(f"The subject with ID {itemid} does not exist.")

class ItemBase:

    def __init__(self, item_id:str | int = None, item_data:dict = None, preabil:dict = None) -> None:
        ''' Создание объекта Item

            Получаем в класс либо id предмета либо формата {"item_id": string, "abilities": dict}
            abilities - не обязателен.

            Пояснение:
              >>> Стандартный предмет - предмет никак не изменённый пользователем, сгенерированный из базы.
              >>> abilities - словарь с индивидуальными харрактеристиками предмета, прочность, использования и тд.
              >>> preabil - используется только для предмета создаваемого из базы, используется для создания нестандартного предмета.

        '''

        if item_id: # Получаем стандартный предмет, если есть только id
            self.id = str(item_id)

        elif item_data: # Предмет от пользователя, есть id и возможно abilities
            self.id = str(item_data['item_id'])
            if 'abilities' in item_data.keys():
                preabil = item_data['abilities']
            
        else:
            raise Exception(f"An empty object cannot be created.")

        self.data = get_data(self.id)
        self.name = self.get_names()
        self.user_data = self.get_item_dict(preabil=preabil)
    
    def __str__(self) -> str:
        return f"Item{self.data['type'].capitalize()}Object {self.name}"


    """ Классовые функции """
    
    def get_names(self) -> dict:
        """Внесение всех имён в данные предмета"""

        # Получаем словарь со всеми альтернативные имена предметов из локализации
        items_names = localization.get_all_text_from_key('items_names')
        data_names = self.data['name']
        name = {}

        # Проверяем есть ли ключ с языком в данных и вносим новые.
        # Приоритетом является имя из items.json
        for lang_code in items_names:
            if lang_code not in data_names.keys():
                if self.id in items_names[lang_code]:
                    name[lang_code] = items_names[lang_code][self.id]
                    self.data['name'][lang_code] = items_names[lang_code][self.id]
            
            else:
                name[lang_code] = data_names[lang_code]
        
        return name
    
    def get_item_dict(self, preabil: dict = None) -> dict:
        ''' Создание словаря, хранящийся в инвентаре пользователя.

            Примеры: 
                Просто предмет
                  >>> f(12)
                  >>> {'item_id': "12"}

                Предмет с предустоновленными 
                  >>> f(30, {'uses': 10})
                  >>> {'item_id': "30", 'abilities': {'uses': 10}}

        '''
        d_it = {'item_id': self.id}

        if 'abilities' in self.data.keys():
            abl = {}
            for k in self.data['abilities'].keys():

                if type(self.data['abilities'][k]) == int:
                    abl[k] = self.data['abilities'][k]

                elif type(self.data['abilities'][k]) == dict:
                    abl[k] = DataFormat.random_dict(self.data['abilities'][k])

            d_it['abilities'] = abl

        if preabil is not None:
            if 'abilities' in d_it.keys():
                for ak in d_it['abilities'].keys():
                    if ak in preabil.keys():

                        if type(preabil[ak]) == int:
                            d_it['abilities'][ak] = preabil[ak]

                        elif type(preabil[ak]) == dict:
                            d_it['abilities'][ak] = DataFormat.random_dict(preabil[ak])

        return d_it
    
    
    """ Используемые функции """

    def view(self) -> None:
        """ Отображает все данные объекта."""
        
        print(f'ID: {self.id}')
        print(f'NAME: {self.name}')

        print("USER_DATA: ", end='')
        pprint(self.user_data)

        print("DATA: ", end='')
        pprint(self.data)


class EatItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class EggItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class AccessoryItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class MaterialItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class RecipeItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class WeaponItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class AmmunitionItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class BackpackItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)
    
class ArmorItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class FreezingItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class DefrostingItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class CaseItem(ItemBase):

    def __init__(self, item_id: str | int = None, item_data: dict = None, preabil: dict = {}) -> None:
        super().__init__(item_id, item_data, preabil)

class CreateItem:

    def __init__(self, item_id:str | int = None, item_data:dict = None, preabil:dict = {}):
        self.item_id = item_id
        self.item_data = item_data
        self.preabil = preabil

        self.data = get_data(str(item_id))

    def new(self):
        data = (self.item_id, self.item_data, self.preabil)

        if self.data['type'] == '+eat':
            return EatItem(*data)
        
        if self.data['type'] == 'egg':
            return EggItem(*data)
        
        if self.data['type'] in ['game_ac', 'journey_ac', 'unv_ac', 'hunt_ac']:
            return AccessoryItem(*data)
        
        if self.data['type'] == 'material':
            return MaterialItem(*data)
        
        if self.data['type'] == 'recipe':
            return RecipeItem(*data)
        
        if self.data['type'] == 'weapon':
            return WeaponItem(*data)
        
        if self.data['type'] == 'ammunition':
            return AmmunitionItem(*data)
        
        if self.data['type'] == 'backpack':
            return BackpackItem(*data)
        
        if self.data['type'] == 'armor':
            return ArmorItem(*data)
        
        if self.data['type'] == 'freezing':
            return FreezingItem(*data)
        
        if self.data['type'] == 'defrosting':
            return DefrostingItem(*data)
        
        if self.data['type'] == 'case':
            return CaseItem(*data)
        
        else:
            return ItemBase(*data)

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")