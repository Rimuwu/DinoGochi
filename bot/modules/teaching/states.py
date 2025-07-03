
from aiogram.fsm.state import StatesGroup, State

class TeachingStates(StatesGroup):
    # Этап выбора яйца
    first_stage = State()
    # Начать играть - выбор яйца 

    # Первый этап обучения, яйца выбрана начата инкубация 
    # Кнопки для обучения: Динозавр, 
    second_stage = State()
    
    # Этап выбора фона
    third_stage = State()
    
    # Этап выбора имени питомца
    fourth_stage = State()
    
    # Этап выбора цвета питомца
    fifth_stage = State()
    
    # Этап выбора цвета фона
    sixth_stage = State()