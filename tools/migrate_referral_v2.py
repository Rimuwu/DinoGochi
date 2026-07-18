"""
Migration script: migrate_referral_v2.py

Updates `referral_lvl` on all SUB (invitee) documents from actual User.lvl,
and marks all reward levels <= current referral level as given (for invitee)
and claimed (for inviter).

Run once at bot startup (or manually). Safe to re-run.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from bot.dbmanager import mongo_client, init_beanie_odm
    from bot.models.user import Referral, User
    from bot.models.enums import ReferralType
    from bot.modules.logs import log

    await init_beanie_odm(mongo_client._real_client)

    log("=== Referral V2 migration started ===", 1, "migrate_referral_v2")

    REWARD_LEVELS = [1, 5, 15, 30, 50]

    subs = await Referral.find(Referral.type == ReferralType.SUB).to_list()
    log(f"Found {len(subs)} invitee (SUB) referral documents", 1, "migrate_referral_v2")

    updated_subs = 0
    updated_generals = 0

    generals_map = {}

    for sub in subs:
        user = await User.find_one(User.userid == sub.userid)
        if not user:
            continue

        actual_lvl = user.lvl
        sub_changed = False

        if sub.referral_lvl != actual_lvl:
            sub.referral_lvl = actual_lvl
            sub_changed = True

        inviter_doc = generals_map.get(sub.code)
        if not inviter_doc and sub.code:
            inviter_doc = await Referral.find_one(
                Referral.code == sub.code,
                Referral.type == ReferralType.GENERAL
            )
            if inviter_doc:
                generals_map[sub.code] = inviter_doc

        inviter_changed = False

        for r_lvl in REWARD_LEVELS:
            if actual_lvl >= r_lvl:
                if r_lvl not in sub.invited_lvl_rewards_given:
                    sub.invited_lvl_rewards_given.append(r_lvl)
                    sub_changed = True

                if inviter_doc and r_lvl not in inviter_doc.lvl_rewards_claimed:
                    inviter_doc.lvl_rewards_claimed.append(r_lvl)
                    inviter_changed = True

        if sub_changed:
            await sub.save()
            updated_subs += 1

        if inviter_changed and inviter_doc:
            await inviter_doc.save()
            updated_generals += 1

    log(
        f"Migration complete. Updated subs: {updated_subs}, updated generals: {updated_generals}",
        1, "migrate_referral_v2"
    )


if __name__ == '__main__':
    asyncio.run(main())
