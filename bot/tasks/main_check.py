from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import DinoMood, Dino
from bot.models.enums import MoodType
from itertools import islice
from time import time
from random import choice, randint, random
import math
import asyncio

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.data_format import transform
from bot.models.dinosaur import Dino
from bot.modules.localization import get_data, get_lang, t
from bot.modules.get_state import get_state
from bot.taskmanager import add_task
from bot.models.dinosaur import Dino

from bot.exec import bot
from bot.modules.user.user import User
from bot.modules.logs import log

from bot.models.enums import DinoStatus

dinosaurs = LazyCollection(Dino)

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

async def kindergarten_check(dino, r):
    
    if random() <= P_EAT_SLEEP:
        r = await Dino.mutate_stat(dino, 'eat', randint(*EAT_CHANGE))

    if random() <= P_GAME:
        r = await Dino.mutate_stat(dino, 'game', randint(*GAME_CHANGE))

    if random() <= P_ENERGY:
        r = await Dino.mutate_stat(dino, 'energy', randint(*ENERGY_CHANGE))

    return r

async def main_checks_task(dinos):
    """Проверка динозавров для отдельного таска"""

    log(prefix='main_checks_task', message=f'Проверка динозавров: {len(dinos)}', lvl=0)
    time_start = time()

    for dino in dinos:
        r = 0

        status = await Dino.check_status_by_id(dino['_id'])
        if status == DinoStatus.INACTIVE:
            continue
        is_sleeping = status == DinoStatus.SLEEP
        skill_activ = status in [DinoStatus.GYM, DinoStatus.LIBRARY, DinoStatus.SWIMMING_POOL, DinoStatus.PARK]

        if dino['stats']['heal'] <= 0:
            dino_cl = await Dino().create(dino['_id'])
            if dino_cl: await dino_cl.dead()
            continue

        if status == DinoStatus.KINDERGARTEN: r = await kindergarten_check(dino, r)

        else:
            # Понижение здоровья
            # если здоровье и еда находятся на критическом уровне
            if dino['stats']['energy'] <= CRITICAL_ENERGY and random() <= P_HEAL:
                r = await Dino.mutate_stat(dino, 'heal', -1)

            elif dino['stats']['eat'] <= CRITICAL_EAT and random() <= P_HEAL:
                r = await Dino.mutate_stat(dino, 'heal', -1)

            elif is_sleeping and randint(0, 1):
                r = await Dino.mutate_stat(dino, 'heal', 1)

            # Уменьшение еды
            # если динозавр спит, вероятность P_EAT_SLEEP
            # если динозавр не спит, вероятность P_EAT
            if (random() <= P_EAT_SLEEP and is_sleeping) or (random() <= P_EAT and not is_sleeping):
                r = await Dino.mutate_stat(dino, 'eat', randint(*EAT_CHANGE)*-1)

            # Уменьшение энергии, если динозавр не играет
            if status != DinoStatus.GAME and random() <= P_GAME:
                r = await Dino.mutate_stat(dino, 'game', randint(*GAME_CHANGE)*-1)

            # Уменьшение энергии
            # если динозавр не спит
            if not(is_sleeping) and (random() <= P_ENERGY):
                r = await Dino.mutate_stat(dino, 'energy', randint(*ENERGY_CHANGE)*-1)


            # Во время тренировки более быстрое уменьшение еды и энергии
            if skill_activ and (random() <= P_ENERGY):
                r = await Dino.mutate_stat(dino, 'energy', -1)

            elif skill_activ and (random() <= P_EAT):
                r = await Dino.mutate_stat(dino, 'eat', -1)

            if randint(1, 5) == 5:
                owner_conn = await Dino.get_owner_by_id(dino['_id'])
                if owner_conn and owner_conn.owner:
                    user_obj = await owner_conn.owner.fetch()
                    if user_obj:
                        if await DinoMood.check_inspiration(dino['_id'], 'exp_boost'):
                            await user_obj.add_xp_lvl(randint(1, 4))
                        else:
                            await user_obj.add_xp_lvl(randint(1, 2))

        # условие выполнения для питания и восстановления здоровья
        # если динозавр не испытывает голод, не находится в критическом запасе энергии, настроение находится выше среднего
        if dino['stats']['eat'] > HIGH_EAT and dino['stats']['energy'] > 50:
            if random() <= P_HEAL_EAT:

                r = await Dino.mutate_stat(dino, 'heal', randint(1, 2))
                if randint(0, 1): 
                    r = await Dino.mutate_stat(dino, 'eat', -1)

        # =================== Настроение ========================== #

        # Если игры меньше 14, то накладывает условие на настроение
        # На настроение будет наложен эффект -1 пока настроение не поднимется до 35
        if dino['stats']['game'] <= 15:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'little_game', 'game', -1, 35, -1)

        # Если игры больше 84, то накладывается положительный эффект +1
        # Действует пока настроение не упадёт до 45
        elif dino['stats']['game'] >= 85:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'multi_games', 'game', 45, 101, 1)


        # Если еды меньше чем LOW_EAT, то накладывает эффект -1 к настроению
        if dino['stats']['eat'] <= LOW_EAT and dino['stats']['eat'] >= 5:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'little_eat', 'eat', 5, 50, -1)

        # Если еды меньше чем 5, то накладывает эффект -2 к настроению
        elif dino['stats']['eat'] < 5:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'little_eat', 'eat', -1, 20, -2)

        # Если еды у динозавра больше 84 то получает бонус к настроению +1 пока настроение не будет меньше 60-ти
        elif dino['stats']['eat'] >= 85:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'multi_eat', 'eat', 60, 101, 1)


        # Если энергии меньше 21-ти, понижает настроение на -1
        if dino['stats']['energy'] <= 20:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'little_energy', 
                              'energy', -1, 40, -1)

        # Если у динозавра много энергии то настроение +1
        elif dino['stats']['energy'] >= 85:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'multi_energy', 
                              'energy', 60, 101, 1)


        # Если здоровье меньше 21 то настроение -1
        if dino['stats']['heal'] <= 20:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'little_heal', 'heal', -1, 40, -1)

        elif dino['stats']['heal'] >= 85:
            if random() <= P_MOOD:
                await DinoMood.mood_while_if(dino['_id'], 'multi_heal', 'heal', 60, 101, 1)

        if status not in ['kindergarten', 'sleep']:
            if dino['stats']['mood'] >= 95:
                if randint(0, 5) == 3:
                    await DinoMood.calculation_points(dino, MoodType.INSPIRATION)
            elif dino['stats']['mood'] <= 5:
                if randint(0, 5) == 3:
                    await DinoMood.calculation_points(dino, MoodType.BREAKDOWN)

        # ========== Мысли вслух ========== # 
        if status == 'pass' and r == 0:
            chance = round(random(), 2) + transform(dino['stats']['charisma'], 20, 10) // 100
            if chance <= 0.05: # Шанс 5 процентов
                owner = await Dino.get_owner_by_id(dino['_id'])

                if owner:
                    user = await User().create(owner.owner_id)
                    if 'no_talk' in user.settings and user.settings['no_talk']:
                        continue

                    lang = await get_lang(owner.owner_id)
                    state = await get_state(user.userid, user.userid)

                    if state == None:
                        if not user.settings.get('my_name', False):
                            owner_name = t('owner', lang)
                        else: owner_name = user.settings['my_name']

                        text = choice(get_data('pass_messages', lang))
                        text = text.format(owner=owner_name)
                        try:
                            await bot.send_message(
                                owner.owner_id, f'🦕 {dino["name"]}: {text}'
                            )
                        except: pass
    
    log(prefix='main_checks_task', message=f'Конец проверки за {time() - time_start}', lvl=0)

async def main_checks():
    """Главная проверка динозавров"""
    dinos: list[dict] = await dinosaurs.find({}, comment='main_checks_dinos')
    num_tasks = 4  # Количество тасков

    tasks = [main_checks_task(chunk) for chunk in chunked(dinos, math.ceil(len(dinos) / num_tasks))]
    await asyncio.gather(*tasks)

def chunked(iterable, size):
    """Разделение списка на чанки фиксированного размера"""
    it = iter(iterable)
    return iter(lambda: list(islice(it, size)), [])

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(main_checks, REPEAT_MINUTS * 60.0, 5.0)