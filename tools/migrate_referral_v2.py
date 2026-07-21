"""
Migration script: migrate_referral_v2.py

Updates `referral_lvl` on all SUB (invitee) documents from actual User.lvl,
marks all reward levels <= current referral level as given (for invitee),
and migrates any existing inviter claims to per-sub `inviter_claimed_lvls`.

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

    generals_map = {}

    for sub in subs:
        user = await User.find_one(User.userid == sub.userid)
        if not user:
            continue

        actual_lvl = user.lvl
        sub_changed = False

        if sub.update_referral_lvl(actual_lvl):
            sub_changed = True

        inviter_doc = generals_map.get(sub.code)
        if not inviter_doc and sub.code:
            inviter_doc = await Referral.find_one(
                Referral.code == sub.code,
                Referral.type == ReferralType.GENERAL
            )
            if inviter_doc:
                generals_map[sub.code] = inviter_doc

        for r_lvl in REWARD_LEVELS:
            if actual_lvl >= r_lvl:
                if sub.add_invited_lvl_reward_given(r_lvl):
                    sub_changed = True

        # If inviter claimed this level globally under legacy system, migrate 1 claim to this sub
        if inviter_doc and inviter_doc.lvl_rewards_claimed:
            for r_lvl in inviter_doc.lvl_rewards_claimed:
                if r_lvl in sub.invited_lvl_rewards_given and r_lvl not in sub.inviter_claimed_lvls:
                    other_claimed_count = sum(
                        1 for s in subs
                        if s.code == sub.code and r_lvl in s.inviter_claimed_lvls
                    )
                    if other_claimed_count < 1:
                        if sub.add_inviter_claimed_lvl(r_lvl):
                            sub_changed = True

        if sub_changed:
            await sub.save()
            updated_subs += 1

    log(
        f"Migration complete. Updated subs: {updated_subs}",
        1, "migrate_referral_v2"
    )


if __name__ == '__main__':
    asyncio.run(main())
