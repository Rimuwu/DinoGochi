from pprint import pprint

import config
dinosaurs = config.CLUSTER_CLIENT.bot.dinosaurs

class Dino:

    def __init__(self, baseid) -> None:
        self.id = baseid
        self.data = dinosaurs.find_one({"_id": self.id})
    
    def __str__(self) -> str:
        return f"DinoObj {self.data['name']}"


    def view(self):
        print('DATA: ', end='')
        pprint(self.data)