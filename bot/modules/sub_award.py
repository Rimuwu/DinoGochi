from bot.const import GAME_SETTINGS as GS
from bot.dbmanager import mongo_client

from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import user_in_chat

onetime_rewards = DBconstructor(mongo_client.other.onetime_rewards)
users = DBconstructor(mongo_client.user.users)

async def check_for_entry(user_id: int, en_type: str):
    assert en_type in ['channel', 'forum'], "Invalid en_type provided"

    chat_id = GS['channel_id'] if en_type == 'channel' else GS['forum_id']
    return await user_in_chat(user_id, chat_id)

async def check_award(user_id: int, en_type: str):
    assert en_type in ['channel', 'forum'], "Invalid en_type provided"

    check = await onetime_rewards.find_one({'user_id': user_id, 'type': en_type}, comment='check_award')
    return check

async def award_for_entry(user_id: int, en_type: str):
    assert en_type in ['channel', 'forum'], "Invalid en_type provided"

    check = await onetime_rewards.find_one({'user_id': user_id, 'type': en_type}, comment='award_for_entry_check')
    if not check:
        if en_type == 'channel':
            coins = GS['channel_subs_reward']
        else:
            coins = GS['forum_subs_reward']

        data = {
            'user_id': user_id,
            'coins': coins,
            'type': en_type,
        }

        await users.update_one({'userid': user_id}, 
                    {'$inc': {'super_coins': coins}}, comment='award_for_entry_update')
        log(f'User {user_id} entered {en_type} and received {coins} super_coins', 1, 'award_for_entry')

        return await onetime_rewards.insert_one(data, comment='award_for_entry')
    return False

async def leave_from_chat(user_id: int, en_type: str):
    assert en_type in ['channel', 'forum'], "Invalid en_type provided"

    check = await onetime_rewards.find_one({'user_id': user_id, 'type': en_type}, comment='leave_from_chat_check')

    if check:
        coins = check['coins']

        await onetime_rewards.delete_one({'_id': check['_id']}, comment='leave_from_chat_delete')

        await users.update_one({'userid': user_id},
                                {'$inc': {'super_coins': -coins}}, comment='leave_from_chat_update')
        log(f'User {user_id} left from {en_type} and lost {coins} super_coins', 1, 'leave_from_chat')

        await user_notification(user_id, 'leave_sub_award')

        return True
    return False
