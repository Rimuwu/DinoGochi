
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.get_state import get_state
from bot.modules.localization import get_lang
from bot.modules.markup import markups_menu as m
from bot.taskmanager import add_task
from bot.modules.logs import log

from bot.modules.overwriting.DataCalsses import DBconstructor
states = DBconstructor(mongo_client.other.states)

async def storage_clear():

    states_data = await states.find({})
    for state in states_data:
        send_message = False
        fsm, userid, chatid = state['_id'].split(':') # fsm:1191252229:1191252229

        if 'data' not in state:
            await states.delete_one({'_id': state['_id']})
            send_message = True
        else:
            if 'time_start' in state['data']:
               if state['data']['time_start'] + 3600 <= time():
                   await states.delete_one({'_id': state['_id']})
                   send_message = True

        if send_message:
            lang = await get_lang(int(userid))
            try:
                await bot.send_message(int(chatid), '❌', 
                    reply_markup= await m(int(userid), 'last_menu', lang))
            except Exception as e:
                continue

            state = await get_state(int(userid), int(chatid))
            if state: await state.clear()

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(storage_clear, 1800, 15)