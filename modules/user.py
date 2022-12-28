import config
from modules.getbot import BotObj
from modules.dinosaur import Dino
from modules.item import CreateItem

users = config.CLUSTER_CLIENT.bot.users

class User:

    def __init__(self, userid: int, telegram: bool = True) -> None:
        """Создание объекта пользователя
           telegram = True - надо ли запрашивать данные из телеги.
        """

        self.id = userid
        self.data = users.find_one({"userid": self.id})
        self.dinos = self.get_dinos()
        self.inventory = self.generate_inventory()

        if telegram:
            self.telegram_data = BotObj.get_bot().get_chat(self.id)
        else:
            self.telegram_data = None
    
    def get_dinos(self) -> list:
        """Возвращает список с объектами динозавров."""
        dino_list = []

        for dino_obj in self.data['dinos']:
            dino_list.append(Dino(dino_obj))

        return dino_list
    
    def generate_inventory(self) -> list:
        inv = []
        for item_dict in self.data['inventory']:
            inv.append(CreateItem(item_data=item_dict).new())
        
        return inv

    
    def view(self) -> None:
        """ Отображает все данные объекта."""

        print(f'ID: {self.id}')
        print(f'DATA: {self.data}')
        print(f'dino_len: {len(self.dinos)}')