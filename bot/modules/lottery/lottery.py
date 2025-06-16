from re import A
from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot

from random import shuffle

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.data_format import list_to_inline, random_code
from bot.modules.items.item import AddItemToUser, ItemData, get_items_names
from bot.modules.localization import get_lang, t

from time import time, strftime, localtime

from bot.modules.user.user import take_coins

lottery = DBconstructor(mongo_client.lottery.lottery)
lottery_members = DBconstructor(mongo_client.lottery.members)

async def generation_code():
    code = f'{random_code(4)}'
    if await lottery.find_one({'alt_id': code}, comment='generation_code_companies'):
        code = await generation_code()
    return code

async def create_lottery(channel_id: int, message_id: int, time_end, prizes: dict, lang: str, max_users: int):
    """
        'prizes': {
            '1': {
                'items': [{'items_data': {'item_id': str}, 'count': Optional[int]}],
                'coins': 0,
                'count': 0
            }
        }
    
    """
    
    data = {
        'alt_id': await generation_code(),

        'channel_id': channel_id,
        'message_id': message_id,
        'time_start': int(time()),
        'time_end': int(time()) + time_end,
        
        'max_users': max_users, # 0 - бесконечно

        'prizes': prizes,
        'lang': lang
    }
    
    await lottery.insert_one(data, comment='create_lottery')
    await create_message(data['alt_id'], end=False)

async def create_lottery_member(userid: int, alt_id: str):

    find_lot = await lottery.find_one({'alt_id': alt_id}, comment='find_lottery')
    if find_lot:

        in_lottery = await lottery_members.find_one({'userid': userid, 
                                                     'lot_id': find_lot['_id']}, comment='find_lottery_member')
        col_lottery_members = await lottery_members.count_documents({'lot_id': find_lot['_id']}, comment='find_lottery_member')

        if col_lottery_members >= find_lot['max_users'] and find_lot['max_users'] != 0:
            return False, 'lottery_full'
        
        if not in_lottery:
            
            data = {
                'userid': userid,
                'lot_id': find_lot['_id']
            }

            await lottery_members.insert_one(data, comment='create_lottery_member')
            return True, 'lottery_member_created'

        return False, 'lottery_member_exist'
    return False, 'lottery_not_found'

async def delete_lottery(lot_id: ObjectId):
    
    await lottery.delete_one({'_id': lot_id}, comment='delete_lottery')
    await lottery_members.delete_many({'lot_id': lot_id}, comment='delete_lottery_member')


async def create_button(alt_id: str):
    
    find_lot = await lottery.find_one({'alt_id': alt_id}, comment='find_lottery')
    if not find_lot: 
        raise Exception('lottery_not_found for create button')

    user_now = await lottery_members.count_documents({'lot_id': find_lot['_id']}, comment='find_lottery_member')

    max_users = find_lot['max_users']
    lang = find_lot['lang']
    if max_users == 0: max_users = '♾️'

    text = t('lottery.button', user_now=user_now, max_users=max_users, lang=lang)
    callback_data = f'lottery_enter:{alt_id}'

    return list_to_inline([{text: callback_data}])

async def create_message(alt_id: str, end: bool = False): 

    lot = await lottery.find_one({'alt_id': alt_id}, comment='create_message')
    if lot:

        channel_id = lot['channel_id']
        lang = lot['lang']
        message = ''
        markup = None

        cap = t('lottery.cap', lang=lang)
        
        prizes_text = t('lottery.prizes_text', lang=lang)

        for key, value in lot['prizes'].items():
            prizes_text += f'#{key}. (👥 x{value["count"]}) — '
            if value['coins']:
                prizes_text += f'{value["coins"]} 🪙'
                if value['items']: prizes_text += ', '

            if value['items']:
                itm_names = get_items_names(value['items'], lot['lang'])
    
                prizes_text += f'{itm_names}'
            prizes_text += '\n'
        
        if not end:
            time_text = strftime('%d.%m.%Y %H:%M', localtime(lot['time_end']))
            now_time = strftime('%H:%M', localtime(lot['time_start']))
            
            time_end_text = t('lottery.time_end_text', now_time=now_time, time_text=time_text, lang=lang)

            markup = await create_button(lot['alt_id'])

        else:
            time_end_text = t('lottery.end_text', lang=lang)

        message += cap + prizes_text + time_end_text
        
        if lot['message_id']:
            await bot.edit_message_text(message, chat_id=channel_id, message_id=lot['message_id'], reply_markup=markup, parse_mode='Markdown')
        else:
            mes = await bot.send_message(channel_id, message, reply_markup=markup, parse_mode='Markdown')

            await lottery.update_one({'_id': lot['_id']}, 
                                     {'$set': {'message_id': mes.message_id}}, comment='create_message')


async def winers_text(winers: dict, lang: str):
    """
    
    winners: {
        "1": [id, id, id]
    }
    
    """
    text = ''

    cap = t('lottery.winners_cap', lang)

    winers_text = ''
    for key, value in winers.items():
        users_len = 0
        if len(value) != 0: 
            winers_text += f"#{key} | "
    
            for user_id in value:
                if users_len >= 10:
                    winers_text += '...'
                    users_len = 0
                    break

                try:
                    user = await bot.get_chat_member(chat_id=user_id, user_id=user_id)
                except:
                    user = None

                if user:
                    users_len += 1
                    if user.user.username:
                        winers_text += f"@{user.user.username} "
                    else:
                        winers_text += f"{user.user.first_name} "
    
            winers_text += '\n'

    footer = t('lottery.winners_footer', lang)

    text += cap + winers_text + footer
    return text

async def find_winners(lot_id: ObjectId):
    winers = {}
    lotter = await lottery.find_one({'_id': lot_id}, comment='find_winners')
    
    if lotter:
        members = await lottery_members.find({'lot_id': lot_id}, comment='find_winners')

        shuf_members = list(members)
        shuffle(shuf_members)

        for key in lotter['prizes'].keys():
            winers[key] = []

        all_get = False
        for user in shuf_members:
            if all_get: break

            for key, value in winers.items():
                if len(winers[key]) < lotter['prizes'][key]['count']:
                    winers[key].append(user['userid'])

                    if key == list(winers.keys())[-1]:
                        all_get = True
                    break

    return winers

async def message_to_winer(user_id: int, win_data: dict):
    lang = await get_lang(user_id)

    text = t('lottery.user_cap', lang)

    if win_data.get('coins', 0):
        text += f'• {win_data["coins"]} 🪙\n'

    if win_data.get('items', []):
        text += f'• {get_items_names(win_data["items"], lang)}\n'

    try:
        await bot.send_message(user_id, text)
    except: pass

async def items_to_winer(user_id: int, win_data: dict):
    """
    win_data['items'] = [{'items_data': {'item_id': str}, 'count': Optional[int]}]

    """

    if win_data.get('items', []):
        for item in win_data['items']:
            
            item_data = ItemData(**item['items_data'])

            count = item.get('count', 1)
            await AddItemToUser(user_id, item_data, count, 'home', None)

    coins = win_data.get('coins', 0)
    if coins: await take_coins(user_id, coins, True)

async def end_lottery(lot_id: ObjectId):
    
    lotter = await lottery.find_one({'_id': lot_id}, comment='end_lottery')
    if lotter:
        try:
            await create_message(lotter['alt_id'], end=True)
        except: pass

        winers = await find_winners(lot_id)
        for key, value in winers.items():
            win_data = lotter['prizes'][key]
            for user_id in value:
                await items_to_winer(user_id, win_data)
                await message_to_winer(user_id, win_data)

        text = await winers_text(winers, lotter['lang'])

        try:
            await bot.send_message(lotter['channel_id'], text)
        except: pass

        await delete_lottery(lot_id)