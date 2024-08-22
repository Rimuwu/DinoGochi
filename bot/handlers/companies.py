from bot.config import mongo_client
from bot.exec import bot
from bot.handlers.start import start_game
from bot.modules.companies import create_company
from bot.modules.data_format import seconds_to_str, str_to_seconds, user_name
from bot.modules.decorators import HDMessage
from bot.modules.inline import inline_menu
from bot.modules.localization import get_lang, t, get_all_locales
from bot.modules.markup import cancel_markup, confirm_markup, answer_markup
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.managment.promo import use_promo
from telebot.types import Message
from bot.modules.states_tools import ChooseStepState

users = DBconstructor(mongo_client.user.users)
langs = DBconstructor(mongo_client.user.lang)

@bot.message_handler(pass_bot=True, commands=['create_company'])
@HDMessage
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

    await ChooseStepState(pre_check, userid, chatid, lang, steps, transmitted_data)


async def pre_check(data, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    message = transmitted_data['message']

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
        }
    ]

    await ChooseStepState(end, userid, chatid, lang, steps, transmitted_data)

async def end(data, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    message = transmitted_data['message']
    
    if data['owner'] == 0:
        data['owner'] = userid

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
        'ignore_system_timeout': data['ignore_system_timeout']
    }

    await create_company(**return_data)
    await bot.send_message(chatid, '✅')