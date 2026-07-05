# -*- coding: utf-8 -*-
import random
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from bot.modules.items.item import get_data, get_item_level
from bot.modules.localization import t, get_data as get_loc_data
from bot.modules.data_format import deepcopy

# =====================================================================
# ДОКУМЕНТАЦИЯ СВОЙСТВ И ПОВЫШЕНИЯ УРОВНЕЙ (Пример конфигурации в JSON)
# =====================================================================
"""
Пример описания предмета с боевыми свойствами и масштабированием уровня в JSON (dungeon.json):

{
    "bone_sword": {
        "type": "weapon",
        "rank": "uncommon",
        "endurance_max": 50,
        "damage": {
            "min": 1,
            "max": 3
        },
        "abilities": {
            "endurance": 50
        },
        
        # 1. Описание боевых свойств по умолчанию (уровень 0)
        "properties": {
            "stun_strike": {
                "name": "combat_properties.names.stun_strike",  # Ключ локализации для названия свойства
                "type": "apply_effect_enemy",
                "points_cost": 1,
                "cooldown": 2,
                "energy_cost": 10,
                "base_chance": 0.2,
                "stat_scale": {
                    "stat": "dexterity",
                    "multiplier": 0.015
                },
                "params": {
                    "effect_type": "stun",
                    "duration": 1
                },
                # Динамическое увеличение параметров при росте уровня:
                # final_value = base_value + lvl * scale_value
                "lvl_scale": {
                    "base_chance": 0.03,
                    "params": {
                        "duration": 0.2
                    }
                }
            }
        },

        # 2. Повышение уровней и переопределение характеристик / свойств
        "lvls": {
            "1": {
                "endurance_max": 75,
                "damage": {"min": 2, "max": 5}
                # Здесь можно переопределить свойства на 1-м уровне, если не хватает lvl_scale:
                # "properties": {
                #     "stun_strike": {
                #         "base_chance": 0.35
                #     }
                # }
            },
            "2": {
                "endurance_max": 112,
                "damage": {"min": 3, "max": 7}
            }
        }
    }
}

Принцип масштабирования свойств:
- Берется базовый объект свойства из "properties".
- Если у свойства задан словарь "lvl_scale", все числовые параметры умножаются на уровень предмета
  по формуле: `значение = базовое_значение + (уровень * коэффициент_lvl_scale)`.
- Если на конкретном уровне (внутри "lvls.[уровень].properties") явно заданы перегрузки параметров, 
  они накладываются поверх динамического масштабирования, переопределяя конечные значения.
"""

# =====================================================================
# СХЕМЫ И МОДЕЛИ ВАЛИДАЦИИ (Спецификация свойств оружия и брони)
# =====================================================================

class StatScale(BaseModel):
    """
    Зависимость дополнительного шанса срабатывания от характеристик динозавра.
    Пример:
        stat: "dexterity"  # Доп. шанс зависит от Ловкости
        multiplier: 0.02   # +2% к шансу за каждую единицу ловкости
    """
    stat: str
    multiplier: float


class CombatPropertyModel(BaseModel):
    """
    Модель описания отдельного свойства оружия или брони.
    
    Примеры использования типов свойств (type):
    1. "multi_strike" - Несколько ударов.
       params:
         extra_chance: float  # Шанс дополнительного удара (от 0.0 до 1.0)
         max_strikes: int     # Максимальное количество ударов
    2. "ignore_armor" - Игнорирование брони.
       params:
         ignore_percent: float # Процент игнорируемой брони (от 0.0 до 1.0)
    3. "aoe" - Урон по области.
       params:
         aoe_percent: float  # Процент урона по остальным целям (от 0.0 до 1.0)
    4. "apply_effect_enemy" - Наложение эффекта на врага.
       params:
         effect_type: str  # Тип эффекта: "stun" (оглушение), "dot" (урон во времени), "corrosion" (окисление)
         effect_name: str  # Ключ локализации для кастомного названия эффекта (например, "combat_properties.effects.burning")
         duration: int     # Длительность в ходах
         val: float        # Сила эффекта (урон/ход или повреждение прочности/ход)
    5. "apply_effect_self" - Наложение эффекта на себя или союзников.
       params:
         effect_name: str       # Ключ локализации для названия баффа (например, "combat_properties.effects.rage")
         duration: int          # Длительность баффа
         buff_stats: Dict[str, float]  # Временное повышение характеристик (например, {"power": 5})
         heal_instant: float    # Моментальное исцеление HP
         energy_regen: float    # Моментальное восстановление энергии
         heal_over_time: float   # Регенерация здоровья за ход
         energy_over_time: float # Регенерация энергии за ход
    6. "ignore_effects" - Игнорирование эффектов (для брони).
       params:
         ignored_types: List[str]  # Список игнорируемых эффектов (например, ["stun", "dot"])
         chance: float             # Шанс полного или частичного игнорирования
         reduction_percent: float  # Процент уменьшения входящего урона от эффектов
    7. "self_repair" - Самовосстановление брони.
       params:
         repair_val: float  # Величина восстановления прочности брони за ход
    8. "counter_attack" - Шанс на дополнительную/контратаку при получении удара.
       params:
         chance: float  # Шанс контратаки
    """
    name: str  # Ключ локализации для названия свойства
    type: str  # Тип свойства (см. список выше)
    points_cost: int = 1  # Стоимость активации в ОД за бой (базово у динозавра 2 очка на бой)
    cooldown: int = 0  # Кулдаун свойства в ходах
    energy_cost: int = 0  # Требуемое количество энергии для использования
    base_chance: float = 1.0  # Базовый шанс срабатывания
    stat_scale: Optional[StatScale] = None  # Влияние характеристик динозавра
    params: Dict[str, Any] = Field(default_factory=dict)  # Параметры конкретного типа свойства
    lvl_scale: Dict[str, Any] = Field(default_factory=dict)  # Коэффициенты масштабирования параметров от уровня


# =====================================================================
# ФУНКЦИИ МАСШТАБИРОВАНИЯ И СОРТИРОВКИ
# =====================================================================

def apply_scale(base: dict, scale: dict, lvl: int) -> dict:
    """
    Рекурсивно увеличивает числовые параметры на основе коэффициентов масштабирования lvl_scale.
    Вычисляется как: base_val + lvl * scale_val
    """
    result = deepcopy(base)
    for k, v in scale.items():
        if k in result:
            if isinstance(v, dict) and isinstance(result[k], dict):
                result[k] = apply_scale(result[k], v, lvl)
            elif isinstance(v, (int, float)) and isinstance(result[k], (int, float)):
                result[k] = result[k] + lvl * v
    return result


def deep_merge(target: dict, source: dict) -> dict:
    """
    Рекурсивное слияние словарей.
    """
    result = deepcopy(target)
    for k, v in source.items():
        if k in result:
            if isinstance(v, dict) and isinstance(result[k], dict):
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        else:
            result[k] = v
    return result


def get_scaled_properties(item_id: str, lvl: int) -> Dict[str, dict]:
    """
    Возвращает свойства предмета, масштабированные под указанный уровень.
    """
    item_data = get_data(item_id)
    if not item_data:
        return {}

    # Загружаем базовые свойства
    base_properties = item_data.get('properties', {})
    scaled_properties = {}

    for prop_id, prop_info in base_properties.items():
        prop_copy = deepcopy(prop_info)
        
        # 1. Применяем динамическое масштабирование по формуле (lvl_scale)
        lvl_scale = prop_copy.get('lvl_scale', {})
        if lvl_scale and lvl > 0:
            prop_copy = apply_scale(prop_copy, lvl_scale, lvl)

        # 2. Перекрываем значениями из явного описания уровней (lvls), если они заданы
        lvl_override = {}
        if lvl > 0:
            lvls = item_data.get('lvls', {})
            valid_lvls = []
            for k, lvl_info in lvls.items():
                try:
                    k_int = int(k)
                    if k_int <= lvl and 'properties' in lvl_info and prop_id in lvl_info['properties']:
                        valid_lvls.append(k_int)
                except ValueError:
                    continue
            if valid_lvls:
                best_lvl = max(valid_lvls)
                lvl_override = lvls[str(best_lvl)]['properties'][prop_id]

        if lvl_override:
            prop_copy = deep_merge(prop_copy, lvl_override)

        # Удаляем lvl_scale из конечного результата
        prop_copy.pop('lvl_scale', None)
        scaled_properties[prop_id] = prop_copy

    return scaled_properties


def get_item_properties(item: dict, level: int = None) -> List[Tuple[str, dict]]:
    """
    Возвращает упорядоченный по приоритету список свойств предмета (prop_id, prop_data).
    Если приоритеты не заданы (или сброшены), возвращает свойства в случайном (но стабильном для сессии/предмета) порядке.
    """
    if 'item_id' not in item and 'items_data' in item:
        item = item['items_data']
        
    item_id = item['item_id']
    if level is None:
        level = get_item_level(item)

    scaled_props = get_scaled_properties(item_id, level)
    if not scaled_props:
        return []

    # Получаем сохраненные приоритеты
    abilities = item.get('abilities', {})
    skills_priority = abilities.get('skills_priority', None)

    # Преобразуем свойства в список кортежей
    props_list = list(scaled_props.items())

    if skills_priority:
        # Сортируем по заданному приоритету (меньшее число - выше приоритет)
        # Если свойство не описано в приоритетах, даем ему очень большой приоритет (в конец)
        def sort_key(x):
            prop_id = x[0]
            return skills_priority.get(prop_id, 9999)
        props_list.sort(key=sort_key)
    else:
        # Если приоритетов нет, перемешиваем свойства случайным образом,
        # используя хэш от item_id и уникального _id (если есть) или имени в качестве зерна, 
        # чтобы порядок был стабилен для конкретного экземпляра предмета
        seed_str = str(item.get('_id', item_id))
        r = random.Random(seed_str)
        r.shuffle(props_list)

    return props_list


# =====================================================================
# ФОРМАТИРОВАНИЕ ДЛЯ ОТОБРАЖЕНИЯ В ТЕЛЕГРАМЕ
# =====================================================================

def round_val(val: Any) -> Any:
    if isinstance(val, (int, float)):
        return round(val, 1)
    return val


def format_plural(val: float, key: str, lang: str) -> str:
    val_r = round_val(val)
    loc_cp = get_loc_data('combat_properties', lang) or {}
    plurals = loc_cp.get('plurals', {}).get(key, [])
    
    if plurals and isinstance(plurals, list) and len(plurals) > 0:
        if len(plurals) == 3:
            if isinstance(val_r, int):
                if val_r % 10 == 1 and val_r % 100 != 11:
                    suffix = plurals[0]
                elif val_r % 10 in [2, 3, 4] and val_r % 100 not in [12, 13, 14]:
                    suffix = plurals[1]
                else:
                    suffix = plurals[2]
            else:
                suffix = plurals[1]
        elif len(plurals) == 2:
            suffix = plurals[0] if val_r == 1 else plurals[1]
        else:
            suffix = plurals[0]
        return f"{val_r} {suffix}"
    
    return f"{val_r} {key}"


def format_turns(turns: float, lang: str) -> str:
    return format_plural(turns, "turns", lang)


def format_units(val: float, lang: str) -> str:
    return format_plural(val, "units", lang)


def _safe_format(template: str, **kwargs) -> str:
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def _translate_template(key: str, lang: str, default: str = "") -> str:
    return t(key, lang, formating=False, default=default)


def _format_effect_name(params: dict, lang: str) -> str:
    eff_type = params.get('effect_type', '')
    eff_name_key = params.get('effect_name')
    
    name_kwargs = {
        'name': params.get('name', eff_type),
        'duration': format_turns(params.get('duration', 1), lang),
        'val': format_units(params.get('val', 0), lang)
    }

    if eff_name_key:
        eff_name = _translate_template(eff_name_key, lang, eff_name_key)
    else:
        eff_name = _translate_template(f"combat_properties.effects.{eff_type}", lang, eff_type)

    return _safe_format(eff_name, **name_kwargs)


def format_property_effect(prop_data: dict, lang: str) -> str:
    loc_cp = get_loc_data('combat_properties', lang) or {}
    params = prop_data.get('params', {})
    p_type = prop_data.get('type', '')
    type_loc = loc_cp.get('types', {}).get(p_type, "")

    if p_type == 'multi_strike':
        return _safe_format(
            type_loc,
            extra_chance=round_val(params.get('extra_chance', 0.0) * 100),
            max_strikes=params.get('max_strikes', 2)
        )

    if p_type == 'ignore_armor':
        return _safe_format(
            type_loc,
            ignore_percent=round_val(params.get('ignore_percent', 0.0) * 100)
        )

    if p_type == 'aoe':
        return _safe_format(
            type_loc,
            aoe_percent=round_val(params.get('aoe_percent', 0.0) * 100)
        )

    if p_type == 'apply_effect_enemy':
        return _safe_format(
            type_loc,
            effect_name=_format_effect_name(params, lang),
            duration=format_turns(params.get('duration', 1), lang),
            val=format_units(params.get('val', 0), lang)
        )

    if p_type == 'apply_effect_self':
        buffs_list = []
        for stat_key, stat_val in params.get('buff_stats', {}).items():
            stat_name = t(f"combat_properties.stats.{stat_key}", lang, default=stat_key)
            buffs_list.append(f"+{round_val(stat_val)} {stat_name}")

        if params.get('heal_instant', 0) > 0:
            buffs_list.append(f"+{round_val(params['heal_instant'])} HP")
        if params.get('energy_regen', 0) > 0:
            buffs_list.append(f"+{round_val(params['energy_regen'])} ⚡")
        if params.get('heal_over_time', 0) > 0:
            val_hot = round_val(params['heal_over_time'])
            lbl_hot = t("combat_properties.stats.hp_over_time", lang, default="HP/turn")
            buffs_list.append(f"+{val_hot} {lbl_hot}")
        if params.get('energy_over_time', 0) > 0:
            val_eot = round_val(params['energy_over_time'])
            lbl_eot = t("combat_properties.stats.energy_over_time", lang, default="⚡/turn")
            buffs_list.append(f"+{val_eot} {lbl_eot}")

        return _safe_format(
            type_loc,
            effect_name=_format_effect_name(params, lang),
            duration=format_turns(params.get('duration', 1), lang),
            buffs=", ".join(buffs_list)
        )

    if p_type == 'ignore_effects':
        ignored_names = [
            _safe_format(
                _translate_template(f"combat_properties.effects.{effect_type}", lang, effect_type),
                name=effect_type,
                duration=format_turns(params.get('duration', 1), lang),
                val=format_units(params.get('val', 0), lang)
            )
            for effect_type in params.get('ignored_types', [])
        ]
        return _safe_format(
            type_loc,
            ignored=", ".join(ignored_names),
            chance=round_val(params.get('chance', 1.0) * 100),
            reduction=round_val(params.get('reduction_percent', 0.0) * 100)
        )

    if p_type == 'self_repair':
        return _safe_format(type_loc, repair_val=round_val(params.get('repair_val', 0)))

    if p_type == 'counter_attack':
        return _safe_format(type_loc, chance=round_val(params.get('chance', 0.0) * 100))

    return str(params)


def format_property_text(prop_id: str, prop_data: dict, lang: str, priority: Optional[int] = None) -> str:
    loc_cp = get_loc_data('combat_properties', lang)
    if not loc_cp:
        loc_cp = {}

    name_key = prop_data.get('name', prop_id)
    name = t(name_key, lang, default=name_key)
    
    # 1. Заголовок
    priority_str = f" [{priority}]" if priority is not None else ""
    text = f"┌ 🔮 *{name}*{priority_str}\n"

    # 2. Стоимость активации
    points = prop_data.get('points_cost', 1)
    energy = prop_data.get('energy_cost', 0)
    cooldown = prop_data.get('cooldown', 0)
    
    cd_str = format_turns(cooldown, lang)
    
    cost_template = loc_cp.get('activation_cost', "├ Цена: {points} очков действия, Энергия: {energy} ⚡, Перезарядка: {cooldown}")
    text += cost_template.format(points=points, energy=energy, cooldown=cd_str) + "\n"

    # 3. Шанс срабатывания
    base_chance = round_val(prop_data.get('base_chance', 1.0) * 100)
    stat_scale = prop_data.get('stat_scale')
    stat_info = ""
    if stat_scale:
        stat_key = stat_scale.get('stat', '')
        mult = round_val(stat_scale.get('multiplier', 0.0) * 100)
        stat_name = t(f"combat_properties.stats.{stat_key}", lang, default=stat_key)
        scale_template = loc_cp.get('stat_scale', "+{percent}% за ед. {stat}")
        stat_info = " (" + scale_template.format(percent=mult, stat=stat_name) + ")"
        
    chance_template = loc_cp.get('chance', "├ Шанс: {chance}%{stat_info}")
    text += chance_template.format(chance=base_chance, stat_info=stat_info) + "\n"

    effect_desc = format_property_effect(prop_data, lang)

    text += f"└ Эффект: {effect_desc}"
    return text


def format_all_properties(item: dict, lang: str) -> str:
    """
    Форматирует все свойства предмета для описания в карточке.
    """
    props = get_item_properties(item)
    if not props:
        return ""

    loc_cp = get_loc_data('combat_properties', lang)
    title = loc_cp.get('title', "\n\n*🔮 Свойства:*")
    
    text = f"{title}\n"
    
    abilities = item.get('abilities', {})
    skills_priority = abilities.get('skills_priority', {})

    for prop_id, prop_data in props:
        priority = None
        if skills_priority and prop_id in skills_priority:
            priority = skills_priority[prop_id]
        
        prop_text = format_property_text(prop_id, prop_data, lang, priority)
        text += prop_text + "\n\n"

    return text.strip()


def format_all_properties_page(item: dict, lang: str, page: int = 0) -> tuple[str, int]:
    props = get_item_properties(item)
    if not props:
        return "", 1

    props_per_page = 3
    total_pages = max(1, (len(props) + props_per_page - 1) // props_per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * props_per_page
    page_props = props[start:start + props_per_page]

    loc_cp = get_loc_data('combat_properties', lang)
    title = loc_cp.get('title', "\n\n*🔮 Свойства:*")
    page_tpl = loc_cp.get('page', "Страница {page}/{pages}")

    abilities = item.get('abilities', {})
    skills_priority = abilities.get('skills_priority', {})

    text = f"{title}\n{page_tpl.format(page=page + 1, pages=total_pages)}\n\n"
    blocks = []
    for prop_id, prop_data in page_props:
        priority = skills_priority.get(prop_id) if skills_priority else None
        blocks.append(format_property_text(prop_id, prop_data, lang, priority))
    text += "\n\n".join(blocks)
    return text.strip(), total_pages


def format_level_preview(item: dict, lang: str) -> str:
    from bot.modules.items.item import (
        get_item_damage,
        get_item_endurance_max,
        get_item_reflection,
        get_item_capacity,
        get_item_effectiv
    )

    if 'item_id' not in item and 'items_data' in item:
        item_data = item['items_data']
    else:
        item_data = item

    item_id = item_data['item_id']
    raw_data = get_data(item_id)
    if not raw_data:
        return "Item not found"

    item_type = raw_data.get('type', '')
    max_lvl = 10 if item_type == 'weapon' else 5
    item_name = t(f"items_names.{item_id}.name", lang, default=item_id)

    loc_cp = get_loc_data('combat_properties', lang)
    title_template = loc_cp.get('level_title', "📊 *Эффекты уровней для {name}:*")
    
    text = title_template.format(name=item_name) + "\n"

    stat_durability = t("combat_properties.stats.endurance", lang, default="Прочность")
    stat_damage = t("combat_properties.stats.damage", lang, default="Урон")
    stat_reflection = t("combat_properties.stats.reflection", lang, default="Защита")
    stat_capacity = t("combat_properties.stats.capacity", lang, default="Вместимость")
    stat_effectiv = t("combat_properties.stats.effectiv", lang, default="Эффективность")

    current_lvl = get_item_level(item_data)

    for lvl in range(max_lvl + 1):
        if lvl == current_lvl:
            current_label = t("combat_properties.current_label", lang, default="Current")
            lvl_label = t("combat_properties.level_label", lang, default="Level")
            text += f"\n*▶ {lvl_label} +{lvl} ({current_label}):*\n"
        else:
            row_template = loc_cp.get('level_row', "\n*Уровень +{lvl}:*\n")
            text += row_template.format(lvl=lvl)
        
        dummy_item = {"item_id": item_id, "abilities": {"lvl": lvl}}
        stats_lines = []
        
        dur = get_item_endurance_max(dummy_item)
        if dur:
            stats_lines.append(f"• {stat_durability}: {dur}")
            
        dmg = get_item_damage(dummy_item)
        if dmg:
            stats_lines.append(f"• {stat_damage}: {dmg['min']} - {dmg['max']}")
            
        refl = get_item_reflection(dummy_item)
        if refl:
            stats_lines.append(f"• {stat_reflection}: {refl}")
            
        cap = get_item_capacity(dummy_item)
        if cap:
            stats_lines.append(f"• {stat_capacity}: {cap}")
            
        eff = get_item_effectiv(dummy_item)
        if eff and eff > 1:
            stats_lines.append(f"• {stat_effectiv}: {eff}")

        text += "\n".join(stats_lines) + "\n"

        props = get_scaled_properties(item_id, lvl)
        if props:
            skills_lines = []
            for prop_id, prop_data in props.items():
                name_key = prop_data.get('name', prop_id)
                name = t(name_key, lang, default=prop_id)
                base_chance = round_val(prop_data.get('base_chance', 1.0) * 100)
                effect_desc = format_property_effect(prop_data, lang)
                chance_label = t("combat_properties.chance_label", lang, default="Chance")
                skills_lines.append(f"• *{name}* ({chance_label}: {base_chance}%): {effect_desc}")

            text += "\n" + "\n\n".join(skills_lines) + "\n"

    return text


def format_level_preview_page(item: dict, lang: str, page: int = 0) -> tuple[str, int]:
    from bot.modules.items.item import (
        get_item_damage,
        get_item_endurance_max,
        get_item_reflection,
        get_item_capacity,
        get_item_effectiv
    )

    if 'item_id' not in item and 'items_data' in item:
        item_data = item['items_data']
    else:
        item_data = item

    item_id = item_data['item_id']
    raw_data = get_data(item_id)
    if not raw_data:
        return "Item not found", 1

    item_type = raw_data.get('type', '')
    max_lvl = 10 if item_type == 'weapon' else 5
    pages = max_lvl + 1
    page = max(0, min(page, pages - 1))
    lvl = page
    current_lvl = get_item_level(item_data)

    item_name = t(f"items_names.{item_id}.name", lang, default=item_id)
    loc_cp = get_loc_data('combat_properties', lang)
    title_template = loc_cp.get('level_title', "📊 *Эффекты уровней для {name}:*")
    page_tpl = loc_cp.get('page', "Страница {page}/{pages}")
    text = title_template.format(name=item_name) + "\n"
    text += page_tpl.format(page=page + 1, pages=pages) + "\n"

    stat_durability = t("combat_properties.stats.endurance", lang, default="Прочность")
    stat_damage = t("combat_properties.stats.damage", lang, default="Урон")
    stat_reflection = t("combat_properties.stats.reflection", lang, default="Защита")
    stat_capacity = t("combat_properties.stats.capacity", lang, default="Вместимость")
    stat_effectiv = t("combat_properties.stats.effectiv", lang, default="Эффективность")

    if lvl == current_lvl:
        current_label = t("combat_properties.current_label", lang, default="Current")
        lvl_label = t("combat_properties.level_label", lang, default="Level")
        text += f"\n*▶ {lvl_label} +{lvl} ({current_label}):*\n"
    else:
        row_template = loc_cp.get('level_row', "\n*Уровень +{lvl}:*\n")
        text += row_template.format(lvl=lvl)

    dummy_item = {"item_id": item_id, "abilities": {"lvl": lvl}}
    stats_lines = []
    
    dur = get_item_endurance_max(dummy_item)
    if dur:
        stats_lines.append(f"• {stat_durability}: {dur}")

    dmg = get_item_damage(dummy_item)
    if dmg:
        stats_lines.append(f"• {stat_damage}: {dmg['min']} - {dmg['max']}")

    refl = get_item_reflection(dummy_item)
    if refl:
        stats_lines.append(f"• {stat_reflection}: {refl}")

    cap = get_item_capacity(dummy_item)
    if cap:
        stats_lines.append(f"• {stat_capacity}: {cap}")

    eff = get_item_effectiv(dummy_item)
    if eff and eff > 1:
        stats_lines.append(f"• {stat_effectiv}: {eff}")

    text += "\n".join(stats_lines) + "\n"

    props = get_scaled_properties(item_id, lvl)
    if props:
        skills_lines = []
        for prop_id, prop_data in props.items():
            name_key = prop_data.get('name', prop_id)
            name = t(name_key, lang, default=prop_id)
            base_chance = round_val(prop_data.get('base_chance', 1.0) * 100)
            effect_desc = format_property_effect(prop_data, lang)
            chance_label = t("combat_properties.chance_label", lang, default="Chance")
            skills_lines.append(f"• *{name}* ({chance_label}: {base_chance}%): {effect_desc}")
        
        text += "\n" + "\n\n".join(skills_lines) + "\n"

    return text.strip(), pages
