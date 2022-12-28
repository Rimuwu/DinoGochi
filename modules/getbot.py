bot = None

class BotObj:
    def __init__(self) -> None:
        """Класс для сохранения объекта бота и получения его откуда угодно."""
        
    def set_bot(bot_obj) -> None:
        """Сохраняет объект бота в глобальную переменную для дальнейшего получения."""
        global bot
        bot = bot_obj
    
    def get_bot(): 
        """Возвращает объект бота."""
        return bot