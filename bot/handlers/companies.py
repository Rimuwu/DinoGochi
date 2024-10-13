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
from bot.modules.states_tools import ChoosePagesState, ChooseStepState
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
                    {'message': {},
                     'delete_steps': True
                     }
                    )

async def new_cycle(userid, chatid, lang, transmitted_data):
    state = transmitted_data['state']
    lang_data = get_all_locales('language_name')
    lang_options = {}

    for key, value in lang_data.items():
        col = await langs.count_documents({'lang': key})
        lang_options[
            value + f' ({col})'
        ] = key

    steps = [
        {
            'type': 'pages', 'name': 'lang',
            'data': {
                'options': lang_options,
                'horizontal': 2
            },
            'translate_message': True,
            'message': {
                'text': 'companies.lang'
            }
        },

        {
            'type': 'str', 'name': 'text',
            'data': {
                'max_len': 1024
            },
            'translate_message': True,
            'message': {
                'text': 'companies.text',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'str', 'name': 'name_button',
            'data': {
                'max_len': 100
            },
            'translate_message': True,
            'message': {
                'text': 'companies.name_button',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'str', 'name': 'button_url',
            'data': {
                'max_len': 1000
            },
            'translate_message': True,
            'message': {
                'text': 'companies.button_url',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'pages', 'name': 'parse_mode',
            'data': {
                'options': {
                    'HTML': 'HTML',
                    'Markdown': 'Markdown',
                    t('companies.no_parse', lang): None
                }
            },
            'translate_message': True,
            'message': {
                'text': 'companies.parse_mode'
            }
        },

        {
            'type': 'image', 'name': 'image',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.image_choose',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'bool', 'name': 'add_lang',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.add_new_lang',
                'reply_markup': answer_markup(lang)
            }
        }

    ]

    await ChooseStepState(pre_check, state, userid, chatid, lang, steps, transmitted_data)


async def pre_check(data, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    message = transmitted_data['message']
    state = transmitted_data['state']

    message[data['lang']
    ] = {
        'text': data['text'],
        'markup': [
            {data['name_button']: data['button_url']}
        ],
        'parse_mode': data['parse_mode'],
        'image': data['image']
    }
    transmitted_data['message'] = message

    if data['add_lang']:
        await new_cycle(userid, chatid, lang, transmitted_data)
        return

    steps = [
        {
            'type': 'int', 'name': 'owner',
            'data': {
                'max_int': 1000000000000,
                'min_int': 0
            },
            'translate_message': True,
            'message': {
                'text': 'companies.owner',
                'reply_markup': cancel_markup(lang)
            }
        },
        
        {
            'type': 'time', 'name': 'time_end',
            'data': {
                'max_int': 1000000000000,
                'min_int': 0
                },
            'translate_message': True,
            'message': {
                'text': 'companies.time_end',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'int', 'name': 'max_count',
            'data': {
                'max_int': 1000000000000,
                'min_int': 0
            },
            'translate_message': True,
            'message': {
                'text': 'companies.max_count',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'bool', 'name': 'priority',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.priority',
                'reply_markup': answer_markup(lang)
            }
        },

        {
            'type': 'bool', 'name': 'one_message',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.one_message',
                'reply_markup': answer_markup(lang)
            }
        },

        {
            'type': 'bool', 'name': 'pin_message',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.pin_message',
                'reply_markup': answer_markup(lang)
            }
        },

        {
            'type': 'int', 'name': 'coin_price',
            'data': {
                'max_int': 100,
                'min_int': 0
            },
            'translate_message': True,
            'message': {
                'text': 'companies.coin_price',
                'reply_markup': cancel_markup(lang)
            }
        },

        {
            'type': 'bool', 'name': 'delete_after',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.delete_after',
                'reply_markup': answer_markup(lang)
            }
        },

        {
            'type': 'bool', 'name': 'ignore_system_timeout',
            'data': {},
            'translate_message': True,
            'message': {
                'text': 'companies.ignore_system_timeout',
                'reply_markup': answer_markup(lang)
            }
        },

        {
            'type': 'int', 'name': 'min_timeout',
            'data': {
                'max_int': 1000000000000,
                'min_int': 0
            },
            'translate_message': True,
            'message': {
                'text': 'companies.min_timeout',
                'reply_markup': cancel_markup(lang)
            }
        },
        
        {
            'type': 'str', 'name': 'name',
            'data': {
                'max_len': 200
            },
            'translate_message': True,
            'message': {
                'text': 'companies.name',
                'reply_markup': cancel_markup(lang)
            }
        },
    ]

    await ChooseStepState(end, state, userid, chatid, lang, steps, transmitted_data)

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
async def companies_c(message: Message, state):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    userid = message.from_user.id
    
    comps = await companies.find({})
    options = {}

    for i in comps:
        options[i['name']] = i['_id']

    await ChoosePagesState(comp_info, state, userid, chatid, lang, options)

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