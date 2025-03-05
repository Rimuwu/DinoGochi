# from bot.minigames.minigame import MiniGame
from bot.dbmanager import mongo_client
from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.taskmanager import add_task

minigames = DBconstructor(mongo_client.minigames.online)

class MiniGameRegistrator:
    def __init__(self):
        self.__base_session_objects = {}
        self.__minigames = {}

    def save_class_object(self, game_id: str, 
                          session_id: str, minigame):
        self.__base_session_objects[game_id][session_id] = minigame

    def get_class_object(self, game_id: str, session_id: str):
        return self.__base_session_objects[game_id].get(
            session_id, None)

    def register_game(self, game):
        self.__base_session_objects[game.GAME_ID] = {}
        self.__minigames[game.GAME_ID] = game
    
    def get_game(self, game_id: str):
        return self.__minigames.get(game_id, None)

    async def on_start(self):
        """ Функция срабатывает при старте бота и создаёт классы миниигр """

        sessions = await minigames.find({})

        for session in sessions:
            session_key = session['session_key']
            game_class = self.get_game(session['GAME_ID'])

            if game_class:
                await game_class.ContinueGame(session_key)
                self.save_class_object(session['GAME_ID'], session_key, game_class)

Registry = MiniGameRegistrator()
add_task(Registry.on_start, 0, 5.0)