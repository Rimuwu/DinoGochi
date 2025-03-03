
from random import choice, randint, random, uniform
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.dinosaur.dino_status import end_skill_activity
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.mood import add_mood, check_inspiration
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.items.item_tools import use_item
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang, t
from bot.modules.notifications import dino_notification
from bot.modules.user.user import get_inventory_from_i
from bot.taskmanager import add_task
from bot.modules.logs import log

from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)


async def end_tranning(skill_activ, dino_id):
    # Завершаем тренировку 
    unit_percent = skill_activ['up'] / 2
    await add_skill_point(dino_id, 
                            skill_activ['up_skill'], -unit_percent)

    await end_skill_activity(dino_id)
    await dino_notification(dino_id,
                            skill_activ['activity_type'] + '_end_negative', 
                            add_unit=round(unit_percent, 4))

async def skills_work():
    res_list = await long_activity.find(
        {'activity_type': {'$in': ['gym', 'library', 'swimming_pool', 'park']},
         'last_check': {'$lte': int(time()) - 600}
         }
    )

    for skill_activ in res_list:
        dino = await Dino().create(skill_activ['dino_id'])
        dino_id = skill_activ['dino_id']
        sended = skill_activ['send']
        ahtung_lvl = skill_activ['ahtung_lvl']
        save = True

        if dino:
            # Если дино в тренировке
            up_unit = uniform(*skill_activ['up_unit'])
            down_unit = uniform(*skill_activ['down_unit'])

            # Проверяем, есть ли вдохновение
            insp = await check_inspiration(dino_id, skill_activ['activity_type'])

            if insp:
                # Если есть вдохновение, то умножаем
                up_unit *= 2
                down_unit *= 2

            # Добавляем / уменьшаем скилы
            await add_skill_point(dino_id, skill_activ['up_skill'], up_unit)
            await add_skill_point(dino_id, skill_activ['down_skill'], down_unit)

            # Проверяем, не пришло ли время
            traning_time = int(time()) - skill_activ['start_time']

            dif_percent = (traning_time - skill_activ['max_time']) // (skill_activ['max_time'] // 100)

            if dif_percent > 0:
                # расчет штрафа за превышение времени
                # расчетаем сколько процентов времени мы превысили
                # и делим на 100, чтобы получить процент
                # например: 7200 - 5400 = 1800 // 540

                if random() <= 0.2:
                    # 1/5 шанс, что дино будет
                    # наказано за превышение времени
                    if dif_percent >= 20 and skill_activ['ahtung_lvl'] == 0:
                        # ...повышается кд на 5 часов
                        ahtung_lvl = 1
                        await save_kd(dino_id, skill_activ['activity_type'], 3600 * 5)

                        lang = await get_lang(sended)
                        text = t('all_skills.overloading', lang, dino_name=dino.name)
                        try:
                            await bot.send_message(sended, text)
                        except: pass

                    elif dif_percent >= 40 and skill_activ['ahtung_lvl'] == 1:
                        # ...иначе тренировка заканчивается
                        save = False
                        await end_tranning(skill_activ, dino_id)

                elif random() <= 0.1:
                    # 1/10 шанс, что дино будет
                    # наказано за превышение времени
                    await dino.update(
                        {'$inc': {
                            'stats.heal': -1
                        }}
                    )

                elif random() <= 0.1:
                    # 1/10 шанс, что дино будет
                    # наказано за превышение времени
                    await add_mood(dino._id, 'overloading', -1, 3600, True)

            if dino.stats['energy'] <= 30 or dino.stats['eat'] <= 15 and save:
                # Если дино голодно или слабо, то...
                send_status = False

                if skill_activ['use_energy'] and dino.stats['energy'] <= 30:
                    # ...можно использовать энергетики
                    energy_eat = get_group('energy_eat')
                    data_for_f = list(map(
                        lambda i: {'item_id': i}, energy_eat))

                    energy_items = await get_inventory_from_i(sended, data_for_f, 5)
                    if energy_items:
                        energy_item = choice(energy_items)

                        lang = await get_lang(sended)
                        send_status, return_text = await use_item(sended, sended, lang, 
                                    energy_item['item'], 1, dino)
                        if send_status:
                            return_text += t('all_skills.use_item', lang)
                            try:
                                await bot.send_message(sended, return_text, parse_mode='Markdown')
                            except: pass

                if not send_status and (dino.stats['energy'] <= 30 or dino.stats['eat'] <= 15):
                    # ...иначе тренировка заканчивается
                    await end_tranning(skill_activ, dino_id)

            if save:
                # Если тренировка не закончилась, то...
                await long_activity.update_one({'_id': skill_activ['_id']}, {
                    '$set': {
                        'last_check': int(time()),
                        'ahtung_lvl': ahtung_lvl
                        },
                    '$inc': {
                        'up': up_unit
                    }
                })

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(skills_work, 300.0, 10.0)