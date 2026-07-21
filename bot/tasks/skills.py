from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import DinoMood, Dino
from bot.models.activity import Activity

from random import choice, randint, random, uniform
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.models.activity.training import TrainingActivity
from bot.models.dinosaur import Dino
from bot.models.activity import KDActivity
from bot.models.dinosaur import Dino
from bot.modules.items.item_tools import use_item
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_lang, t
from bot.modules.notifications import dino_notification
from bot.models.user import User
from bot.taskmanager import add_task
from bot.modules.logs import log

dinosaurs = LazyCollection(Dino)
long_activity = LazyCollection(Activity)


async def end_tranning(skill_activ, dino_id):
    # Завершаем тренировку с штрафом (половина от накопленного прогресса)
    unit_percent = skill_activ['up'] / 2
    await Dino.add_skill_point(dino_id, 
                            skill_activ['up_skill'], -unit_percent)

    await TrainingActivity.end(dino_id)
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
        sended = skill_activ.get('userid', 0)
        ahtung_lvl = skill_activ['ahtung_lvl']
        save = True

        if dino:
            # Если дино в тренировке — рассчитываем прирост навыков
            up_unit = uniform(*skill_activ['up_unit'])
            # sec_unit — прирост вторичного навыка (тоже положительный)
            sec_unit = uniform(*skill_activ['sec_unit'])

            # Проверяем, есть ли вдохновение
            insp = await DinoMood.check_inspiration(dino_id, skill_activ['activity_type'])

            if insp:
                # Вдохновение удваивает прирост обоих навыков
                up_unit *= 2
                sec_unit *= 2

            # Применяем бустер тренировки, если он активен
            boost = skill_activ.get('training_boost')
            if boost and boost.get('expires_at', 0) > int(time()):
                bonus = 1 + boost['bonus_percent']
                up_unit *= bonus
                sec_unit *= bonus

            # Добавляем прогресс обоих навыков
            await Dino.add_skill_point(dino_id, skill_activ['up_skill'], up_unit)
            await Dino.add_skill_point(dino_id, skill_activ['sec_skill'], sec_unit)

            # Проверяем, не пришло ли время завершать
            traning_time = int(time()) - skill_activ['start_time']

            dif_percent = (traning_time - skill_activ['max_time']) // (skill_activ['max_time'] // 100)

            if dif_percent > 0:
                # расчет штрафа за превышение времени
                # расчетаем сколько процентов времени мы превысили
                # и делим на 100, чтобы получить процент
                # например: 7200 - 5400 = 1800 // 540

                # Deterministic state progression / warnings
                if dif_percent >= 20 and skill_activ['ahtung_lvl'] == 0:
                    # ...повышается кд на 5 часов
                    ahtung_lvl = 1
                    await KDActivity.save_kd(dino_id, skill_activ['activity_type'], 3600 * 5)

                    lang = await get_lang(sended)
                    text = t('all_skills.overloading', lang, dino_name=dino.name)
                    try:
                        await bot.send_message(sended, text)
                    except: pass

                elif dif_percent >= 40 and skill_activ['ahtung_lvl'] == 1:
                    # ...иначе тренировка заканчивается
                    save = False
                    await end_tranning(skill_activ, dino_id)

                # Probabilistic stat/mood penalties (checked independently)
                if random() <= 0.1:
                    # 1/10 шанс, что дино будет
                    # наказано за превышение времени
                    await dino.update(
                        {'$inc': {
                            'stats.heal': -1
                        }}
                    )

                if random() <= 0.1:
                    # 1/10 шанс, что дино будет
                    # наказано за превышение времени
                    await DinoMood.add(dino._id, 'overloading', -1, 3600, True)

            if dino.stats['energy'] <= 30 or dino.stats['eat'] <= 15 and save:
                # Если дино голодно или слабо, то...
                send_status = False

                if skill_activ['use_energy'] and dino.stats['energy'] <= 30:
                    # ...можно использовать энергетики
                    energy_eat = get_group('energy_eat')
                    data_for_f = list(map(
                        lambda i: {'item_id': i}, energy_eat))

                    energy_items = await User.get_inventory_from_i(sended, data_for_f, 5)
                    if energy_items:
                        energy_item = choice(energy_items)

                        lang = await get_lang(sended)
                        send_status, return_text = await use_item(sended, sended, lang, 
                                    energy_item['item'], 1, dino)
                        if send_status:
                            return_text += t('all_skills.use_item', lang)
                            try:
                                await bot.send_message(sended, return_text)
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