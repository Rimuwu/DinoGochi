

from bson import ObjectId
from bot.modules.data_format import seconds_to_str
from bot.modules.localization import t
from bot.exec import bot

from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

async def send_mood_log(dino_id: ObjectId, lang: str, userid: int):
    mood_list = await dino_mood.find(
        {'dino_id': dino_id}, comment='dino_profile_dino_profile')
    mood_dict, text, event_text = {}, '', ''
    res, event_end = 0, 0

    for mood in mood_list:
        if mood['type'] not in ['breakdown', 'inspiration']:
        
            key = mood['action']
            if key not in mood_dict:
                mood_dict[key] = {'col': 1, 'unit': mood['unit']}
            else:
                mood_dict[key]['col'] += 1
            res += mood['unit']

        else:
            event_text = t(f'mood_log.{mood["type"]}.{mood["action"]}', lang)
            event_end = mood['end_time'] -mood['start_time'] 

    text = t('mood_log.info', lang, result=res)
    if event_text: 
        event_time = seconds_to_str(event_end, lang, True)
        text += t('mood_log.event_info', lang, action=event_text, event_time=event_time)

    text += '\n'

    for key, data_m in mood_dict.items():
        em = '💚'
        if data_m['unit'] <= 0: em = '💔'
        act = t(f'mood_log.{key}', lang)
        
        unit = str(data_m['unit'] * data_m['col'])
        if data_m['unit'] > 0: unit = '+'+unit

        text += f'{em} {act}: `{unit}` '
        if data_m['col'] > 1: text += f'x{data_m["col"]}'
        text += '\n'

    await bot.send_message(userid, text, parse_mode='Markdown')