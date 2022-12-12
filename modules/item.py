import json

with open('json/items.json', encoding='utf-8') as f: items_data = json.load(f)['items']

class Item:

    def __init__(self, item_id:str | int = None, item_data:dict = None) -> None:
        ''' Создание объекта Item

            Получаем в класс либо id предмета, либо данные формата {"item_id": string(), *}
            Данные так же могу быть формата {"item_id": string(), "abilities": dict()}

            Пояснение:
              Стандартный предмет - предмет никак не изменённый пользователем, сгенерированный из 

              abilities - словарь индивидуальным харрактеристиками предмета, прочность, использования...

        '''

        if item_id: # Получаем стандартный предмет, если есть только id
            self.id = str(item_id)
            self.data = self.get_data()
        elif item_data: # Предмет от пользователя, есть id и возможно abilities
            ...
        else:
            raise Exception(f"An empty object cannot be created.")
    
    def __str__(self) -> str:
        pass

    def get_data(self = None, item_id:str = None) -> dict | None:
        if item_id == None: item_id = self.id 

        if item_id in items_data.keys():
            # Проверяем еть ли предмет с таким ключём в items.json
            return items_data[item_id]

        else: # Иначе вызываем ошибку 
            raise Exception(f"The subject with ID {self.id} does not exist.")
    
    # def get_name(self = None, item_id:str = None) -> str:
    #     if item_id == None: item_id = self.id 
        
    #     data_items = items_f['items']
    #     item = data_items[item_id]

    #     if lg in item['name'].keys():
    #         return item['name'][lg]

    #     else:
    #         return item['name']['en']

if __name__ == '__main__':
    raise Exception("This file cannot be launched on its own!")