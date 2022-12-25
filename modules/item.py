import json

from modules.localization import Localization
localization = Localization()

with open('json/items.json', encoding='utf-8') as f: items_data = json.load(f)['items']

class Item:

    def __init__(self, item_id:str | int = None, item_data:dict = None) -> None:
        ''' Создание объекта Item

            Получаем в класс либо id предмета, либо данные формата {"item_id": string(), *}
            Данные так же могу быть формата {"item_id": string(), "abilities": dict()}

            Пояснение:
              Стандартный предмет - предмет никак не изменённый пользователем, сгенерированный из базы.

              abilities - словарь индивидуальным харрактеристиками предмета, прочность, использования...

        '''

        if item_id: # Получаем стандартный предмет, если есть только id
            self.id = str(item_id)
            self.data = self.get_data()
            self.name = self.get_names()

        elif item_data: # Предмет от пользователя, есть id и возможно abilities
            ...
        else:
            raise Exception(f"An empty object cannot be created.")
    
    def __str__(self) -> str:
        return f"ItemObject {self.name}"

    def get_data(self = None, item_id:str = None) -> dict | None:
        if item_id == None: item_id = self.id 

        if item_id in items_data.keys():
            # Проверяем еть ли предмет с таким ключём в items.json
            return items_data[item_id]

        else: # Иначе вызываем ошибку 
            raise Exception(f"The subject with ID {self.id} does not exist.")
    
    def get_names(self) -> dict:
        """ Внесение всех имён в данные предмета
        """

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


    
    # def get_names(self = None, item_id:str = None) -> str:
    #     if item_id == None: item_id = self.id 
        
    #     data_items = items_f['items']
    #     item = data_items[item_id]

    #     if lg in item['name'].keys():
    #         return item['name'][lg]

    #     else:
    #         return item['name']['en']

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")