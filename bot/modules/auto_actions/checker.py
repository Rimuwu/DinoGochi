"""
Хук вызываемый после окончания любой активности динозавра.
Проверяет отложенные действия и conditional с триггером activity_end.
"""
import time
from bson import ObjectId
from bot.modules.logs import log


async def on_activity_end(dino_id: ObjectId, owner_id: int):
    """
    Вызывается в конце каждой активности.
    - Выполняет deferred действие если есть.
    - Выполняет conditional действие с condition.stat == 'activity_end' если есть.
    """
    try:
        from bot.models.dinosaur import DinoAutoAction, Dino
        from bot.modules.auto_actions.executor import execute_auto_action
        from bot.modules.localization import get_lang

        dino = await Dino.find_one(Dino.id == dino_id)
        if not dino:
            return

        lang = await Dino.get_language(dino_id)

        # --- Отложенное действие ---
        deferred = await DinoAutoAction.get_deferred(dino_id)
        if deferred and deferred.enabled:
            if deferred.skip_once:
                deferred.skip_once = False
                await deferred.save()
            else:
                ok = await execute_auto_action(deferred.action, dino, owner_id, lang, auto_action_doc=deferred)
                if ok:
                    log(f'[AutoActions] deferred выполнено для {dino_id}: {deferred.action}', lvl=0)
                # Отложенное — одноразовое, удаляем после попытки выполнения
                await deferred.delete()

        # --- Conditional action_end ---
        cond_actions = await DinoAutoAction.get_for_dino(dino_id, 'conditional')
        from bot.const import GAME_SETTINGS
        cooldown = GAME_SETTINGS.get('auto_actions', {}).get('conditional_cooldown_seconds', 43200)
        now = int(time.time())
        for cond in cond_actions:
            if not cond.enabled:
                continue
            if cond.condition and cond.condition.get('stat') != 'activity_end':
                continue
            if cond.last_triggered and (now - cond.last_triggered) < cooldown:
                continue
            if cond.skip_once:
                cond.skip_once = False
                await cond.save()
                continue
            ok = await execute_auto_action(cond.action, dino, owner_id, lang, auto_action_doc=cond)

            if ok:
                cond.last_triggered = now
                await cond.save()
                log(f'[AutoActions] conditional(activity_end) выполнено для {dino_id}', lvl=0)
    except Exception as e:
        log(f'[AutoActions] on_activity_end error dino={dino_id}: {e}', lvl=3)
