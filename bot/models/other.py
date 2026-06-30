from bot.models.dinosaur import State
from typing import List, Dict, Any, Optional, Union
from beanie import Document
from bson.objectid import ObjectId
from pydantic import Field
from pymongo import IndexModel, ASCENDING

class Lottery(Document):
    alt_id: str = ""
    channel_id: int = 0
    message_id: Optional[int] = None
    time_start: int = 0
    time_end: int = 0
    max_users: int = 0
    prizes: Dict[str, Any] = Field(default_factory=dict)
    lang: str = "en"

    class Settings:
        name = "lottery"

    @classmethod
    async def generation_code(cls) -> str:
        from bot.modules.data_format import random_code
        code = f'{random_code(4)}'
        if await cls.find_one(cls.alt_id == code):
            code = await cls.generation_code()
        return code

    @classmethod
    async def create_lottery(cls, channel_id: int, message_id: int, time_end: int, prizes: dict, lang: str, max_users: int):
        import time
        alt_id = await cls.generation_code()
        data = cls(
            alt_id=alt_id,
            channel_id=channel_id,
            message_id=message_id,
            time_start=int(time.time()),
            time_end=int(time.time()) + time_end,
            max_users=max_users,
            prizes=prizes,
            lang=lang
        )
        await data.insert()
        await cls.create_message(alt_id, end=False)

    @classmethod
    async def delete_lottery(cls, lot_id: ObjectId):
        lot = await cls.find_one(cls.id == lot_id)
        if lot:
            await lot.delete()
            await LotteryMember.find(LotteryMember.lot_id == str(lot_id)).delete()

    @classmethod
    async def create_button(cls, alt_id: str):
        from bot.modules.localization import t
        from bot.modules.data_format import list_to_inline
        find_lot = await cls.find_one(cls.alt_id == alt_id)
        if not find_lot: 
            raise Exception('lottery_not_found for create button')

        user_now = await LotteryMember.find(LotteryMember.lot_id == str(find_lot.id)).count()
        max_users = find_lot.max_users
        lang = find_lot.lang
        if max_users == 0: 
            max_users = '♾️'

        text = t('lottery.button', user_now=user_now, max_users=max_users, lang=lang)
        callback_data = f'lottery_enter:{alt_id}'
        return list_to_inline([{text: callback_data}])

    @classmethod
    async def create_message(cls, alt_id: str, end: bool = False): 
        import time
        from bot.modules.localization import t
        from bot.modules.items.item import get_items_names
        from bot.exec import bot

        lot = await cls.find_one(cls.alt_id == alt_id)
        if lot:
            channel_id = lot.channel_id
            lang = lot.lang
            message = ''
            markup = None

            cap = t('lottery.cap', lang=lang)
            prizes_text = t('lottery.prizes_text', lang=lang)

            for key, value in lot.prizes.items():
                prizes_text += f'#{key}. (👥 x{value["count"]}) — '
                if value['coins']:
                    prizes_text += f'{value["coins"]} 🪙'
                    if value['items']: 
                        prizes_text += ', '

                if value['items']:
                    itm_names = get_items_names(value['items'], lot.lang)
                    prizes_text += f'{itm_names}'
                prizes_text += '\n'
            
            if not end:
                time_text = time.strftime('%d.%m.%Y %H:%M', time.localtime(lot.time_end))
                now_time = time.strftime('%H:%M', time.localtime(lot.time_start))
                time_end_text = t('lottery.time_end_text', now_time=now_time, time_text=time_text, lang=lang)
                markup = await cls.create_button(lot.alt_id)
            else:
                time_end_text = t('lottery.end_text', lang=lang)

            message += cap + prizes_text + time_end_text
            
            if lot.message_id:
                await bot.edit_message_text(message, chat_id=channel_id, message_id=lot.message_id, reply_markup=markup, parse_mode='Markdown')
            else:
                mes = await bot.send_message(channel_id, message, reply_markup=markup, parse_mode='Markdown')
                await lot.update({'$set': {'message_id': mes.message_id}})

    @classmethod
    async def winers_text(cls, winers: dict, lang: str) -> str:
        from bot.modules.localization import t
        from bot.exec import bot

        text = ''
        cap = t('lottery.winners_cap', lang)
        Lottery.winers_text = ''
        for key, value in winers.items():
            users_len = 0
            if len(value) != 0: 
                Lottery.winers_text += f"#{key} | "
        
                for user_id in value:
                    if users_len >= 10:
                        Lottery.winers_text += '...'
                        users_len = 0
                        break

                    try:
                        user = await bot.get_chat_member(chat_id=user_id, user_id=user_id)
                    except:
                        user = None

                    if user:
                        users_len += 1
                        if user.user.username:
                            Lottery.winers_text += f"@{user.user.username} "
                        else:
                            Lottery.winers_text += f"{user.user.first_name} "
        
                Lottery.winers_text += '\n'

        footer = t('lottery.winners_footer', lang)
        text += cap + Lottery.winers_text + footer
        return text

    @classmethod
    async def find_winners(cls, lot_id: ObjectId) -> dict:
        from random import shuffle
        winers = {}
        lotter = await cls.find_one(cls.id == lot_id)
        
        if lotter:
            members = await LotteryMember.find(LotteryMember.lot_id == str(lot_id)).to_list()
            shuf_members = list(members)
            shuffle(shuf_members)

            for key in lotter.prizes.keys():
                winers[key] = []

            all_get = False
            for user in shuf_members:
                if all_get: 
                    break

                for key, value in winers.items():
                    if len(winers[key]) < lotter.prizes[key]['count']:
                        winers[key].append(user.userid)

                        if key == list(winers.keys())[-1]:
                            all_get = True
                        break

        return winers

    @classmethod
    async def end_lottery(cls, lot_id: ObjectId):
        from bot.exec import bot
        lotter = await cls.find_one(cls.id == lot_id)
        if lotter:
            try:
                await cls.create_message(lotter.alt_id, end=True)
            except: 
                pass

            winers = await cls.find_winners(lot_id)
            for key, value in winers.items():
                win_data = lotter.prizes[key]
                for user_id in value:
                    await LotteryMember.items_to_winner(user_id, win_data)
                    await LotteryMember.message_to_winner(user_id, win_data)

            text = await cls.winers_text(winers, lotter.lang)
            try:
                await bot.send_message(lotter.channel_id, text)
            except: 
                pass

            await cls.delete_lottery(lot_id)

class LotteryMember(Document):
    lot_id: str = ""
    userid: Optional[int] = None

    class Settings:
        name = "lottery_members"

    @classmethod
    async def create_member(cls, userid: int, alt_id: str):
        from bot.models.other import Lottery
        find_lot = await Lottery.find_one(Lottery.alt_id == alt_id)
        if find_lot:
            in_lottery = await cls.find_one(cls.userid == userid, cls.lot_id == str(find_lot.id))
            col_lottery_members = await cls.find(cls.lot_id == str(find_lot.id)).count()

            if col_lottery_members >= find_lot.max_users and find_lot.max_users != 0:
                return False, 'lottery_full'
            
            if not in_lottery:
                data = cls(
                    userid=userid,
                    lot_id=str(find_lot.id)
                )
                await data.insert()
                return True, 'lottery_member_created'

            return False, 'lottery_member_exist'
        return False, 'lottery_not_found'

    @classmethod
    async def message_to_winner(cls, user_id: int, win_data: dict):
        from bot.modules.localization import get_lang, t
        from bot.modules.items.item import get_items_names
        from bot.exec import bot

        lang = await get_lang(user_id)
        text = t('lottery.user_cap', lang)

        if win_data.get('coins', 0):
            text += f'• {win_data["coins"]} 🪙\n'

        if win_data.get('items', []):
            text += f'• {get_items_names(win_data["items"], lang)}\n'

        try:
            await bot.send_message(user_id, text)
        except: 
            pass

    @classmethod
    async def items_to_winner(cls, user_id: int, win_data: dict):
        from bot.modules.items.item import AddItemToUser, get_item_dict
        from bot.modules.user.user import take_coins

        if win_data.get('items', []):
            for item in win_data['items']:
                item_dict = get_item_dict(
                    item['items_data']['item_id'], 
                    item['items_data'].get('abilities', {})
                )
                item_id = item['items_data']['item_id']
                abilities = item_dict.get('abilities', {})
                count = item.get('count', 1)
                await AddItemToUser(user_id, item_id, count, abilities)

        coins = win_data.get('coins', 0)
        if coins: 
            await take_coins(user_id, coins, True)

class Online(Document):
    userid: Optional[int] = None
    game_type: str = ""
    joined_time: int = 0

    class Settings:
        name = "online"

class Management(Document):
    id: str = Field(alias="_id")
    data: Optional[List[Any]] = None
    ids: Optional[List[Any]] = None
    time: Optional[int] = None
    all_count: Optional[int] = None

    class Settings:
        name = "management"

class Statistic(Document):
    date: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "statistic"

class Event(Document):
    type: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    time_start: int = 0
    time_end: int = 0

    class Settings:
        name = "events"

    @classmethod
    async def get_event(cls, event_type: str = '') -> dict:
        res = await cls.find_one(cls.type == event_type)
        if res:
            return res.model_dump()
        return {}

    @classmethod
    async def check_event(cls, event_type: str = '') -> bool:
        res = await cls.find_one(cls.type == event_type)
        return bool(res)

    @classmethod
    async def create_event_dict(cls, event_type: str = '', time_end: int = 0) -> dict:
        import time
        from random import choice, randint
        from random import choices
        from bot.modules.data_format import random_dict
        from bot.const import GAME_SETTINGS as GS

        if not event_type:
            event_types = {
                'add_hunting': 20,
                'add_fishing': 20,
                'add_collecting': 20,
                'add_all': 10,
                'xp_boost': 5,
                'xp_premium_boost': 5
            }
            event_type = choices(
                list(event_types.keys()),
                list(event_types.values())
            )[0]

        event_data = {}
        t_end = time_end

        if event_type == 'time_year':
            month_n = int(time.strftime("%m"))
            if month_n < 3 or month_n > 11:
                event_data['season'] = 'winter'
            elif 6 > month_n > 2:
                event_data['season'] = 'spring'
            elif 9 > month_n > 5:
                event_data['season'] = 'summer'
            else: 
                event_data['season'] = 'autumn'

        elif event_type == 'new_year':
            day_n = int(time.strftime("%j"))
            event_data['send'] = []
            t_end = (86400 * (366 - day_n + 7)) + int(time.time())

        elif event_type in ['add_hunting', 'add_fishing', 'add_collecting', 'add_all']:
            max_col = random_dict(GS['events']['random_data']['random_col'])
            items = []
            while len(items) < max_col:
                for key, value in GS['events']['random_data'][event_type].items():
                    if randint(1, value[1]) <= value[0]:
                        items.append(key)
            event_data['items'] = items
            event_data['special_chance'] = {}

            if time_end == 0:
                t_end = int(time.time()) + choice(GS['events']['random_data']['random_time'])

        elif event_type in ['xp_premium_boost', 'xp_boost']:
            event_data['xp_boost'] = round(randint(1, 2) / 10, 1)
            if time_end == 0:
                t_end = int(time.time()) + choice([14_400, 28_800, 7200, 3600])

        return {
            'type': event_type,
            'data': event_data,
            'time_start': int(time.time()),
            'time_end': t_end
        }

    @classmethod
    async def add_event(cls, event: dict, delete_old: bool = False) -> bool:
        res = await cls.find_one(cls.type == event['type'])
        if not res:
            new_ev = cls(**event)
            await new_ev.insert()
            return True
        else: 
            if delete_old:
                await res.delete()
                new_ev = cls(**event)
                await new_ev.insert()
                return True
            return False

    @classmethod
    async def auto_event(cls):
        import time
        import datetime
        from bot.exec import bot
        from bot.dbmanager import conf
        from bot.modules.localization import t

        # Проверка на время года
        time_year = await cls.find_one(cls.type == 'time_year')
        ty_event = await cls.create_event_dict('time_year')
        if time_year:
            if time_year.data.get('season') != ty_event['data']['season']:
                time_year.data = ty_event['data']
                await time_year.save()
        else:
            await cls.add_event(ty_event)

        # Проверка на новогоднее событие
        if not await cls.check_event('new_year'):
            day_n = int(time.strftime("%j"))
            if day_n >= 363:
                new_year_event = await cls.create_event_dict('new_year')
                await cls.add_event(new_year_event)
                await bot.send_message(conf.bot_group_id, t("events.new_year"))

        # Проверка на 1-ое апреля
        if not await cls.check_event('april_1'):
            today = datetime.date.today()
            if today.strftime("%m-%d") == "04-01":
                time_end = (86400 * 3) + int(time.time())
                april_event = await cls.create_event_dict('april_1', time_end)

                events_lst = []
                for i in ['add_hunting', 'add_fishing', 'add_collecting', 'add_all']:
                    ev = await cls.create_event_dict(i, time_end)
                    ev['data']['items'] = ['fried_egg']
                    events_lst.append(ev)

                await cls.add_event(april_event)
                for i in events_lst: 
                    await cls.add_event(i, True)
                await bot.send_message(conf.bot_group_id, t("events.april_1"))

        # День рождения бота
        if not await cls.check_event('april_5'):
            today = datetime.date.today()
            if today.strftime("%m-%d") == "04-05":
                time_end = (86400 * 3) + int(time.time())
                april_event = await cls.create_event_dict('april_5', time_end)

                events_lst = []
                add_hunting = await cls.create_event_dict('add_hunting', time_end)
                add_hunting['data']['items'] += ['meat_pie', 'ale', 'cake']
                events_lst.append(add_hunting)

                add_fishing = await cls.create_event_dict('add_fishing', time_end)
                add_fishing['data']['items'] += ['fish_cake', 'ale', 'cake']
                events_lst.append(add_fishing)

                add_collecting = await cls.create_event_dict('add_collecting', time_end)
                add_collecting['data']['items'] += ['berry_pie', 'ale', 'cake']
                events_lst.append(add_collecting)

                add_all = await cls.create_event_dict('add_all', time_end)
                add_all['data']['items'] += ['berry_pie', 'fish_cake', 'meat_pie', 'ale', 'cake']
                events_lst.append(add_all)
                
                xp_boost = await cls.create_event_dict('xp_boost', time_end)
                xp_boost['data']['xp_boost'] = 1
                events_lst.append(xp_boost)

                await cls.add_event(april_event)
                for i in events_lst: 
                    await cls.add_event(i, True)

                await bot.send_message(conf.bot_group_id, t("events.april_5"))

class Promo(Document):
    code: str = ""
    users: List[int] = Field(default_factory=list)
    col: Union[int, str] = 0
    time_end: Union[int, str] = 0
    time: Union[int, str] = 0
    coins: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)
    active: bool = False

    class Settings:
        name = "promo"

    @classmethod
    async def create_promo(cls, code: str, col: Union[int, str], seconds: Union[int, str], coins: int, items: list, active: bool = False) -> bool:
        promo_check = await cls.find_one(cls.code == code)
        if not promo_check:
            data = cls(
                code=code,
                users=[],
                col=col,
                time_end=seconds,
                time=seconds,
                coins=coins,
                items=items,
                active=active
            )
            await data.insert()
            return True
        return False

    @classmethod
    async def promo_ui(cls, code: str, lang: str):
        import time
        from bot.modules.localization import t, get_data
        from bot.modules.items.item import counts_items
        from bot.modules.data_format import list_to_inline, seconds_to_str

        data = await cls.find_one(cls.code == code)
        text, markup = '', None

        if data:
            status = '✅' if data.active else '❌'
            id_list = [i['item_id'] for i in data.items]

            if data.time_end == 'inf':
                txt_time = '♾'
            else: 
                txt_time = seconds_to_str(int(data.time_end) - int(time.time()), lang)

            text = t('promo_commands.ui.text', lang,
                     code=code, status=status,
                     col=data.col, coins=data.coins,
                     items=counts_items(id_list, lang),
                     txt_time=txt_time)

            but = get_data('promo_commands.ui.buttons', lang)
            inl_l = {
                but[0]: f'promo {code} active',
                but[1]: f'promo {code} delete',
                but[2]: f'promo {code} use'
            }
            markup = list_to_inline([inl_l], 2)
        return text, markup

    @classmethod
    async def get_promo_pages(cls) -> dict:
        res = await cls.find_all().to_list()
        data = {}
        for i in res: 
            data[i.code] = i.code
        return data

    @classmethod
    async def use_promo(cls, code: str, userid: int, lang: str):
        import time
        from bot.modules.localization import t
        from bot.models.user import User
        from bot.modules.user.user import take_coins
        from bot.modules.items.item import AddItemToUser, counts_items

        data = await cls.find_one(cls.code == code)
        user = await User.find_one(User.userid == userid)
        text = ''

        if user:
            if data:
                col = data.col
                if col == 'inf': 
                    col = 1

                seconds = data.time_end
                if seconds == 'inf': 
                    seconds = int(time.time()) + 100

                if data.active:
                    if col:
                        if int(seconds) - int(time.time()) > 0:
                            if userid not in data.users:
                                await data.update({
                                    "$push": {f'users': userid}
                                })
                                if data.col != 'inf':
                                    await data.update({
                                        "$inc": {f'col': -1}
                                    })

                                text = t('promo_commands.activate', lang)
                                if data.coins:
                                    await take_coins(userid, data.coins, True)
                                    text += t('promo_commands.coins', lang, coins=data.coins)
                                
                                if data.items:
                                    id_list = []
                                    for item in data.items:
                                        count = item.get('count', 1)
                                        abil = item.get('abilities', {})
                                        item_id = item['item_id']
                                        await AddItemToUser(userid, item_id, count, abil)
                                        id_list.append(item_id)

                                    text += t('promo_commands.items', lang, items=counts_items(id_list, lang))

                                return 'ok', text
                            else:
                                text = t('promo_commands.already_use', lang)
                                return 'already_use', text
                        else:
                            text = t('promo_commands.time_end', lang)
                            return 'time_end', text
                    else:
                        text = t('promo_commands.max_col', lang)
                        return 'max_col_use', text
                else:
                    text = t('promo_commands.deactivated', lang)
                    return 'deactivated', text
            else:
                text = t('promo_commands.not_found', lang)
                return 'not_found', text
        text = t('promo_commands.no_user', lang)
        return 'no_user', text

class DeadUser(Document):
    userid: Optional[int] = None
    last_m: int = 0

    class Settings:
        name = "dead_users"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("last_m", ASCENDING)], name="last_m")
        ]

class Company(Document):
    name: str = ""
    time_end: int = 0

    class Settings:
        name = "companies"
        indexes = [
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

class MessageLog(Document):
    userid: Optional[int] = None
    advert_id: Optional[str] = None
    message_log: int = 0

    class Settings:
        name = "message_log"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("advert_id", ASCENDING)], name="advert_id"),
            IndexModel([("message_log", ASCENDING)], name="message_log")
        ]

class States(Document):
    userid: Optional[int] = None
    state: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "states"

class Booster(Document):
    user_id: Optional[int] = None
    end_time: int = 0
    time: int = 0

    class Settings:
        name = "boosters"

    @classmethod
    async def user_boost_channel_status(cls, userid: int) -> bool:
        from bot.exec import bot
        from bot.const import GAME_SETTINGS
        try:
            res = await bot.get_user_chat_boosts(GAME_SETTINGS['channel_id'], userid)
            if res and len(res.boosts) > 0:
                return True
            return False
        except: 
            return False

    @classmethod
    async def base_boost_check(cls, userid: int) -> bool:
        import time
        check = await cls.find_one(cls.user_id == userid)
        if check:
            if check.end_time > int(time.time()):
                return True
            else:
                res = await cls.delete_boost(userid)
                return not res
        return False

    @classmethod
    async def create_boost(cls, userid: int, end_time: int = 0):
        import time
        check = await cls.find_one(cls.user_id == userid)
        if check:
            return check

        boost = cls(
            user_id=userid,
            end_time=end_time,
            time=int(time.time())
        )
        await boost.insert()
        return boost

    @classmethod
    async def delete_boost(cls, userid: int) -> bool:
        res = await cls.user_boost_channel_status(userid)
        if not res:
            await cls.find(cls.user_id == userid).delete()
            return True
        return False

class OnetimeReward(Document):
    user_id: int
    coins: int
    type: str

    class Settings:
        name = "onetime_rewards"

    @classmethod
    async def check_for_entry(cls, user_id: int, en_type: str) -> bool:
        from bot.const import GAME_SETTINGS as GS
        from bot.modules.user.user import user_in_chat

        assert en_type in ['channel', 'forum'], "Invalid en_type provided"
        chat_id = GS['channel_id'] if en_type == 'channel' else GS['forum_id']
        return await user_in_chat(user_id, chat_id)

    @classmethod
    async def check_award(cls, user_id: int, en_type: str):
        return await cls.find_one(cls.user_id == user_id, cls.type == en_type)

    @classmethod
    async def award_for_entry(cls, user_id: int, en_type: str) -> bool:
        from bot.const import GAME_SETTINGS as GS
        from bot.models.user import User
        from bot.modules.logs import log

        check = await cls.check_award(user_id, en_type)
        if not check:
            coins = GS['channel_subs_reward'] if en_type == 'channel' else GS['forum_subs_reward']
            
            user_doc = await User.find_one(User.userid == user_id)
            if user_doc:
                user_doc.super_coins += coins
                await user_doc.save()

            log(f'User {user_id} entered {en_type} and received {coins} super_coins', 1, 'award_for_entry')

            data = cls(
                user_id=user_id,
                coins=coins,
                type=en_type
            )
            await data.insert()
            return True
        return False


class DungLobby(Document):
    dungeonid: int = 0
    users: Dict[str, Any] = Field(default_factory=dict)
    floor: Dict[str, Any] = Field(default_factory=dict)
    rooms: Dict[str, Any] = Field(default_factory=dict)
    stage: str = "preparation"
    stage_data: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "lobby"


