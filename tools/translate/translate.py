import json
import time
import random

import emoji

import translators
from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0

from_l = 'ru'
to_langs = ['en']

with open(f'languages/{from_l}.json', encoding='utf-8') as f: 
    main_lang = json.load(f) # type: dict

def trs(text: str, trans='bing'):
    from_language = from_l
    to_lang = ro_l
    if trans == 'myMemory' and from_language == 'ru': from_language = 'ru-RU'

    elif trans == 'myMemory' and to_lang == 'uk': to_lang = 'uk-UA'
    elif trans == 'baidu' and to_lang == 'uk': to_lang = 'ukr'

    if text:
        try: lang = detect(text)
        except: lang = 'emoji'

        if lang not in ['en', 'it', 'emoji']:
            ret = translators.translate_text(text, 
                from_language=from_language,
                to_language=to_lang, translator=trans) 
            print("\n#TEXT#", text, '\n#translatore#', trans, '\nRETURN TEXT#', ret, '\nlang', lang)
            return ret

    return text

def trs_circul(s):
    # myMemory bing papago modernMt reverso
    res = s
    for i in range(700):
        translators = ['myMemory', 'bing', 'modernMt']#['bing', 'modernMt', 'myMemory'] # 'myMemory',  reverso !papago!
        trans = 'bing'
        res = ''

        for trans in translators:
            r_t = random.uniform(0, 1)
            time.sleep(r_t)
        
            try:
                try:
                    res = trs(s, trans)
                    return res
                except Exception as E:
                    trans = random.choice(translators)
                    res = trs(s, trans)

                    return res
            except Exception as E: print(E)

    return res

k_list = ['*', '`']

def dict_string(s, s_key):

    if type(s) == str:
        if len(s) == 1: return s

        if s_key not in ['data', 'callback', 'inline_menu']:
            repl_words = {
                '(111!)': {'text': '\n', 'translate': False},
                '(222!)': {'text': '\n\n', 'translate': False},
                '(333!)': {'text': '\n\n\n', 'translate': False},
                '(444!)': {'text': '\n\n\n\n', 'translate': False},
                '(100!)': {'text': 'ᴜsᴇʀ ᴘʀᴏғɪʟᴇ', 'translate': False},
                '(200!)': {'text': 'ʟᴇᴠᴇʟ', 'translate': False},
                '(300!)': {'text': 'ᴅɪɴᴏsᴀᴜʀs', 'translate': False},
                '(400!)': {'text': 'ɪɴᴠᴇɴᴛᴏʀʏ', 'translate': False},
                '(500!)': {'text': '->', 'translate': False},
                '(600!)': {'text': '</code>', 'translate': False},
                '(700!)': {'text': '<code>', 'translate': False},
                '(800!)': {'text': '<i>', 'translate': False},
                '(900!)': {'text': '</i>', 'translate': False},
            }
            for key, item in repl_words.items(): s = s.replace(item['text'], key)

            word, st = '', False
            i, new_text = '', ''

            for i in emoji.emoji_list(s):
                k_name = f'({len(repl_words)}{len(repl_words)}!)'
                repl_words[k_name] = {
                    'text': i['emoji'],
                    'translate': False
                }
                s = s.replace(i['emoji'], k_name)
                word = ''

            word, st = '', False

            for i in s:
                if i == '{':
                    st = True
                    word += i

                if i == '}':
                    st = False
                    word += i

                    word = word[1:]

                    k_name = f'({len(repl_words)}{len(repl_words)}!)'
                    repl_words[k_name] = {
                        'text': word,
                        'translate': False
                    }
                    s = s.replace(word, k_name)

                    word = ''

                if st: word += i

            for i in s:
                if i in k_list and st: 
                    st = False
                    translate_st = True
                    word += i
                    end_word = word[1:-1]

                    if len(end_word) == 1: translate_st = False

                    k_name = f'({len(repl_words)}{len(repl_words)}!)'
                    repl_words[k_name] = {
                        'text': end_word,
                        'translate': translate_st,
                        'sml': i
                    }
                    s = s.replace(word, k_name)
                    word = ''

                elif i in k_list and not st: st = True
                if st: word += i

            if i != s: new_text = trs_circul(s)

            for i in range(4):
                for key, data in repl_words.items():

                    if data['translate']:
                        if len(data['text']) > 3 and data['text'][1] == '(' and data['text'][-2] == ')': txt = data['text']
                        else:
                            txt = trs_circul(data['text'])
                            print(txt, 'txt')
                    else: txt = data['text']
                    
                    if 'sml' in data:
                        txt = data['sml'] + txt + data['sml']

                    new_text = new_text.replace(key, txt) #type: ignore

            return new_text

    elif  type(s) == int: return s

    elif type(s) == list:
        lst = []
        for i in s: lst.append(dict_string(i, s_key))
        return lst

    elif type(s) == dict:
        dct = {}
        for key, value in s.items(): 
            if key not in ['data', 'callback']:
                dct[key] = dict_string(value, s_key)
            else: dct[key] = value
        return dct
    return s

def save(data, lang, dr='languages'):
    with open(f'{dr}/{lang}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
start = time.time()

for ro_l in to_langs:
    with open(f'languages/{ro_l}.json', encoding='utf-8') as f: 
        add_lang = json.load(f) # type: dict
    
    with open(f'saves/{ro_l}.json', encoding='utf-8') as f: 
        save_from = json.load(f) # type: dict

    if not add_lang: add_lang[ro_l] = {}
    if not save_from: save_from[from_l] = {}

    for key, value in main_lang[from_l].items():

        if key in save_from[from_l]:
            if value != save_from[from_l][key]:
                del add_lang[ro_l][key]

        if type(value) == dict:
            if key not in add_lang[ro_l]: add_lang[ro_l][key] = {}
            if key not in save_from[from_l]: save_from[from_l][key] = {}

            for key1, value1 in value.items():

                if key1 not in add_lang[ro_l][key]:
                    add_lang[ro_l][key][key1] = dict_string(value1, key1)
                    save_from[from_l][key][key1] = value1

                    save(add_lang, ro_l)
                    save(save_from, ro_l, 'saves')

        elif key not in add_lang[ro_l]:
            add_lang[ro_l][key] = dict_string(value, key)
            save_from[from_l][key] = value

            save(add_lang, ro_l)
            save(save_from, ro_l, 'saves')

print('END translate', time.time() - start)

