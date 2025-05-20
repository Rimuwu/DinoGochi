from ast import In
from re import M
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.handlers.start import start_game
from bot.modules.companies import create_company, end_company, generate_message, info
from bot.modules.data_format import seconds_to_str, str_to_seconds
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.inline import inline_menu
from bot.modules.localization import get_all_locales, get_lang, t
from bot.modules.managment.promo import use_promo
from bot.modules.markup import answer_markup, cancel_markup, confirm_markup
from bot.modules.overwriting.DataCalsses import DBconstructor
# from bot.modules.states_tools import ChoosePagesState, ChooseStepState
# from bot.modules.states_tools import ChooseStepState
from bot.modules.states_fabric.state_handlers import ChoosePagesStateHandler, ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import *
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command

users = DBconstructor(mongo_client.user.users)
companies = DBconstructor(mongo_client.other.companies)
langs = DBconstructor(mongo_client.user.lang)

@HDMessage
@main_router.message(IsAdminUser(), Command(commands=['create_company']))
async def create_company_com(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await new_cycle(userid, chatid, lang,
                    {'message': {}}
                    )

async def button_check(transmitted_data: dict):
    
    return_data = transmitted_data['return_data']
    if return_data['name_button'] == '0':
        del transmitted_data['steps'][4]
        transmitted_data['return_data']['button_url'] = None
        transmitted_data['return_data']['name_button'] = None

    return transmitted_data, True

async def new_cycle(userid, chatid, lang, transmitted_data):
    
    lang_data = get_all_locales('language_name')
    lang_options = {}

    for key, value in lang_data.items():
        col = await langs.count_documents({'lang': key})
        lang_options[
            value + f' ({col})'
        ] = key
    
    steps = [
        PagesStepData('lang', StepMessage('companies.lang', None, True), options=lang_options, horizontal=2),
        StringStepData('text', StepMessage('companies.text', cancel_markup(lang), True), max_len=1024),
        StringStepData('name_button', StepMessage('companies.name_button', cancel_markup(lang), True), max_len=100),
        BaseUpdateType(button_check),
        StringStepData('button_url', StepMessage('companies.button_url', cancel_markup(lang), True), max_len=1000),
        PagesStepData('parse_mode', StepMessage('companies.parse_mode', None, True), options={
            'HTML': 'HTML',
            'Markdown': 'Markdown',
            t('companies.no_parse', lang): None
        }),
        ImageStepData('image', StepMessage('companies.image_choose', cancel_markup(lang), True)),
        ConfirmStepData('add_lang', StepMessage('companies.add_new_lang', answer_markup(lang), True))
    ]

    # steps = [
    #     {
    #         'type': 'pages', 'name': 'lang',
    #         'data': {
    #             'options': lang_options,
    #             'horizontal': 2
    #         },
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.lang'
    #         }
    #     },

    #     {
    #         'type': 'str', 'name': 'text',
    #         'data': {
    #             'max_len': 1024
    #         },
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.text',
    #             'reply_markup': cancel_markup(lang)
    #         }
    #     },

    #     {
    #         'type': 'str', 'name': 'name_button',
    #         'data': {
    #             'max_len': 100
    #         },
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.name_button',
    #             'reply_markup': cancel_markup(lang)
    #         }
    #     },

    #     {
    #         'type': 'str', 'name': 'button_url',
    #         'data': {
    #             'max_len': 1000
    #         },
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.button_url',
    #             'reply_markup': cancel_markup(lang)
    #         }
    #     },

    #     {
    #         'type': 'pages', 'name': 'parse_mode',
    #         'data': {
    #             'options': {
    #                 'HTML': 'HTML',
    #                 'Markdown': 'Markdown',
    #                 t('companies.no_parse', lang): None
    #             }
    #         },
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.parse_mode'
    #         }
    #     },

    #     {
    #         'type': 'image', 'name': 'image',
    #         'data': {},
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.image_choose',
    #             'reply_markup': cancel_markup(lang)
    #         }
    #     },

    #     {
    #         'type': 'bool', 'name': 'add_lang',
    #         'data': {},
    #         'translate_message': True,
    #         'message': {
    #             'text': 'companies.add_new_lang',
    #             'reply_markup': answer_markup(lang)
    #         }
    #     }

    # ]

    # await ChooseStepState(pre_check, userid, chatid, lang, steps, transmitted_data)
    await ChooseStepHandler(
        pre_check, userid, chatid, lang, steps, transmitted_data).start()


async def pre_check(data, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    message = transmitted_data['message']

    message[data['lang']] = {
        'text': data['text'],
        'parse_mode': data['parse_mode'],
        'markup': [],
        'image': data['image']
    }
    if data['button_url'] is not None:
        message[data['lang']]['markup'] = [
            {data['name_button']: data['button_url']}
        ]

    transmitted_data['message'] = message

    if data['add_lang']:
        await new_cycle(userid, chatid, lang, transmitted_data)
        return

    steps = [
        IntStepData('owner', StepMessage('companies.owner', cancel_markup(lang), True), min_int=0, max_int=1000000000000),
        TimeStepData('time_end', StepMessage('companies.time_end', cancel_markup(lang), True), min_int=0, max_int=1000000000000),
        IntStepData('max_count', StepMessage('companies.max_count', cancel_markup(lang), True), min_int=0, max_int=1000000000000),
        ConfirmStepData('priority', StepMessage('companies.priority', answer_markup(lang), True)),
        ConfirmStepData('one_message', StepMessage('companies.one_message', answer_markup(lang), True)),
        ConfirmStepData('pin_message', StepMessage('companies.pin_message', answer_markup(lang), True)),
        IntStepData('coin_price', StepMessage('companies.coin_price', cancel_markup(lang), True), min_int=0, max_int=100),
        ConfirmStepData('delete_after', StepMessage('companies.delete_after', answer_markup(lang), True)),
        ConfirmStepData('ignore_system_timeout', StepMessage('companies.ignore_system_timeout', answer_markup(lang), True)),
        IntStepData('min_timeout', StepMessage('companies.min_timeout', cancel_markup(lang), True), min_int=0, max_int=1000000000000),
        StringStepData('name', StepMessage('companies.name', cancel_markup(lang), True), max_len=200),
        TimeStepData('min_reg_time', StepMessage('companies.min_reg_time', cancel_markup(lang), True), min_int=0, max_int=1000000000000),
    ]

    await ChooseStepHandler(
        end, userid, chatid, lang, steps, transmitted_data).start() 

async def end(data, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    message = transmitted_data['message']

    if data['owner'] == 0: data['owner'] = userid

    return_data = {
        'owner': data['owner'],
        'message': message,
        'time_end': data['time_end'],
        'count': data['max_count'],
        'priority': data['priority'],
        'one_message': data['one_message'],
        'pin_message': data['pin_message'],
        'coin_price': data['coin_price'],
        'min_timeout': data['min_timeout'],
        'delete_after': data['delete_after'],
        'ignore_system_timeout': data['ignore_system_timeout'],
        'name': data['name']
    }

    await create_company(**return_data)
    await bot.send_message(chatid, '✅')

@HDMessage
@main_router.message(Command(commands=['companies']), IsAdminUser())
async def companies_c(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    userid = message.from_user.id
    
    comps = await companies.find({})
    options = {}

    for i in comps:
        options[i['name']] = i['_id']
        
    await ChoosePagesStateHandler(
        comp_info, userid, chatid, lang, options).start()

    # await ChoosePagesState(comp_info, userid, chatid, lang, options)

async def comp_info(com_id, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    text, mrk = await info(com_id, lang)
    await bot.send_message(
        chatid, text, reply_markup=mrk
    )

@HDCallback
@main_router.callback_query(F.data.startswith('company_info') , IsAuthorizedUser())
async def company_info(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    data = callback.data.split()

    action = data[1]
    alt_id = data[2]

    c = await companies.find_one({'alt_id': alt_id})

    if c:
        if action == 'delete':
            await end_company(c['_id'])
            await bot.delete_message(chatid, callback.message.message_id)

        elif action == 'activate':
            await companies.update_one({'_id': c['_id']}, {'$set': {'status': True}})

            text, mrk = await info(c['_id'], lang)
            await bot.edit_message_text(
                text, None, chatid, callback.message.message_id, reply_markup=mrk
            )

        elif action == 'stop':
            await companies.update_one({'_id': c['_id']}, {'$set': {'status': False}})

            text, mrk = await info(c['_id'], lang)
            await bot.edit_message_text(
                text, None, chatid, callback.message.message_id, reply_markup=mrk
            )

        elif action == 'message':
            langs = c['message'].keys()
            
            for i in langs:
                await generate_message(userid, c['_id'], i, False)