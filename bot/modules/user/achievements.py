


from typing import Any, Union
from bot.const import ACHIEVEMENTS
from bot.dbmanager import mongo_client

user_achievements = mongo_client.user.achievements

# Есть разные типы достижений
# 1. Просто получить. Выдаются разово. Например получил 10 уровень.
# 2. С прогрессом. То есть мы храним либо число в базе и сверяемся с функцией првоерки прогресса, либо список с например съеденными предметами.
# 3. Плавающие. Например первое место в рейтинге / первый по уровню. Может быть потеряно.

def get_achievement(achievement_type: str) -> dict:

    ach_data = {
        "type": "", # Тип достижения. Может быть: 'simple' - простое достижение, 'progress' - с прогрессом, 'floating' - плавающее достижение
        "name": "", # Название достижения (для профиля)
        "title": "", # Титул, который можно получить за достижение
        "description": "", # Описание при получении
        "short_description": "", # Краткое описание в профиле

        "secret": False, # Если True то не будет учитываться при подсчёте прогресса (описание)
        "first_user": False, # Если True то получит только первый пользователь
        "stack": False, # Если True то будет стакаться (то есть будет что то х21)

        "award": {
            "money": 0, # Количество денег
            "exp": 0, # Количество опыта
            "items": [] # Предметы формата {'itemid': 1, 'count': 1, 'abilities': {} }
        },
        "progress_check": "" # Функция для проверки прогресса, если не указана то просто получит при получении
    }

    ach_data.update(
        ACHIEVEMENTS['achievements'].get(achievement_type, {})
    )
    return ach_data

async def create_simple_data(userid: int,
                             achievement_type: str):
    
    base_data = get_achievement(achievement_type)
    data = {
        'user_id': userid,
        'achievement_type': achievement_type
    }

    if base_data['stack']: data['stack'] = 1

    await user_achievements.insert_one(data)
    

async def create_floating_data(userid: int,
                               achievement_type: str,
                               data: Any
                               ):

    data = {
        'user_id': userid,
        'achievement_type': achievement_type,
        'data': data
    }

    await user_achievements.insert_one(data)

async def create_progress_data(userid: int,
                               achievement_type: str,
                               progress: Union[list, int]
                               ):

    data = {
        'user_id': userid,
        'achievement_type': achievement_type,
        'progress': progress
    }

    await user_achievements.insert_one(data)


async def check_first_user(achievement_type: str) -> bool:
    """ Отвечает на вопрос, можно ли добавить достижение или оно уже занято.
    """

    res = await user_achievements.find_one(
        { "achievement_type": achievement_type }
    )
    return res is not None

async def check_stack_status(achievement_type: str, 
                             userid: int) -> bool:
    """ 
        True - Если нет достижения и любой stack
        True - Если есть достижение и stack = True
        False - Если есть достижение и stack = False
    """

    res = await user_achievements.find_one(
        { "achievement_type": achievement_type,
          "user_id": userid 
        }
    )

    if not res: return True
    data = get_achievement(achievement_type)

    if data['stack']:
        return True
    return False

async def get_achievement_base(userid: int, achievement_type: str) -> dict | None:
    """ Получить данные о достижении пользователя """

    return await user_achievements.find_one(
        { "user_id": userid, "achievement_type": achievement_type }
    )

async def add_achievement(userid: int, achievement_type: str, 
                        data: Any = None):
    ach_data = get_achievement(achievement_type)
    add_reward = False

    if ach_data:
        stack_status = await check_stack_status(
            achievement_type, userid
            )
        first_user_status = ach_data['first_user']
        add_st = [stack_status]

        if first_user_status:
            add_st.append(
                await check_first_user(achievement_type)
            )

        if all(add_st):
            in_base_data = await get_achievement_base(
                userid, achievement_type)

            if ach_data['type'] == 'simple':

                if in_base_data:
                    if ach_data['stack']:

                        await user_achievements.update_one(
                            { '_id': in_base_data['_id'] },
                            { "$inc": {'stack': 1} }
                        )

                else:
                    add_reward = True
                    await create_simple_data(userid, achievement_type)

            elif ach_data['type'] == 'floating':
                # Не стакается
                # Всегда first_user=True

                if isinstance(data, int) and isinstance(data, int):

                    if in_base_data:
                        if data >= in_base_data['data']:

                            await user_achievements.delete_one(
                                {'_id': in_base_data['_id']}
                            )

                            await create_floating_data(userid, 
                                                       achievement_type, data)

            elif ach_data['progress'] == 'progress':
                
                # Не стакается 
                # Если нет, то создаём данные 
                # Если да, то добавляет данные
                # Если чекер выводит True то ничего не делает
                
                func_checker = 
                

        if add_reward:
            ...



# ================ Checkers ================ #

# Асинхроные функции в формате key: str и value: callable
checkers = {
    
}

async def ach_progress_goal(userid: int, achievement_type: str, 
                            data: Union[list, int]) -> bool:
    """ Отвечает на вопрос, выполнены ли условия достижения"""
    