from time import time

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.data_format import seconds_to_str
from bot.modules.notifications import user_notification
from bot.taskmanager import add_task
from bot.modules.donation import check_donations
from bot.modules.localization import  get_lang

subscriptions = mongo_client.user.subscriptions
users = mongo_client.bot.users

async def subscription_notification():
    data = list(await subscriptions.find({'sub_end': {'$lte': int(time()) - 86400}, 
                    'end_notif': False}).to_list(None)).copy()  

    for sub in data:
        try:
            chat_user = await bot.get_chat_member(sub['userid'], sub['userid'])
            lang = await get_lang(chat_user.user.id)
        except: lang = 'en'

        await user_notification(sub['userid'], 'donation', lang, 
                                end_text=seconds_to_str(time() - sub['sub_end'], lang),
                                add_way='subscription_end_day'
                                )
        await subscriptions.update_one({'_id': sub['_id']}, {'$set': {'end_notif': True}})

async def subscription_check():
    data = list(await subscriptions.find(
        {'sub_end': {'$lte': int(time())}}).to_list(None)).copy()  

    for sub in data:
        await subscriptions.delete_one({'_id': sub['_id']})

        try:
            chat_user = await bot.get_chat_member(sub['userid'], sub['userid'])
            lang = await get_lang(chat_user.user.id)
        except: lang = 'en'
        await user_notification(sub['userid'], 'donation', lang, 
                                add_way='subscription_end'
                                )

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(subscription_notification, 1800.0, 1.0)
        add_task(subscription_check, 300.0, 1.0)
        # add_task(check_donations, 120.0, 1.0)