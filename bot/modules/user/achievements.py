from typing import Any, Union, List, Dict, Optional
import time
from pydantic import BaseModel, Field
from bson import ObjectId

from bot.const import ACHIEVEMENTS
from bot.exec import bot
from bot.modules.localization import t, get_lang

# ================ Pydantic Models for Config Validation ================ #

class AchievementAward(BaseModel):
    coins: int = 0
    exp: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)

class AchievementConfig(BaseModel):
    type: str  # 'simple', 'progress', 'floating'
    title: str = ""
    description: str
    short_description: str
    secret: bool = False
    first_user: bool = False
    stack: int = 0  # 0: non-stackable, >0: max stacks, -1: infinite
    # Events that trigger this achievement check and the checker function name
    events: List[str] = Field(default_factory=list)
    checker: str = ""
    # Floating achievements cannot have rewards — validated below
    award: Optional[AchievementAward] = None
    progress_check: str = ""
    ignore_progress: bool = False
    save_progress: bool = False

    def model_post_init(self, __context: Any) -> None:
        if self.type == 'floating' and self.award is not None:
            if self.award.coins != 0 or self.award.exp != 0 or self.award.items:
                raise ValueError(
                    f"Floating achievement cannot have award (coins/exp/items). "
                    f"Remove 'award' or set all values to 0."
                )
        if self.type != 'floating' and self.award is None:
            # Non-floating defaults to empty award
            object.__setattr__(self, 'award', AchievementAward())

class AchievementsFileConfig(BaseModel):
    groups: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    display_groups: List[Dict[str, Any]] = Field(default_factory=list)
    achievements: Dict[str, AchievementConfig]

# ================ Helper Functions ================ #

def get_achievement(achievement_type: str) -> dict:
    ach_data = {
        "type": "simple",
        "title": "",
        "description": "",
        "short_description": "",
        "secret": False,
        "first_user": False,
        "stack": 0,
        "award": {
            "coins": 0,
            "exp": 0,
            "items": []
        },
        "progress_check": ""
    }
    ach_data.update(
        ACHIEVEMENTS['achievements'].get(achievement_type, {})
    )
    return ach_data

async def add_achievement(userid: int, achievement_type: str, data: Any = None) -> bool:
    """ Manually unlocks or awards an achievement. Called from admin commands or direct overrides. """
    return await award_achievement_to_user(userid, achievement_type)

async def award_achievement_to_user(userid: int, ach_id: str) -> bool:
    from bot.models.user import Achievement, User
    
    ach_cfg = ACHIEVEMENTS['achievements'].get(ach_id)
    if not ach_cfg:
        return False
        
    # Check first_user constraint
    if ach_cfg.get('first_user', False):
        already_held = await Achievement.find_one(
            Achievement.achievement_id == ach_id,
            Achievement.unlocked_time > 0
        )
        if already_held:
            return False

    ach_doc = await Achievement.find_one(
        Achievement.userid == userid,
        Achievement.achievement_id == ach_id
    )

    max_stack = ach_cfg.get('stack', 0)

    if ach_doc:
        if ach_doc.unlocked_time > 0:
            if max_stack == 0:
                return False
            elif max_stack > 0 and ach_doc.stack >= max_stack:
                return False
            
            ach_doc.stack += 1
            ach_doc.unlocked_time = int(time.time())
            await ach_doc.save()
        else:
            ach_doc.unlocked_time = int(time.time())
            ach_doc.stack = 1
            await ach_doc.save()
    else:
        ach_doc = Achievement(
            userid=userid,
            achievement_id=ach_id,
            unlocked_time=int(time.time()),
            stack=1
        )
        await ach_doc.insert()

    # Invalidate profile stats cache so next view reflects new achievement
    try:
        from bot.redismanager import redis_del
        await redis_del(f"profile_ach:{userid}")
    except Exception:
        pass

    # Give awards (floating achievements have no award field)
    user = await User.find_one(User.userid == userid)
    if user:
        award = ach_cfg.get('award') or {}
        if award.get('coins', 0) > 0:
            await user.add_coins(award['coins'])
        if award.get('exp', 0) > 0:
            await user.add_xp_lvl(award['exp'])
        if award.get('items'):
            from bot.modules.items.item import AddItemToUser
            for it in award['items']:
                it_id = it.get('item_id') or it.get('itemid')
                if it_id:
                    abilities = dict(it.get('abilities') or {})
                    abilities['interact'] = False
                    await AddItemToUser(userid, it_id, it.get('count', 1), abilities)

    # Send congratulatory notification with effect 🎉
    try:
        lang = await get_lang(userid)
        ach_name = t(f"achievements.{ach_id}.name", lang)
        desc = t(ach_cfg.get('description', ''), lang)
        congrat_text = t("achievements.unlocked_message", lang, name=ach_name, desc=desc)

        # Add rewards info to notification if present
        award = ach_cfg.get('award') or {}
        coins = award.get('coins', 0)
        exp = award.get('exp', 0)
        items = award.get('items', [])

        reward_lines = []
        if coins > 0:
            reward_lines.append(t("achievements.reward_coins", lang, coins=coins))
        if exp > 0:
            reward_lines.append(t("achievements.reward_xp", lang, xp=exp))
        if items:
            from bot.modules.items.item import get_name as get_item_name
            for it in items:
                it_id = it.get('item_id') or it.get('itemid')
                count = it.get('count', 1)
                abilities = it.get('abilities', {})
                if it_id:
                    it_name = get_item_name(it_id, lang, abilities)
                    reward_lines.append(
                        t("achievements.reward_item", lang, item_name=it_name, count=count))

        if reward_lines:
            congrat_text += t("achievements.reward_prefix", lang) + "".join(reward_lines)
        
        # Replace coins emoji with custom emoji and resolve all custom emojis
        import re
        custom_emojis = re.findall(r'\!\[[^\]]+\]\(tg://emoji\?id=\d+\)', congrat_text)
        for i, ce in enumerate(custom_emojis):
            congrat_text = congrat_text.replace(ce, f"%%CE_{i}%%")

        congrat_text = congrat_text.replace("🪙", "{custom_emoji:coins}")
        from bot.modules.localization import resolve_custom_emojis
        congrat_text = resolve_custom_emojis(congrat_text)

        for i, ce in enumerate(custom_emojis):
            congrat_text = congrat_text.replace(f"%%CE_{i}%%", ce)

        try:
            await bot.send_message(
                chat_id=userid,
                text=congrat_text,
                parse_mode="Markdown",
                message_effect_id="5159385139981059251"
            )
        except Exception:
            await bot.send_message(
                chat_id=userid,
                text=congrat_text,
                parse_mode="Markdown"
            )
    except Exception as e:
        import traceback
        from bot.modules.logs import log
        log(f"Exception in award_achievement_to_user for user {userid}, achievement {ach_id}: {e}\n{traceback.format_exc()}", 4)
        
    # Trigger recursive achievement check for percentage-based achievements
    if ach_id not in ("quests_pct_25", "quests_pct_50", "quests_pct_75", "quests_pct_100", "quests_pct_first", "quests_secrets_all"):
        import asyncio
        asyncio.create_task(check_achievements(userid, "achievement_unlocked"))

    return True

async def check_achievements(userid: int, event_type: str, data: Any = None):
    """ Checks all achievements whose events list includes event_type. Config is read from JSON. """
    from bot.models.user import Achievement

    all_achievements = ACHIEVEMENTS.get('achievements', {})

    # Determine which ach_ids are relevant for this event_type
    relevant_ids = [
        ach_id for ach_id, ach_cfg in all_achievements.items()
        if ach_cfg.get('type') != 'floating' and event_type in ach_cfg.get('events', [])
    ]
    if not relevant_ids:
        return

    # Fetch all existing docs for this user in one batch query
    existing_docs: dict[str, Achievement] = {
        d.achievement_id: d
        for d in await Achievement.find(Achievement.userid == userid).to_list()
    }

    for ach_id in relevant_ids:
        ach_cfg = all_achievements[ach_id]
        ach_doc = existing_docs.get(ach_id)

        # If already unlocked and not stackable, skip
        if ach_doc and ach_doc.unlocked_time > 0:
            max_stack = ach_cfg.get('stack', 0)
            if max_stack == 0 or (max_stack > 0 and ach_doc.stack >= max_stack):
                continue

        checker_name = ach_cfg.get('checker', '')
        if not checker_name:
            continue
        checker_func = globals().get(checker_name)
        if checker_func:
            current_progress = ach_doc.progress if ach_doc else None
            try:
                is_completed, updated_progress = await checker_func(userid, event_type, data, current_progress)
            except Exception as e:
                from bot.modules.logs import log
                log(f"Error running checker {checker_name} for user {userid}: {e}", 3)
                continue

            # Save progress if changed
            if updated_progress != current_progress:
                if ach_cfg.get('save_progress', False):
                    if not ach_doc:
                        ach_doc = Achievement(
                            userid=userid,
                            achievement_id=ach_id,
                            unlocked_time=0,
                            progress=updated_progress
                        )
                        await ach_doc.insert()
                        existing_docs[ach_id] = ach_doc
                    else:
                        ach_doc.progress = updated_progress
                        await ach_doc.save()

            if is_completed:
                await award_achievement_to_user(userid, ach_id)

async def check_all_achievements(userid: int):
    """ Performs static queries (levels, counts, market shop, etc.) to retroactively grant achievements. """
    from bot.redismanager import redis_get, redis_set
    cooldown_key = f"check_ach_cooldown:{userid}"
    try:
        if await redis_get(cooldown_key):
            return
    except Exception:
        pass

    await check_achievements(userid, "static")

    try:
        await redis_set(cooldown_key, 1, ex=300)  # 5 minutes cooldown
    except Exception:
        pass

async def revoke_floating_achievement(userid: int, ach_id: str):
    """ Removes a floating achievement from a user and notifies them. """
    from bot.models.user import Achievement
    holder_doc = await Achievement.find_one(
        Achievement.userid == userid,
        Achievement.achievement_id == ach_id
    )
    if holder_doc:
        await holder_doc.delete()

    # Notify the previous holder
    try:
        lang = await get_lang(userid)
        ach_cfg = ACHIEVEMENTS['achievements'].get(ach_id, {})
        ach_name = t(f"achievements.{ach_id}.name", lang)
        revoke_text = t("achievements.floating_revoked", lang, name=ach_name)
        try:
            await bot.send_message(
                chat_id=userid,
                text=revoke_text,
                parse_mode="Markdown"
            )
        except Exception:
            pass
    except Exception:
        pass

async def update_floating_ranking(ranking_id: str, candidates: Union[list[int], int]):
    """ Transfers a floating achievement to a new leader, notifying the previous holder. """
    from bot.models.user import Achievement
    from typing import Union

    if isinstance(candidates, int):
        candidates = [candidates]

    if not candidates:
        return

    current_holder = await Achievement.find_one(
        Achievement.achievement_id == ranking_id,
        Achievement.unlocked_time > 0
    )

    if current_holder:
        if current_holder.userid in candidates:
            return
        # Notify previous holder before removing
        await revoke_floating_achievement(current_holder.userid, ranking_id)
    else:
        await award_achievement_to_user(candidates[0], ranking_id)
        return

    await award_achievement_to_user(candidates[0], ranking_id)


# ================ Checker Implementation Functions ================ #

async def check_quests_100(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    if user:
        val = user.settings.get('quests_ended', 0)
        return val >= 100, val
    return False, current_progress

async def check_feed_all_food(userid, event_type, data, current_progress):
    if not isinstance(current_progress, list):
        current_progress = []
    if data and data not in current_progress:
        current_progress.append(data)
    from bot.modules.items.collect_items import get_all_items
    all_items = get_all_items()
    all_eat_ids = {k for k, v in all_items.items() if getattr(v, 'type', '') == 'eat'}
    current_progress = [x for x in current_progress if x in all_eat_ids]
    return len(current_progress) >= len(all_eat_ids), current_progress

async def check_feed_dislike(userid, event_type, data, current_progress):
    if data == 'disliked':
        return True, None
    return False, current_progress

async def check_equip_full(userid, event_type, data, current_progress):
    from bot.models.user import User
    from bot.models.items import Item
    user = await User.find_one(User.userid == userid)
    if user:
        dinos = await user.get_dinos()
        for dino in dinos:
            accs = await Item.find_accessory(dino.id)
            if len(accs) >= 5:
                return True, len(accs)
    return False, current_progress

async def check_journey_all_locations(userid, event_type, data, current_progress):
    if not isinstance(current_progress, list):
        current_progress = []
    if isinstance(data, list):
        for loc in data:
            if loc not in current_progress:
                current_progress.append(loc)
    all_locations = {'forest', 'lost-islands', 'desert', 'mountains', 'magic-forest'}
    current_progress = [x for x in current_progress if x in all_locations]
    return len(current_progress) >= len(all_locations), current_progress

async def check_journey_12h(userid, event_type, data, current_progress):
    if isinstance(data, (int, float)) and data >= 12 * 3600:
        return True, data
    return False, current_progress

async def check_sleep_24h(userid, event_type, data, current_progress):
    if isinstance(data, (int, float)) and data >= 24 * 3600:
        return True, data
    return False, current_progress

async def check_skill_20_power(userid, event_type, data, current_progress):
    return await _check_skill(userid, data, current_progress, 'power')

async def check_skill_20_dexterity(userid, event_type, data, current_progress):
    return await _check_skill(userid, data, current_progress, 'dexterity')

async def check_skill_20_intelligence(userid, event_type, data, current_progress):
    return await _check_skill(userid, data, current_progress, 'intelligence')

async def check_skill_20_charisma(userid, event_type, data, current_progress):
    return await _check_skill(userid, data, current_progress, 'charisma')

async def _check_skill(userid, data, current_progress, skill_name):
    from bot.models.user import User
    from bot.models.dinosaur import Dino
    dinos = [data] if isinstance(data, Dino) else []
    if not dinos:
        user = await User.find_one(User.userid == userid)
        dinos = await user.get_dinos() if user else []
    for d in dinos:
        if d.stats.get(skill_name, 0.0) >= 20.0:
            return True, 20.0
    return False, current_progress

async def check_skills_all_20(userid, event_type, data, current_progress):
    from bot.models.user import User
    from bot.models.dinosaur import Dino
    dinos = [data] if isinstance(data, Dino) else []
    if not dinos:
        user = await User.find_one(User.userid == userid)
        dinos = await user.get_dinos() if user else []
    for d in dinos:
        if (d.stats.get('power', 0.0) >= 20.0 and
            d.stats.get('dexterity', 0.0) >= 20.0 and
            d.stats.get('intelligence', 0.0) >= 20.0 and
            d.stats.get('charisma', 0.0) >= 20.0):
            return True, 20.0
    return False, current_progress

async def check_skills_all_10(userid, event_type, data, current_progress):
    from bot.models.user import User
    from bot.models.dinosaur import Dino
    dinos = [data] if isinstance(data, Dino) else []
    if not dinos:
        user = await User.find_one(User.userid == userid)
        dinos = await user.get_dinos() if user else []
    for d in dinos:
        if (d.stats.get('power', 0.0) >= 10.0 and
            d.stats.get('dexterity', 0.0) >= 10.0 and
            d.stats.get('intelligence', 0.0) >= 10.0 and
            d.stats.get('charisma', 0.0) >= 10.0):
            return True, 10.0
    return False, current_progress

async def check_lvl_25(userid, event_type, data, current_progress):
    return await _check_lvl(userid, data, current_progress, 25)

async def check_lvl_50(userid, event_type, data, current_progress):
    return await _check_lvl(userid, data, current_progress, 50)

async def check_lvl_75(userid, event_type, data, current_progress):
    return await _check_lvl(userid, data, current_progress, 75)

async def check_lvl_100(userid, event_type, data, current_progress):
    return await _check_lvl(userid, data, current_progress, 100)

async def check_first_lvl_100(userid, event_type, data, current_progress):
    return await _check_lvl(userid, data, current_progress, 100)

async def check_first_lvl_200(userid, event_type, data, current_progress):
    return await _check_lvl(userid, data, current_progress, 200)

async def _check_lvl(userid, data, current_progress, target_lvl):
    from bot.models.user import User
    lvl = data if isinstance(data, int) else 0
    if not lvl:
        user = await User.find_one(User.userid == userid)
        lvl = user.lvl if user else 0
    return lvl >= target_lvl, lvl

async def check_create_market_shop(userid, event_type, data, current_progress):
    from bot.models.market import Seller
    seller = await Seller.find_one(Seller.owner_id == userid)
    return seller is not None, 1 if seller else 0

async def check_sell_first_item(userid, event_type, data, current_progress):
    return True, 1

async def check_buy_first_item(userid, event_type, data, current_progress):
    return True, 1

async def check_revive_dino(userid, event_type, data, current_progress):
    return True, 1

async def check_friends_30(userid, event_type, data, current_progress):
    from bot.models.user import Friend
    from bot.models.enums import FriendType
    friends_count = await Friend.find(Friend.userid == userid, Friend.type == FriendType.FRIENDS).count()
    return friends_count >= 30, friends_count

async def check_invite_50(userid, event_type, data, current_progress):
    from bot.models.user import Referral
    from bot.models.enums import ReferralType
    owner_code_doc = await Referral.find_one(Referral.userid == userid, Referral.type == ReferralType.GENERAL)
    if owner_code_doc:
        invite_count = await Referral.find(Referral.code == owner_code_doc.code, Referral.type == ReferralType.SUB).count()
        return invite_count >= 50, invite_count
    return False, current_progress

async def check_transform_dino(userid, event_type, data, current_progress):
    return True, 1

async def check_buy_junk_100(userid, event_type, data, current_progress):
    if not isinstance(current_progress, int):
        current_progress = 0
    cnt = data if isinstance(data, int) else 0
    current_progress += cnt
    return current_progress >= 100, current_progress

async def check_sell_buyer_1k(userid, event_type, data, current_progress):
    if not isinstance(current_progress, int):
        current_progress = 0
    cnt = data if isinstance(data, int) else 0
    current_progress += cnt
    return current_progress >= 1000, current_progress

async def check_upgrade_1(userid, event_type, data, current_progress):
    return await _check_upgrade(userid, data, current_progress, 1)

async def check_upgrade_3(userid, event_type, data, current_progress):
    return await _check_upgrade(userid, data, current_progress, 3)

async def check_upgrade_5(userid, event_type, data, current_progress):
    return await _check_upgrade(userid, data, current_progress, 5)

async def check_upgrade_10(userid, event_type, data, current_progress):
    return await _check_upgrade(userid, data, current_progress, 10)

async def _check_upgrade(userid, data, current_progress, target_lvl):
    lvl = data if isinstance(data, int) else 0
    return lvl >= target_lvl, lvl

async def _count_donations(userid):
    from bot.models.other import Donation
    count = await Donation.find(
        Donation.userid == userid,
        Donation.product != "non_repayable"
    ).count()
    return count

async def check_support_bot(userid, event_type, data, current_progress):
    count = await _count_donations(userid)
    return count >= 1, count

async def check_support_5(userid, event_type, data, current_progress):
    count = await _count_donations(userid)
    return count >= 5, count

async def check_support_20(userid, event_type, data, current_progress):
    count = await _count_donations(userid)
    return count >= 20, count

# ================ New Checker Functions ================ #

# -- Quests count --
async def _check_quests_n(userid, n, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('quests_ended', 0) if user else 0
    return val >= n, val

async def check_quests_10(userid, event_type, data, current_progress):
    return await _check_quests_n(userid, 10, current_progress)

async def check_quests_50(userid, event_type, data, current_progress):
    return await _check_quests_n(userid, 50, current_progress)

async def check_quests_250(userid, event_type, data, current_progress):
    return await _check_quests_n(userid, 250, current_progress)

async def check_quests_500(userid, event_type, data, current_progress):
    return await _check_quests_n(userid, 500, current_progress)

# -- Quests % completion --
def _count_completable_achievements():
    """Count non-floating, non-first_user achievements (the ones a user can complete)."""
    total = 0
    for ach_id, cfg in ACHIEVEMENTS.get('achievements', {}).items():
        if ach_id == 'example':
            continue
        if cfg.get('type') == 'floating':
            continue
        if cfg.get('first_user', False):
            continue
        if cfg.get('ignore_progress', False):
            continue
        total += 1
    return total

async def _check_quests_pct(userid, pct, current_progress):
    from bot.models.user import Achievement
    total = _count_completable_achievements()
    if total == 0:
        return False, 0
    ignored_ids = [ach_id for ach_id, cfg in ACHIEVEMENTS.get('achievements', {}).items()
                   if cfg.get('ignore_progress', False)]
    unlocked = await Achievement.find({
        "userid": userid,
        "unlocked_time": {"$gt": 0},
        "achievement_id": {"$nin": ignored_ids}
    }).count()
    user_pct = int(unlocked * 100 / total)
    return user_pct >= pct, user_pct

async def check_quests_pct_25(userid, event_type, data, current_progress):
    return await _check_quests_pct(userid, 25, current_progress)

async def check_quests_pct_50(userid, event_type, data, current_progress):
    return await _check_quests_pct(userid, 50, current_progress)

async def check_quests_pct_75(userid, event_type, data, current_progress):
    return await _check_quests_pct(userid, 75, current_progress)

async def check_quests_pct_100(userid, event_type, data, current_progress):
    return await _check_quests_pct(userid, 100, current_progress)

async def check_quests_pct_first(userid, event_type, data, current_progress):
    """first_user: only awarded once globally via update_floating_ranking-like logic."""
    done, val = await _check_quests_pct(userid, 100, current_progress)
    return done, val

async def check_quests_secrets_all(userid, event_type, data, current_progress):
    """All secret achievements unlocked."""
    from bot.models.user import Achievement
    secret_ids = [ach_id for ach_id, cfg in ACHIEVEMENTS.get('achievements', {}).items()
                  if cfg.get('secret', False) and cfg.get('type') != 'floating' and not cfg.get('first_user', False)]
    if not secret_ids:
        return False, 0
    unlocked = await Achievement.find({
        "userid": userid,
        "achievement_id": {"$in": secret_ids},
        "unlocked_time": {"$gt": 0}
    }).count()
    return unlocked >= len(secret_ids), unlocked

# -- Dino count --
async def _check_dino_count(userid, n):
    from bot.models.dinosaur import DinoOwners
    count = await DinoOwners.find(DinoOwners.owner_id == userid).count()
    return count >= n, count

async def check_dino_count_2(userid, event_type, data, current_progress):
    return await _check_dino_count(userid, 2)

async def check_dino_count_3(userid, event_type, data, current_progress):
    return await _check_dino_count(userid, 3)

async def check_dino_count_6(userid, event_type, data, current_progress):
    return await _check_dino_count(userid, 6)

async def check_dino_count_10(userid, event_type, data, current_progress):
    return await _check_dino_count(userid, 10)

# Rarity order for upgrade/downgrade detection
QUALITY_ORDER = ['com', 'unc', 'rar', 'mys', 'leg']

async def check_dino_upgrade_rarity(userid, event_type, data, current_progress):
    """data = {'from': old_q, 'to': new_q}"""
    if not isinstance(data, dict):
        return False, current_progress
    from_q = data.get('from', '')
    to_q = data.get('to', '')
    if from_q in QUALITY_ORDER and to_q in QUALITY_ORDER:
        upgraded = QUALITY_ORDER.index(to_q) > QUALITY_ORDER.index(from_q)
        return upgraded, 1 if upgraded else 0
    return False, current_progress

async def check_dino_downgrade_rarity(userid, event_type, data, current_progress):
    """data = {'from': old_q, 'to': new_q}"""
    if not isinstance(data, dict):
        return False, current_progress
    from_q = data.get('from', '')
    to_q = data.get('to', '')
    if from_q in QUALITY_ORDER and to_q in QUALITY_ORDER:
        downgraded = QUALITY_ORDER.index(to_q) < QUALITY_ORDER.index(from_q)
        return downgraded, 1 if downgraded else 0
    return False, current_progress

async def check_dino_downgrade_secret(userid, event_type, data, current_progress):
    """Secret: from legendary (leg) to common (com)."""
    if not isinstance(data, dict):
        return False, current_progress
    return data.get('from') == 'leg' and data.get('to') == 'com', 1

# -- Collection % --
async def _check_collection_pct(userid, pct):
    from bot.models.user import DinoCollection
    from bot.const import DINOS
    total_families = len({v.get('name', '') for v in DINOS.get('elements', {}).values()})
    if total_families == 0:
        return False, 0
    user_families = await DinoCollection.get_count_families(userid)
    user_pct = int(user_families * 100 / total_families)
    return user_pct >= pct, user_pct

async def check_collection_pct_25(userid, event_type, data, current_progress):
    return await _check_collection_pct(userid, 25)

async def check_collection_pct_50(userid, event_type, data, current_progress):
    return await _check_collection_pct(userid, 50)

async def check_collection_pct_75(userid, event_type, data, current_progress):
    return await _check_collection_pct(userid, 75)

async def check_collection_pct_100(userid, event_type, data, current_progress):
    return await _check_collection_pct(userid, 100)

async def check_collection_first_100(userid, event_type, data, current_progress):
    done, val = await _check_collection_pct(userid, 100)
    return done, val

# -- Journey: NPC / events / sub-locations --
NPC_EVENT_IDS = [
    'rimuru_encounter', 'magecode_sage', 'kot_artist', 'despat_goblin',
    'tsuhaa_paladin', 'kai_adventurer', 'mdm_channel', 'cftxme_tycoon',
    'psadnik_veteran', 'debaster_benefactor', 'dwarf_encounter', 'ha4apur4ik_encounter'
]
ALL_JOURNEY_EVENTS = [
    'breeze', 'sunshine', 'rain', 'cold_wind', 'magic_light', 'magic_animal', 'darkness',
    'stalactites', 'cave_loot', 'cave_bat', 'fresh_water', 'palm_trees', 'oasis_rest',
    'oasis_camel', 'flooded_deck', 'reef_fish', 'sunken_chest', 'shark_attack',
    'riddle_chest', 'strange_berries', 'mysterious_crevice', 'muddy_trail', 'swamp_gas',
    'swamp_treasure', 'ruins_exploration', 'ruins_trap', 'ruins_loot', 'rimuru_encounter',
    'magecode_sage', 'kot_artist', 'despat_goblin', 'tsuhaa_paladin', 'kai_adventurer',
    'mdm_channel', 'cftxme_tycoon', 'psadnik_veteran', 'debaster_benefactor',
    'friend_meeting', 'friend_gift', 'friend_coop', 'find_dwarf_ring', 'dwarf_encounter',
    'ancient_obelisk', 'find_elven_pendant', 'elven_altar', 'find_ancient_key',
    'locked_vault', 'rune_shrine', 'mystic_portal', 'ha4apur4ik_encounter',
    'wild_predator_encounter', 'lost_archaeologist', 'fork_in_the_road', 'cat_rescue',
    'arm_wrestling', 'boulder_lift', 'broken_bridge', 'steep_climb', 'ancient_runic_puzzle',
    'poisonous_flower', 'trader_haggle', 'beast_tame', 'archery_contest', 'weightlifting',
    'riddle_sphinx', 'music_performance', 'maze_navigation', 'rope_balancing',
    'heavy_gate_push', 'beggar_dino', 'artifact_appraisal', 'dodge_trap', 'chest_pry',
    'merchant_charm', 'sleeping_dino_steal'
]
ALL_SUBLOCATIONS = [
    'cave', 'oasis', 'shipwreck', 'swamp', 'ancient_ruins', 'abandoned_camp',
    'coral_reef', 'abandoned_mine', 'underground_lake', 'dragon_lair', 'elven_groove'
]
ALL_MOBS = [
    'crocodile', 'lion', 'tiger', 'bear', 'wolf', 'shark', 'snake', 'rhino', 'elephant',
    'gorilla', 'spider', 'scorpion', 'camel', 'puma', 'fox', 'hyena', 'hippo', 'skunk',
    'sloth', 'snail', 'snow_leopard', 'squid', 'swan', 'toucan', 'turtle', 'walrus',
    'weasel', 'whale', 'wombat', 'zebra'
]

def _update_seen_list(current_progress, new_item):
    """Add item to progress list if not already present."""
    seen = list(current_progress) if isinstance(current_progress, list) else []
    if new_item not in seen:
        seen.append(new_item)
    return seen

async def check_journey_see_all_npc(userid, event_type, data, current_progress):
    """data = event_key (str)"""
    seen = _update_seen_list(current_progress, data) if isinstance(data, str) and data in NPC_EVENT_IDS else (
        list(current_progress) if isinstance(current_progress, list) else []
    )
    return all(npc in seen for npc in NPC_EVENT_IDS), seen

async def check_journey_see_all_events(userid, event_type, data, current_progress):
    """data = event_key (str)"""
    seen = _update_seen_list(current_progress, data) if isinstance(data, str) and data in ALL_JOURNEY_EVENTS else (
        list(current_progress) if isinstance(current_progress, list) else []
    )
    return all(ev in seen for ev in ALL_JOURNEY_EVENTS), seen

async def check_journey_all_sublocations(userid, event_type, data, current_progress):
    """data = list of visited locations/sublocations from journey_end."""
    seen = list(current_progress) if isinstance(current_progress, list) else []
    if isinstance(data, list):
        for loc in data:
            if loc in ALL_SUBLOCATIONS and loc not in seen:
                seen.append(loc)
    return all(sl in seen for sl in ALL_SUBLOCATIONS), seen

# -- Battle wins/losses --
async def _check_battle_wins(userid, n):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('battle_wins', 0) if user else 0
    return val >= n, val

async def check_battle_win_1(userid, event_type, data, current_progress):
    return await _check_battle_wins(userid, 1)

async def check_battle_win_5(userid, event_type, data, current_progress):
    return await _check_battle_wins(userid, 5)

async def check_battle_win_50(userid, event_type, data, current_progress):
    return await _check_battle_wins(userid, 50)

async def check_battle_win_100(userid, event_type, data, current_progress):
    return await _check_battle_wins(userid, 100)

async def check_battle_win_1000(userid, event_type, data, current_progress):
    return await _check_battle_wins(userid, 1000)

async def check_battle_defeat_all_mobs(userid, event_type, data, current_progress):
    """data = list of killed mob_ids."""
    seen = list(current_progress) if isinstance(current_progress, list) else []
    if isinstance(data, list):
        for mob in data:
            if mob in ALL_MOBS and mob not in seen:
                seen.append(mob)
    return all(m in seen for m in ALL_MOBS), seen

async def check_battle_lose_100(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('battle_losses', 0) if user else 0
    return val >= 100, val

# -- Sleep short (<4h) --
async def check_sleep_short(userid, event_type, data, current_progress):
    secs = data if isinstance(data, (int, float)) else 0
    return 0 < secs < 14400, 1 if 0 < secs < 14400 else 0

# -- Activity achievements --
async def check_hunt_once(userid, event_type, data, current_progress):
    return True, 1

async def check_fish_once(userid, event_type, data, current_progress):
    return True, 1

async def check_gather_once(userid, event_type, data, current_progress):
    return True, 1

ALL_ACTIVITY_TYPES = ['hunt', 'fish', 'gather', 'journey', 'sleep']

async def check_all_activities(userid, event_type, data, current_progress):
    """Track which activity types the user has done."""
    done = list(current_progress) if isinstance(current_progress, list) else []
    event_map = {
        'hunt_end': 'hunt', 'fish_end': 'fish', 'gather_end': 'gather',
        'journey_end': 'journey', 'sleep_end': 'sleep'
    }
    act = event_map.get(event_type)
    if act and act not in done:
        done.append(act)
    # Static check
    if event_type == 'static':
        from bot.models.user import User
        user = await User.find_one(User.userid == userid)
        if user:
            for key in ALL_ACTIVITY_TYPES:
                if user.settings.get(f'{key}_count', 0) > 0 and key not in done:
                    done.append(key)
    return all(a in done for a in ALL_ACTIVITY_TYPES), done

# -- Max skills dinos --
async def _count_max_skill_dinos(userid):
    """Count dinos where all 4 combat skills >= 20."""
    from bot.models.dinosaur import DinoOwners
    conns = await DinoOwners.find(DinoOwners.owner_id == userid).to_list()
    count = 0
    for conn in conns:
        if not conn.dino:
            continue
        try:
            d = await conn.dino.fetch()
            if d:
                stats = d.stats or {}
                if all(stats.get(s, 0) >= 20.0 for s in ['power', 'dexterity', 'intelligence', 'charisma']):
                    count += 1
        except Exception:
            pass
    return count

async def check_max_skills_dinos_2(userid, event_type, data, current_progress):
    count = await _count_max_skill_dinos(userid)
    return count >= 2, count

async def check_max_skills_dinos_3(userid, event_type, data, current_progress):
    count = await _count_max_skill_dinos(userid)
    return count >= 3, count

async def check_max_skills_dinos_5(userid, event_type, data, current_progress):
    count = await _count_max_skill_dinos(userid)
    return count >= 5, count

# -- Market sales count --
async def _get_market_sell_count(userid):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    return user.settings.get('market_sell_count', 0) if user else 0

async def _get_market_sell_total(userid):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    return user.settings.get('market_sell_total', 0) if user else 0

async def check_market_sell_10(userid, event_type, data, current_progress):
    val = await _get_market_sell_count(userid)
    return val >= 10, val

async def check_market_sell_100(userid, event_type, data, current_progress):
    val = await _get_market_sell_count(userid)
    return val >= 100, val

async def check_market_sell_1000(userid, event_type, data, current_progress):
    val = await _get_market_sell_count(userid)
    return val >= 1000, val

async def check_market_sell_10000(userid, event_type, data, current_progress):
    val = await _get_market_sell_count(userid)
    return val >= 10000, val

async def check_market_coins_1m(userid, event_type, data, current_progress):
    val = await _get_market_sell_total(userid)
    return val >= 1_000_000, val

async def check_market_coins_10m(userid, event_type, data, current_progress):
    val = await _get_market_sell_total(userid)
    return val >= 10_000_000, val

async def check_market_coins_100m(userid, event_type, data, current_progress):
    val = await _get_market_sell_total(userid)
    return val >= 100_000_000, val

# -- Buyer sales --
async def _get_buyer_count(userid):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    return user.settings.get('buyer_sell_count', 0) if user else 0

async def _get_buyer_total(userid):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    return user.settings.get('buyer_sell_total', 0) if user else 0

async def check_buyer_sell_10(userid, event_type, data, current_progress):
    val = await _get_buyer_count(userid)
    return val >= 10, val

async def check_buyer_sell_100(userid, event_type, data, current_progress):
    val = await _get_buyer_count(userid)
    return val >= 100, val

async def check_buyer_sell_1000(userid, event_type, data, current_progress):
    val = await _get_buyer_count(userid)
    return val >= 1000, val

async def check_buyer_coins_1m(userid, event_type, data, current_progress):
    val = await _get_buyer_total(userid)
    return val >= 1_000_000, val

async def check_buyer_sell_rar(userid, event_type, data, current_progress):
    """data = {'rarity': str}"""
    rarity = data.get('rarity', '') if isinstance(data, dict) else ''
    return rarity in ('rar', 'mys', 'leg'), 1

async def check_buyer_sell_leg(userid, event_type, data, current_progress):
    rarity = data.get('rarity', '') if isinstance(data, dict) else ''
    return rarity == 'leg', 1

async def check_buyer_sell_myth(userid, event_type, data, current_progress):
    """myth = 'mit' or similar mythical rarity if exists."""
    rarity = data.get('rarity', '') if isinstance(data, dict) else ''
    return rarity in ('mit', 'myth', 'myt'), 1

# -- Friends --
async def _get_friend_count(userid):
    from bot.models.user import Friend
    return await Friend.find(Friend.userid == userid).count()

async def check_friends_10(userid, event_type, data, current_progress):
    val = await _get_friend_count(userid)
    return val >= 10, val

async def check_friends_50(userid, event_type, data, current_progress):
    val = await _get_friend_count(userid)
    return val >= 50, val

async def check_friends_100(userid, event_type, data, current_progress):
    val = await _get_friend_count(userid)
    return val >= 100, val

# -- Referrals --
async def _get_invite_count(userid):
    from bot.models.user import Referral
    from bot.models.enums import ReferralType
    ref = await Referral.find_one(Referral.userid == userid, Referral.type == ReferralType.GENERAL)
    if not ref:
        return 0
    return await Referral.find(Referral.code == ref.code, Referral.type == ReferralType.SUB).count()

async def check_invite_10(userid, event_type, data, current_progress):
    val = await _get_invite_count(userid)
    return val >= 10, val

async def check_invite_100(userid, event_type, data, current_progress):
    val = await _get_invite_count(userid)
    return val >= 100, val

async def check_invite_250(userid, event_type, data, current_progress):
    val = await _get_invite_count(userid)
    return val >= 250, val

async def check_quests_failed_50(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('quests_failed', 0) if user else 0
    return val >= 50, val

async def check_dino_dead_10(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('dino_deaths', 0) if user else 0
    return val >= 10, val

async def check_items_discarded_1000(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('items_discarded', 0) if user else 0
    return val >= 1000, val

async def check_items_transferred_1000(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    val = user.settings.get('items_transferred', 0) if user else 0
    return val >= 1000, val

async def check_all_backgrounds_bought(userid, event_type, data, current_progress):
    from bot.models.user import User
    import bot.const as _const
    bgs_config = _const.GAME_SETTINGS.get('backgrounds', {}) or {}
    if not bgs_config:
        import json
        try:
            bgs_config = json.load(open(r'c:\Папки\коды\Telegram DinoGochi\DinoGochi\bot\json\backgrounds.json', encoding='utf-8'))
        except Exception:
            pass
    target_ids = {int(k) for k, v in bgs_config.items() if v.get('show', True)}
    if not target_ids:
        return False, 0
    user = await User.find_one(User.userid == userid)
    if not user:
        return False, 0
    user_bgs = set(user.saved.get('backgrounds', []))
    is_subset = target_ids.issubset(user_bgs)
    return is_subset, len(user_bgs)

async def check_friend_dev(userid, event_type, data, current_progress):
    from bot.config import conf
    from bot.models.user import Friend
    from bot.models.enums import FriendType
    dev_id = conf.bot_devs[0] if conf.bot_devs else 0
    if not dev_id:
        return False, 0
    conn = await Friend.find_one(
        Friend.userid == userid,
        Friend.friendid == dev_id,
        Friend.type == FriendType.FRIENDS
    )
    if conn:
        return True, 1
    conn2 = await Friend.find_one(
        Friend.userid == dev_id,
        Friend.friendid == userid,
        Friend.type == FriendType.FRIENDS
    )
    if conn2:
        return True, 1
    return False, 0

async def check_is_dev(userid, event_type, data, current_progress):
    """Тут всё же не совсем разработчик, как больше участник команды, поэтому не из конфига прав, а просто статичные."""
    is_dev = userid in [1191252229, 866830945, 6244045402]
    return is_dev, 1 if is_dev else 0

async def check_blacksmith_lost_1000(userid, event_type, data, current_progress):
    from bot.models.user import User
    user = await User.find_one(User.userid == userid)
    if not user:
        return False, 0
    count = user.settings.get('blacksmith_lost_items', 0)
    return count >= 1000, count

# Execute validation on load
try:
    AchievementsFileConfig(**ACHIEVEMENTS)
except Exception as e:
    from bot.modules.logs import log
    log(f"Achievements config validation failed: {e}", 4)

    raise e