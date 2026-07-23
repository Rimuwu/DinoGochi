"""
Executor для автоматических действий динозавра.
Запускает действие без Telegram-интерфейса — только бизнес-логика.
"""
from bson import ObjectId
from bot.models.dinosaur import Dino
from bot.models.enums import DinoStatus
from bot.modules.logs import log
from bot.exec import bot
from bot.modules.localization import t


async def _send_auto_notify(userid: int, lang: str, text: str):
    footer = t('dino_auto_actions.auto_executed_footer', lang,
               default='\n\n⚙️ <i>Отправлено автоматически в соответствии с настройками</i>')
    full_text = f"{text}{footer}"
    try:
        await bot.send_message(userid, full_text)
    except Exception as e:
        log(f'[AutoActions] Не удалось отправить уведомление пользователю {userid}: {e}', lvl=2)


async def _check_free(dino: Dino) -> bool:
    st = await dino.check_status()
    return st == DinoStatus.PASS


async def execute_auto_action(action_cfg: dict, dino: Dino, userid: int, lang: str, auto_action_doc=None) -> bool:
    """
    Запускает автоматическое действие для дино.
    Возвращает True если действие запущено успешно.
    """
    action_type = action_cfg.get('type', '')
    try:
        if action_type == 'sleep':
            res = await _exec_sleep(action_cfg, dino, userid, lang, auto_action_doc)
        elif action_type == 'collecting':
            res = await _exec_collecting(action_cfg, dino, userid, lang)
        elif action_type == 'game':
            res = await _exec_game(action_cfg, dino, userid, lang)
        elif action_type == 'feed':
            res = await _exec_feed(action_cfg, dino, userid, lang)
        elif action_type in ('gym', 'library', 'park', 'swimming_pool'):
            res = await _exec_skill(action_type, dino, userid, lang, action_cfg)
        elif action_type in ('mine', 'bank', 'sawmill'):
            res = await _exec_work(action_cfg, action_type, dino, userid, lang)
        elif action_type == 'pet':
            res = await _exec_pet(dino, userid, lang)
        elif action_type == 'talk':
            res = await _exec_talk(dino, userid, lang)
        elif action_type == 'fighting':
            res = await _exec_fighting(dino, userid, lang)
        else:
            log(f'[AutoActions] Неизвестный тип действия: {action_type}', lvl=2)
            return False

        if res:
            act_title = t(f'dino_auto_actions.action.{action_type}', lang, default=action_type)
            msg = t('dino_auto_actions.notify_started', lang, name=dino.name, action=act_title,
                    default=f'🦕 <b>{dino.name}</b> — запущенно автодействие: <b>{act_title}</b>')
            await _send_auto_notify(userid, lang, msg)

        return res
    except Exception as e:
        log(f'[AutoActions] Ошибка при выполнении {action_type} для {dino.id}: {e}', lvl=3)
        return False


async def _exec_sleep(action_cfg: dict, dino: Dino, userid: int, lang: str, auto_action_doc=None) -> bool:
    from bot.models.activity import SleepActivity
    from bot.models.items import Item
    if not await _check_free(dino):
        return False
    sleep_type = action_cfg.get('sleep_type', 'long')
    duration = action_cfg.get('duration', 0)
    has_bear = await Item.check_accessory(dino, 'bear')
    if sleep_type == 'short' and not has_bear:
        sleep_type = 'long'
        action_cfg['sleep_type'] = 'long'
        if auto_action_doc and hasattr(auto_action_doc, 'save'):
            auto_action_doc.action['sleep_type'] = 'long'
            await auto_action_doc.save()
    if has_bear and sleep_type == 'short':
        await Item.check_accessory(dino, 'bear', True)
    return await SleepActivity.start(dino._id, sleep_type, duration)


async def _exec_collecting(action_cfg: dict, dino: Dino, userid: int, lang: str) -> bool:
    from bot.models.items import Item
    from bot.models.dinosaur import DinoMood
    if not await _check_free(dino):
        return False
    coll_type = action_cfg.get('coll_type', 'collecting')
    max_count = action_cfg.get('max_count', 10)
    from bot.modules.user.user import count_inventory_items, max_eat
    eat_count = await count_inventory_items(userid, ['eat'])
    max_c = await max_eat(userid)
    if eat_count + max_count > max_c:
        max_count = max(1, max_c - eat_count)
    if max_count <= 0:
        return False
    await dino.collecting(userid, coll_type, max_count)
    await Item.check_accessory(dino, 'basket', True)
    percent, _ = await dino.memory_percent('action', f'collecting.{coll_type}', True)
    await DinoMood.repeat_activity(dino._id, percent)
    return True


async def _exec_game(action_cfg: dict, dino: Dino, userid: int, lang: str) -> bool:
    from bot.models.activity import GameActivity
    import random
    if not await _check_free(dino):
        return False
    min_t = action_cfg.get('min_time', 30)
    max_t = action_cfg.get('max_time', 60)
    duration = random.randint(min_t, max_t) * 60
    return bool(await GameActivity.start(dino._id, duration))


async def _exec_feed(action_cfg: dict, dino: Dino, userid: int, lang: str) -> bool:
    from bot.modules.items.item_tools import use_item
    from bot.models.items import Item
    items = action_cfg.get('items', [])
    if not items:
        return False
    any_fed = False
    for item_cfg in items:
        item_id = item_cfg.get('item_id')
        count = item_cfg.get('count', 1)
        if not item_id:
            continue
        user_item = await Item.find_one({'owner_id': userid, 'items_data.item_id': item_id})
        if not user_item or user_item.count < count:
            continue
        send_status, _ = await use_item(userid, userid, lang, {'item_id': item_id}, count, dino)
        if send_status:
            any_fed = True
    return any_fed


async def _exec_skill(skill: str, dino: Dino, userid: int, lang: str, action_cfg: dict = None) -> bool:
    from bot.models.activity import KDActivity
    from bot.models.activity.training import TrainingActivity
    from bot.models.dinosaur import DinoMood
    from bot.const import GAME_SETTINGS
    if not await _check_free(dino):
        return False
    skills_data = GAME_SETTINGS['skills_data']
    if skill not in skills_data:
        return False
    kd = await KDActivity.check_activity(dino._id, skill)
    if kd:
        return False

    use_energy_items = action_cfg.get('use_energy_items', False) if action_cfg else False
    if use_energy_items and dino.stats.get('energy', 100) < 50:
        from bot.models.items import Item
        from bot.modules.items.item import get_data as get_item_data
        from bot.modules.items.item_tools import use_item

        all_user_items = await Item.find(Item.owner_id == userid).to_list()
        for itm in all_user_items:
            iid = itm.items_data.get('item_id', '')
            idata = get_item_data(iid)
            if idata and idata.get('type') == 'energy':
                await use_item(userid, userid, lang, {'item_id': iid}, 1, dino)
                break

    await KDActivity.save_kd(dino._id, skill, skills_data[skill]['kd'])
    percent, _ = await dino.memory_percent('action', skill, True)
    await DinoMood.repeat_activity(dino._id, percent)
    res = await TrainingActivity.start(
        dino._id, skill,
        *skills_data[skill]['skills'],
        *skills_data[skill]['units'], sended=userid,
        use_energy=use_energy_items
    )
    return bool(res)


async def _exec_work(action_cfg: dict, work_type: str, dino: Dino, userid: int, lang: str) -> bool:
    from bot.models.activity import WorkActivity
    from bot.models.dinosaur import DinoMood
    if not await _check_free(dino):
        return False
    target_option = action_cfg.get('target_option', '')
    if not target_option:
        return False
    percent, _ = await dino.memory_percent('action', work_type, True)
    await DinoMood.repeat_activity(dino._id, percent)
    if work_type == 'mine':
        await WorkActivity.start_mine(dino._id, userid, target_option)
    elif work_type == 'bank':
        await WorkActivity.start_bank(dino._id, userid, target_option)
    elif work_type == 'sawmill':
        await WorkActivity.start_sawmill(dino._id, userid, target_option)
    return True


async def _exec_pet(dino: Dino, userid: int, lang: str) -> bool:
    from bot.models.activity import KDActivity
    from bot.models.dinosaur import DinoMood
    from random import choice, randint, uniform
    kd = await KDActivity.check_activity(dino._id, 'pet')
    if kd:
        return False
    await DinoMood.add(dino._id, 'pet', 1, 600)
    await KDActivity.save_kd(dino._id, 'pet', 900)
    percent, _ = await dino.memory_percent('action', 'pet', True)
    await DinoMood.repeat_activity(dino._id, percent)
    lst_skills = ['power', 'dexterity', 'intelligence', 'charisma']
    await Dino.add_skill_point(dino._id, choice(lst_skills), -uniform(0.0001, 0.001))
    if randint(1, 4) == 2:
        res = await DinoMood.find_one(DinoMood.dino.id == dino.id, DinoMood.type == 'breakdown')
        if res:
            await res.delete()
            if res.action == 'hysteria':
                await dino.set_status(DinoStatus.PASS)
    return True


async def _exec_talk(dino: Dino, userid: int, lang: str) -> bool:
    from bot.models.activity import KDActivity
    from bot.models.dinosaur import DinoMood
    from random import uniform
    kd = await KDActivity.check_activity(dino._id, 'talk')
    if kd:
        return False
    percent, _ = await dino.memory_percent('action', 'talk', True)
    await DinoMood.repeat_activity(dino._id, percent)
    if uniform(1, 10) > 5 + 0.4 * dino.stats.get('charisma', 0):
        unit, key = -1, 'negative_talk'
    else:
        unit, key = 1, 'positive_talk'
    await DinoMood.add(dino._id, key, unit, 600)
    await KDActivity.save_kd(dino._id, 'talk', 900)
    await Dino.add_skill_point(dino._id, 'charisma', uniform(0.001, 0.01))
    return True


async def _exec_fighting(dino: Dino, userid: int, lang: str) -> bool:
    from bot.models.activity import KDActivity
    from bot.models.dinosaur import DinoMood
    from random import randint, uniform
    kd = await KDActivity.check_activity(dino._id, 'fighting')
    if kd:
        return False
    percent, _ = await dino.memory_percent('action', 'fighting', True)
    await DinoMood.repeat_activity(dino._id, percent)
    await KDActivity.save_kd(dino._id, 'fighting', 2400)
    dex_ok = uniform(1, 10) < 4 + 0.4 * dino.stats.get('dexterity', 0)
    blk_ok = not dex_ok and uniform(1, 10) < 4 + 0.4 * dino.stats.get('power', 0)
    if not dex_ok and not blk_ok:
        heal = randint(1, 5)
        await DinoMood.add(dino._id, 'break', -1, 1200)
        await Dino.add_skill_point(dino._id, 'power', uniform(0.001, 0.01))
        await Dino.mutate_stat(dino, 'heal', -heal)
    elif dex_ok:
        await Dino.add_skill_point(dino._id, 'dexterity', uniform(0.001, 0.01))
    else:
        await Dino.add_skill_point(dino._id, 'power', uniform(0.001, 0.01))
    return True
