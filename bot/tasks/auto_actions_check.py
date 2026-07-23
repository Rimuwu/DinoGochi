"""
Периодическая задача: проверка scheduled и conditional автодействий.
Запускается раз в минуту.
"""
import time
from bot.modules.logs import log


async def check_scheduled_actions():
    """Проверяет действия по расписанию для всех динозавров."""
    try:
        from bot.models.dinosaur import DinoAutoAction, Dino
        from bot.modules.auto_actions.executor import execute_auto_action
        from bot.const import GAME_SETTINGS
        import datetime

        all_scheduled = await DinoAutoAction.find(
            DinoAutoAction.action_type == 'scheduled',
            DinoAutoAction.enabled == True
        ).to_list()

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        for action in all_scheduled:
            try:
                if not action.schedule_time:
                    continue
                tz_offset = action.schedule_time.get('tz_offset', 0)
                target_hour = action.schedule_time.get('hour', 0)
                target_minute = action.schedule_time.get('minute', 0)

                # Время пользователя
                user_now = now_utc + datetime.timedelta(hours=tz_offset)
                cur_h, cur_m = user_now.hour, user_now.minute

                if cur_h != target_hour or cur_m != target_minute:
                    continue

                # Проверяем не выполнялось ли уже сегодня
                if action.last_triggered:
                    last_dt = datetime.datetime.fromtimestamp(
                        action.last_triggered, tz=datetime.timezone.utc
                    ) + datetime.timedelta(hours=tz_offset)
                    if last_dt.date() == user_now.date():
                        continue  # Уже выполнялось сегодня

                if action.skip_once:
                    action.skip_once = False
                    await action.save()
                    continue

                dino = await Dino.find_one(Dino.id == action.dino_id)
                if not dino:
                    continue

                lang = await Dino.get_language(action.dino_id)
                from bot.models.enums import DinoStatus
                st = await dino.check_status()
                if st == DinoStatus.INACTIVE:
                    await DinoAutoAction.delete_all_for_dino(dino.id)
                    continue
                elif st != DinoStatus.PASS:
                    # Дино занят — ставим в отложенное
                    await DinoAutoAction.upsert_deferred(
                        action.dino_id, action.owner_id, action.action
                    )
                    log(f'[AutoActions] scheduled: дино занят, отложено для {action.dino_id}', lvl=0)
                    continue


                ok = await execute_auto_action(action.action, dino, action.owner_id, lang, auto_action_doc=action)

                if ok:
                    action.last_triggered = int(time.time())
                    await action.save()
                    log(f'[AutoActions] scheduled выполнено для {action.dino_id}', lvl=0)
            except Exception as e:
                log(f'[AutoActions] check_scheduled error for {action.dino_id}: {e}', lvl=3)
    except Exception as e:
        log(f'[AutoActions] check_scheduled_actions error: {e}', lvl=3)


async def check_conditional_actions():
    """Проверяет conditional действия по статам для всех динозавров."""
    try:
        from bot.models.dinosaur import DinoAutoAction, Dino
        from bot.modules.auto_actions.executor import execute_auto_action
        from bot.const import GAME_SETTINGS
        from bot.models.enums import DinoStatus

        cooldown = GAME_SETTINGS.get('auto_actions', {}).get('conditional_cooldown_seconds', 43200)
        now = int(time.time())

        all_conditional = await DinoAutoAction.find(
            DinoAutoAction.action_type == 'conditional',
            DinoAutoAction.enabled == True
        ).to_list()

        for action in all_conditional:
            try:
                if not action.condition:
                    continue
                stat = action.condition.get('stat', '')
                if stat == 'activity_end':
                    continue  # Обрабатывается через on_activity_end hook

                # Cooldown
                if action.last_triggered and (now - action.last_triggered) < cooldown:
                    continue

                dino = await Dino.find_one(Dino.id == action.dino_id)
                if not dino:
                    continue

                # Проверяем условие
                threshold = action.condition.get('threshold', 0)
                op = action.condition.get('op', '<=')
                stat_val = dino.stats.get(stat)
                if stat_val is None:
                    continue

                triggered = False
                if op == '<=' and stat_val <= threshold:
                    triggered = True
                elif op == '<' and stat_val < threshold:
                    triggered = True
                elif op == '>=' and stat_val >= threshold:
                    triggered = True
                elif op == '==' and stat_val == threshold:
                    triggered = True

                if not triggered:
                    continue

                if action.skip_once:
                    action.skip_once = False
                    await action.save()
                    continue

                st = await dino.check_status()
                if st == DinoStatus.INACTIVE:
                    await DinoAutoAction.delete_all_for_dino(dino.id)
                    continue
                elif st != DinoStatus.PASS:
                    # Дино занят — ставим в отложенное
                    await DinoAutoAction.upsert_deferred(
                        action.dino_id, action.owner_id, action.action
                    )
                    log(f'[AutoActions] conditional: дино занят, отложено для {action.dino_id}', lvl=0)
                    continue


                lang = await Dino.get_language(action.dino_id)
                ok = await execute_auto_action(action.action, dino, action.owner_id, lang, auto_action_doc=action)

                if ok:
                    action.last_triggered = now
                    await action.save()
                    log(f'[AutoActions] conditional выполнено для {action.dino_id} ({stat}<={threshold})', lvl=0)
            except Exception as e:
                log(f'[AutoActions] check_conditional error for {action.dino_id}: {e}', lvl=3)
    except Exception as e:
        log(f'[AutoActions] check_conditional_actions error: {e}', lvl=3)


# Регистрируем задачи
from bot.config import conf
if __name__ != '__main__':
    if conf.active_tasks:
        from bot.taskmanager import add_task
        add_task(check_scheduled_actions, 60.0, 5.0)
        add_task(check_conditional_actions, 60.0, 10.0)
