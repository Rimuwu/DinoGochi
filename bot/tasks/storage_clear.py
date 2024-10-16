import pickle
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.localization import get_lang
from bot.modules.markup import markups_menu as m
from bot.taskmanager import add_task
from bot.modules.logs import log

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)

async def storage_clear():

    with open('.state-save/states.pkl', 'rb') as file:
        data = pickle.load(file)

    for chat_key in data:

        for user_key in data[chat_key]:

            res = await users.find_one({'userid': user_key}, 
                                       {'last_message_time': 1})
            if res is None or int(time()) - res['last_message_time'] > 3600:
                lang = await get_lang(user_key)
                try:
                    await bot.send_message(chat_key, '❌', 
                        reply_markup= await m(user_key, 'last_menu', lang))
                except Exception as e:
                    log(f"[storage_clear] Error on send message: {e}", 1)
                try:
                    await bot.delete_state(user_key, chat_key)
                except Exception as e:
                    log(f"[storage_clear] Error on delete state: {e}", 2)
                try:
                    await bot.reset_data(user_key, chat_key)
                except Exception as e:
                    log(f"[storage_clear] Error on reset data: {e}", 2)


# if __name__ != '__main__':
#     if conf.active_tasks:
#         add_task(storage_clear, 7200, 200)