import random
from random import randint

from bot.config import conf, mongo_client
from bot.modules.dinosaur import mutate_dino_stat
from bot.taskmanager import add_task
from bot.modules.dinosaur import Dino, get_owner
from bot.modules.mood import mood_while_if, calculation_points
from bot.modules.user import experience_enhancement

from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

# Переменные изменения харрактеристик
HEAL_CHANGE = 1, 2
EAT_CHANGE = 1, 2
GAME_CHANGE = 1, 2
ENERGY_CHANGE = 1, 2
MOOD_CHANGE = 1, 2

# Переменные порогов
CRITICAL_ENERGY = 10
CRITICAL_EAT = 20
HIGH_EAT = 80
LOW_EAT = 20
HIGH_MOOD = 50

REPEAT_MINUTS = 4

# Переменные вероятности
P_HEAL = 0.03 * REPEAT_MINUTS
P_EAT = 0.045 * REPEAT_MINUTS
P_EAT_SLEEP = 0.035 * REPEAT_MINUTS
P_GAME = 0.1 * REPEAT_MINUTS
P_ENERGY = 0.05 * REPEAT_MINUTS
P_MOOD = 0.2 * REPEAT_MINUTS
P_HEAL_EAT = 0.1 * REPEAT_MINUTS
EVENT_CHANCE = 0.05 * REPEAT_MINUTS

async def main_checks():
    """Главная проверка динозавров
    """

    dinos = await dinosaurs.find({}, comment='main_checks_dinos')
    for dino in dinos:
        dino: dict
        if dino['status'] == 'inactive': continue
        is_sleeping = dino['status'] == 'sleep'

        if dino['stats']['heal'] <= 0:
            dino_cl = await Dino().create(dino['_id'])
            await dino_cl.dead()
            continue

        if dino['status'] == 'kindergarten':
            if random.uniform(0, 1) <= P_EAT_SLEEP:
                await mutate_dino_stat(dino, 'eat', randint(*EAT_CHANGE))

            if random.uniform(0, 1) <= P_GAME:
                await mutate_dino_stat(dino, 'game', randint(*GAME_CHANGE))

            if random.uniform(0, 1) <= P_ENERGY:
                await mutate_dino_stat(dino, 'energy', randint(*ENERGY_CHANGE))

        else:
            # Понижение здоровья
            # если здоровье и еда находятся на критическом уровне
            if dino['stats']['energy'] <= CRITICAL_ENERGY and random.uniform(0, 1) <= P_HEAL:
                await mutate_dino_stat(dino, 'heal', -1)

            elif dino['stats']['eat'] <= CRITICAL_EAT and random.uniform(0, 1) <= P_HEAL:
                await mutate_dino_stat(dino, 'heal', -1)

            elif is_sleeping and randint(0, 1):
                await mutate_dino_stat(dino, 'heal', 1)

            # Уменьшение еды
            # если динозавр спит, вероятность P_EAT_SLEEP
            # если динозавр не спит, вероятность P_EAT
            if (random.uniform(0, 1) <= P_EAT_SLEEP and is_sleeping) or (random.uniform(0, 1) <= P_EAT and not is_sleeping):
                await mutate_dino_stat(dino, 'eat', randint(*EAT_CHANGE)*-1)

            # Уменьшение энергии, если динозавр не играет
            if dino['status'] != 'game' and random.uniform(0, 1) <= P_GAME:
                await mutate_dino_stat(dino, 'game', randint(*GAME_CHANGE)*-1)

            # Уменьшение энергии
            # если динозавр не спит
            if not(is_sleeping) and (random.uniform(0, 1) <= P_ENERGY):
                await mutate_dino_stat(dino, 'energy', randint(*ENERGY_CHANGE)*-1)

            if randint(1, 5) == 5:
                owner = await get_owner(dino['_id'])
                if owner:
                    await experience_enhancement(owner['owner_id'], randint(1, 2))

        # условие выполнения для питания и восстановления здоровья
        # если динозавр не испытывает голод, не находится в критическом запасе энергии, настроение находится выше среднего
        if dino['stats']['eat'] > HIGH_EAT and dino['stats']['energy'] > 50:
            if random.uniform(0, 1) <= P_HEAL_EAT:

                await mutate_dino_stat(dino, 'heal', randint(1, 2))
                if randint(0, 1): await mutate_dino_stat(dino, 'eat', -1)

        # =================== Настроение ========================== #

        # Если игры меньше 14, то накладывает условие на настроение
        # На настроение будет наложен эффект -1 пока настроение не поднимется до 35
        if dino['stats']['game'] <= 15:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'little_game', 'game', -1, 35, -1)

        # Если игры больше 84, то накладывается положительный эффект +1
        # Действует пока настроение не упадёт до 45
        elif dino['stats']['game'] >= 85:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'multi_games', 'game', 45, 101, 1)


        # Если еды меньше чем LOW_EAT, то накладывает эффект -1 к настроению
        if dino['stats']['eat'] <= LOW_EAT and dino['stats']['eat'] >= 5:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'little_eat', 'eat', 5, 50, -1)

        # Если еды меньше чем 5, то накладывает эффект -2 к настроению
        elif dino['stats']['eat'] < 5:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'little_eat', 'eat', -1, 20, -2)

        # Если еды у динозавра больше 84 то получает бонус к настроению +1 пока настроение не будет меньше 60-ти
        elif dino['stats']['eat'] >= 85:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'multi_eat', 'eat', 60, 101, 1)


        # Если энергии меньше 21-ти, понижает настроение на -1
        if dino['stats']['energy'] <= 20:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'little_energy', 
                              'energy', -1, 40, -1)

        # Если у динозавра много энергии то настроение +1
        elif dino['stats']['energy'] >= 85:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'multi_energy', 
                              'energy', 60, 101, 1)


        # Если здоровье меньше 21 то настроение -1
        if dino['stats']['heal'] <= 20:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'little_heal', 'heal', -1, 40, -1)

        elif dino['stats']['heal'] >= 85:
            if random.uniform(0, 1) <= P_MOOD:
                await mood_while_if(dino['_id'], 'multi_heal', 'heal', 60, 101, 1)

        if dino['status'] not in ['kindergarten', 'sleep']:
            if dino['stats']['mood'] >= 95:
                if random.randint(0, 5) == 3:
                    await calculation_points(dino, 'inspiration')
            elif dino['stats']['mood'] <= 5:
                if random.randint(0, 5) == 3:
                    await calculation_points(dino, 'breakdown')

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(main_checks, REPEAT_MINUTS * 60.0, 5.0)