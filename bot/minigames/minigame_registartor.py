# from bot.minigames.minigame import MiniGame
from math import e
from bot.dbmanager import mongo_client
from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.taskmanager import add_task

minigames = DBconstructor(mongo_client.minigame.online)

class MiniGameRegistrator:
    def __init__(self):
        self.__base_session_objects = {}
        self.__minigames = {}

        self.trades_list = []

    def save_class_object(self, game_id: str, 
                          session_id: str, minigame):
        if game_id not in self.__base_session_objects:
            self.__base_session_objects[game_id] = {}
        self.__base_session_objects[game_id][session_id] = minigame

    def get_class_object(self, game_id: str, session_id: str):
        return self.__base_session_objects[game_id].get(
            session_id, None)

    def delete_class_object(self, game_id: str, session_id: str):
        if game_id not in self.__base_session_objects: return
        if session_id not in self.__base_session_objects[game_id]: return

        del self.__base_session_objects[game_id][session_id]

    def register_game(self, game):
        if game.GAME_ID in self.__minigames:
            raise ValueError(f"Game with ID {game.GAME_ID} is already registered. -> {self.__minigames}")

        self.__base_session_objects[game.GAME_ID] = {}
        self.__minigames[game.GAME_ID] = game

        log(f"Game with ID {game.GAME_ID} has been registered successfully.")

    def get_game(self, game_id: str):
        return self.__minigames.get(game_id, None)

    async def on_start(self):
        """ Функция срабатывает при старте бота и создаёт классы миниигр """

        sessions = await minigames.find({})

        for session in sessions:
            session_key = session['session_key']
            game_class = self.get_game(session['GAME_ID'])

            if game_class:
                try:
                    await game_class.ContinueGame(session_key)
                except Exception as e:
                    log(f"Error while continuing game {session_key}: {e}")

                self.save_class_object(session['GAME_ID'], session_key, game_class)

Registry = MiniGameRegistrator()
add_task(Registry.on_start, 0, 1.0)