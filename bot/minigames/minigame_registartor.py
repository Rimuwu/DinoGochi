# from bot.minigames.minigame import MiniGame

class MiniGameRegistrator:
    def __init__(self):
        self.__base_session_objects = {}

    def save_class_object(self, game_id: str, 
                          session_id: str, minigame):
        self.__base_session_objects[game_id][session_id] = minigame

    def get_class_object(self, game_id: str, session_id: str):
        return self.__base_session_objects[game_id].get(
            session_id, None)

    def register_game(self, game):
        self.__base_session_objects[game.GAME_ID] = {}


Registry = MiniGameRegistrator()
