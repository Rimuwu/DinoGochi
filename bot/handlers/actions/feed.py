
from telebot.types import Message

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.dinosaur import Dino
from bot.modules.inventory_tools import start_inv
from bot.modules.item import get_data as get_item_data
from bot.modules.item import get_name
from bot.modules.item_tools import use_item
from bot.modules.markup import feed_count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_tools import ChooseStepState
from bot.modules.user import User
from bot.modules.localization import  get_lang
from bot.modules.over_functions import send_message

items = mongo_client.items.items

async def adapter_function(return_dict, transmitted_data):
    count = return_dict['count']
    item = transmitted_data['item']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    dino = transmitted_data['dino']
    lang = transmitted_data['lang']
    
    send_status, return_text = await use_item(userid, chatid, lang, item, count, dino)
    
    if send_status:
        await send_message(chatid, return_text, parse_mode='Markdown', reply_markup= await m(userid, 'last_menu', lang))

async def inventory_adapter(item, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    dino: Dino = transmitted_data['dino']

    transmitted_data['item'] = item

    limiter = 100 # Ограничение по количеству использований за раз
    item_data = get_item_data(item['item_id'])
    item_name = get_name(item['item_id'], lang)

    base_item = await items.find_one({'owner_id': userid, 'items_data': item})

    if base_item:
        if 'abilities' in item.keys() and 'uses' in item['abilities']:
            max_count = base_item['count'] * base_item['items_data']['abilities']['uses']
        else: max_count = base_item['count']

        if max_count > limiter: max_count = limiter

        percent = 1
        age = await dino.age
        if age.days >= 10:
            percent, repeat = await dino.memory_percent('games', item['item_id'], False)

        steps = [
            {"type": 'int', "name": 'count', "data": {
                "max_int": max_count, "autoanswer": False}, 
             "translate_message": True,
                'message': {'text': 'css.wait_count', 
                            'reply_markup': feed_count_markup(
                                dino.stats['eat'], int(item_data['act'] * percent), max_count, item_name, lang)}}
                ]
        await ChooseStepState(adapter_function, userid, chatid, 
                              lang, steps, 
                              transmitted_data=transmitted_data)

@bot.message_handler(pass_bot=True, text='commands_name.actions.feed')
async def feed(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    user = await User().create(userid)
    
    transmitted_data = {
        'chatid': chatid,
        'lang': lang,
        'dino': await user.get_last_dino()
    }
    
    await start_inv(inventory_adapter, userid, chatid, lang, ['eat'], changing_filters=False, transmitted_data=transmitted_data)