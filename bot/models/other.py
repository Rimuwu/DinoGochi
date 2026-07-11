from bot.models.dinosaur import State
from typing import List, Dict, Any, Optional, Union
from beanie import Document, Link, PydanticObjectId
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel, ASCENDING
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User

class Lottery(PrivateModelMixin, Document):
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
        await cls.create_task(data.id, data.time_end)
        await cls.create_message(alt_id, end=False)

    @classmethod
    async def delete_lottery(cls, lot_id: ObjectId):
        lot = await cls.find_one(cls.id == lot_id)
        if lot:
            await lot.delete()
            await LotteryMember.find(LotteryMember.lot_id == str(lot_id)).delete()
            await cls.cancel_task(lot_id)

    @classmethod
    async def create_task(cls, lot_id: ObjectId, end_time: int):
        from bot.modules.task_queue import enqueue_task
        await enqueue_task("lottery_end", {"lottery_id": str(lot_id)}, run_at=end_time, resource_id=f"lottery:{lot_id}")

    @classmethod
    async def cancel_task(cls, lot_id: ObjectId):
        from bot.modules.task_queue import cancel_task_by_resource
        await cancel_task_by_resource(f"lottery:{lot_id}")

    @classmethod
    async def verify_tasks(cls):
        from bot.modules.task_queue import is_task_scheduled
        import time
        current_time = int(time.time())
        lotteries = await cls.find().to_list()
        for lot in lotteries:
            res_id = f"lottery:{lot.id}"
            if not await is_task_scheduled(res_id):
                run_at = max(current_time, lot.time_end)
                await cls.create_task(lot.id, run_at)

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
    async def create_message(cls, alt_id: str, end: bool = False, winners_count: int = 0): 
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
                time_end_text = t('lottery.end_text', lang=lang, winners_count=winners_count)

            message += cap + prizes_text + time_end_text
            
            if lot.message_id:
                try:
                    await bot.edit_message_text(message, chat_id=channel_id, message_id=lot.message_id, reply_markup=markup, parse_mode='Markdown')
                except Exception as e:
                    pass
            else:
                try:
                    mes = await bot.send_message(channel_id, message, reply_markup=markup, parse_mode='Markdown')
                    lot.message_id = mes.message_id
                    await lot.save()
                except Exception as e:
                    pass

    @classmethod
    async def winers_text(cls, winers: dict, lang: str) -> str:
        from bot.modules.localization import t
        from bot.exec import bot

        text = ''
        cap = t('lottery.winners_cap', lang)
        winers_text_val = ''
        for key, value in winers.items():
            users_len = 0
            if len(value) != 0: 
                winers_text_val += f"#{key} | "
        
                for user_id in value:
                    if users_len >= 10:
                        winers_text_val += '...'
                        users_len = 0
                        break

                    try:
                        user = await bot.get_chat_member(chat_id=user_id, user_id=user_id)
                    except:
                        user = None

                    if user:
                        users_len += 1
                        if user.user.username:
                            winers_text_val += f"@{user.user.username} "
                        else:
                            winers_text_val += f"{user.user.first_name} "
        
                winers_text_val += '\n'

        footer = t('lottery.winners_footer', lang)
        text += cap + winers_text_val + footer
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
            for member in shuf_members:
                if all_get: 
                    break

                for key, value in winers.items():
                    if len(winers[key]) < lotter.prizes[key]['count']:
                        if member.userid:
                            winers[key].append(member.userid)

                            if key == list(winers.keys())[-1]:
                                all_get = True
                            break
                        break

        return winers

    @classmethod
    async def end_lottery(cls, lot_id: ObjectId):
        from bot.exec import bot
        lotter = await cls.find_one(cls.id == lot_id)
        if lotter:
            winers = await cls.find_winners(lot_id)
            total_winners = sum(len(v) for v in winers.values())
            try:
                await cls.create_message(lotter.alt_id, end=True, winners_count=total_winners)
            except: 
                pass

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


class LotteryMember(PrivateModelMixin, Document):
    lot_id: str = ""
    userid: int = 0

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
        from bot.models.user import User

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
            user_obj = await User.find_one(User.userid == user_id)
            if user_obj:
                await user_obj.add_coins(coins)



class Statistic(PrivateModelMixin, Document):
    date: str = ""
    dinosaurs: int = 0
    users: int = 0
    items: int = 0
    groups: int = 0

    class Settings:
        name = "statistic"


class Event(PrivateModelMixin, Document):
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
        from random import choice, randint, choices
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

        time_year = await cls.find_one(cls.type == 'time_year')
        ty_event = await cls.create_event_dict('time_year')
        if time_year:
            if time_year.data.get('season') != ty_event['data']['season']:
                time_year.data = ty_event['data']
                await time_year.save()
        else:
            await cls.add_event(ty_event)

        if not await cls.check_event('new_year'):
            day_n = int(time.strftime("%j"))
            if day_n >= 363:
                new_year_event = await cls.create_event_dict('new_year')
                await cls.add_event(new_year_event)
                await bot.send_message(conf.bot_group_id, t("events.new_year"))

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


class Promo(PrivateModelMixin, Document):
    code: str = ""
    users: List[Union[Link[User], int]] = Field(default_factory=list)
    col: Union[int, str] = 0
    time_end: Union[int, str] = 0
    time: Union[int, str] = 0
    coins: int = 0
    super_coins: int = 0
    items: List[Dict[str, Any]] = Field(default_factory=list)
    active: bool = False

    class Settings:
        name = "promo"

    @classmethod
    async def create_promo(cls, code: str, col: Union[int, str], seconds: Union[int, str], coins: int, items: list, active: bool = False, super_coins: int = 0) -> bool:
        promo_check = await cls.find_one(cls.code == code)
        if not promo_check:
            data = cls(
                code=code,
                users=[],
                col=col,
                time_end=seconds,
                time=seconds,
                coins=coins,
                super_coins=super_coins,
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

            super_coins_val = getattr(data, 'super_coins', 0)
            activations_val = len(data.users) if data.users else 0

            text = t('promo_commands.ui.text', lang,
                     code=code, status=status,
                     activations=activations_val,
                     col=data.col, coins=data.coins,
                     super_coins=super_coins_val,
                     items=counts_items(id_list, lang),
                     txt_time=txt_time)

            but = get_data('promo_commands.ui.buttons', lang)
            clear_text = t('promo_commands.ui.clear_users', lang, default='🗑 Очистить участников')
            
            inl_l1 = {
                but[0]: f'promo {code} active',
                but[1]: f'promo {code} delete'
            }
            inl_l2 = {
                but[2]: f'promo {code} use',
                clear_text: f'promo {code} clear_users'
            }
            markup = list_to_inline([inl_l1, inl_l2], 2)
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
                            has_used = False
                            for u in data.users:
                                if isinstance(u, int):
                                    if u == user.userid:
                                        has_used = True
                                        break
                                else:
                                    u_id = u.ref.id if hasattr(u, 'ref') else getattr(u, 'id', None)
                                    if u_id == user.id:
                                        has_used = True
                                        break
                            if not has_used:
                                await data.add_user(user)
                                if data.col != 'inf':
                                    await data.decrement_col()

                                text = t('promo_commands.activate', lang)
                                if data.coins:
                                    await user.add_coins(data.coins)
                                    text += t('promo_commands.coins', lang, coins=data.coins)
                                
                                if getattr(data, 'super_coins', 0):
                                    await user.add_super_coins(data.super_coins)
                                    text += t('promo_commands.super_coins', lang, coins=data.super_coins, default=f"💎 | Супер-коины: {data.super_coins}\n")

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

    async def toggle_active(self) -> None:
        self.active = not self.active
        await self.save()

    async def add_user(self, user: User) -> None:
        self.users.append(user)
        await self.save()

    async def decrement_col(self) -> None:
        if isinstance(self.col, int):
            self.col -= 1
            await self.save()

    async def clear_users(self) -> None:
        self.users = []
        await self.save()


class DeadUser(PrivateModelMixin, Document):
    userid: int = 0
    last_m: int = 0

    class Settings:
        name = "dead_users"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("last_m", ASCENDING)], name="last_m")
        ]

    async def set_last_m(self, timestamp: int) -> None:
        self.last_m = timestamp
        await self.save()


class Company(PrivateModelMixin, Document):
    owner: int = 0
    message: dict = {}
    langs: List[str] = Field(default_factory=list)
    time_end: Union[int, str] = 0
    time_start: int = 0
    max_count: Union[int, str] = 0
    show_count: int = 0
    coin_price: int = 0
    priority: bool = False
    one_message: bool = False
    pin_message: bool = False
    delete_after: bool = False
    ignore_system_timeout: bool = False
    min_timeout: int = 0
    status: bool = False
    name: str = ""
    alt_id: str = ""
    min_reg_time: int = 0

    class Settings:
        name = "companies"
        indexes = [
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

    @classmethod
    async def generation_code(cls, owner_id):
        from bot.modules.data_format import random_code
        code = f'{owner_id}_{random_code(4)}'
        if await cls.find_one(cls.alt_id == code):
            code = await cls.generation_code(owner_id)
        return code

    @classmethod
    async def create_company(cls, owner: int, message: dict, time_end: int, 
                            count: int, coin_price: int, priority: bool, 
                            one_message: bool, pin_message: bool, min_timeout: int,
                            delete_after: bool, ignore_system_timeout: bool, name: str,
                            min_reg_time: int = 0
                            ):
        import time
        if time_end == 0: end = 0
        else: end = time_end + int(time.time())

        data = {
            'owner': owner,
            'message': message,
            'langs': list(message.keys()),
            'time_end': end,
            'time_start': int(time.time()),
            'max_count': count, 'show_count': 0,
            'coin_price': coin_price,
            'priority': priority,
            'one_message': one_message,
            'pin_message': pin_message,
            'delete_after': delete_after,
            'ignore_system_timeout': ignore_system_timeout,
            'min_timeout': min_timeout,
            'status': False,
            'name': name,
            'alt_id': await cls.generation_code(owner),
            'min_reg_time': min_reg_time
        }
        await cls(**data).insert()

    @classmethod
    async def end_company(cls, advert_id: ObjectId):
        from bot.modules.localization import t, get_lang
        from bot.modules.data_format import seconds_to_str
        from bot.exec import bot
        from bot.dbmanager import conf
        from bot.modules.logs import log
        import time
        companie = await cls.find_one(cls.id == advert_id)

        if companie:
            await companie.delete()
            
            for i in set([companie.owner] + conf.bot_devs):
                lang = await get_lang(i)
                try:
                    await bot.send_message(i,
                        t('companies.end_company', lang, 
                        time_work = seconds_to_str(int(time.time()) - companie.time_start, lang),
                        show_count = companie.show_count,
                        max_count = companie.max_count,
                        name = companie.name)
                        )
                except Exception as e:
                    log(f'except in end_company {e}', 3)

            if companie.delete_after:
                messages_models = await MessageLog.find(MessageLog.advert_id == str(advert_id)).to_list()
                for mes in messages_models:
                    if companie.pin_message:
                        try:
                            await bot.unpin_chat_message(mes.userid, mes.message_id)
                        except: pass
                    try:
                        await bot.delete_message(mes.userid, mes.message_id)
                    except: pass
                    await mes.delete()
            else:
                await MessageLog.find(MessageLog.advert_id == str(advert_id)).delete()

    @classmethod
    async def generate_message(cls, userid: int, company_id: ObjectId, lang = None, save = True):
        from bot.modules.localization import get_lang, t
        from bot.exec import bot
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from bot.modules.logs import log
        if not lang: lang = await get_lang(userid)

        companie = await cls.find_one(cls.id == company_id)
        if companie and lang in companie.message.keys():
            message = companie.message[lang]
            text = message['text']
            parse_mode = message['parse_mode']
            image = message['image']

            inline = InlineKeyboardBuilder()
            for i in message['markup']:
                for key, value in i.items():
                    inline.add(InlineKeyboardButton(text=key, url=value))

            m = None
            if image != 'no_image':
                try:
                    m = await bot.send_photo(userid, image, caption=text, parse_mode=parse_mode, 
                                             reply_markup=inline.as_markup(resize_keyboard=True))
                except Exception as e:
                    log(f'generate_comp_message image error - {e}', 2)
                    m = await bot.send_photo(userid, image, caption=text, 
                                         reply_markup=inline.as_markup(resize_keyboard=True))
            else:
                try:
                    m = await bot.send_message(userid, text, 
                                           parse_mode=parse_mode, reply_markup=inline.as_markup(resize_keyboard=True))
                except Exception as e:
                    log(f'generate_comp_message error - {e}', 2)
                    m = await bot.send_message(userid, text, 
                                         reply_markup=inline.as_markup(resize_keyboard=True))

            if m and save:
                await MessageLog.save_message(company_id, userid, m.message_id)

            if companie.pin_message and save:
                try:
                    s = await bot.pin_chat_message(m.chat.id, m.message_id)
                    if s: await bot.delete_message(m.chat.id, m.message_id + 1)
                except: pass

            if companie.coin_price > 0 and m and save:
                user = await User.find_one(User.userid == userid)
                if user:
                    await user.add_super_coins(companie.coin_price)
                log(f"Edit super_coins: user: {userid} col: {companie.coin_price}", 1, "generate_message")
                try:
                    await bot.send_message(userid, 
                                        t('super_coins.moder_reward', lang, coin=companie.coin_price), parse_mode="Markdown")
                except:
                    await bot.send_message(userid, 
                                        t('super_coins.moder_reward', lang, coin=companie.coin_price))
            return m.message_id
        return None

    @classmethod
    async def nextinqueue(cls, userid: int, lang = None) -> Union[ObjectId, None]:
        from bot.modules.localization import get_lang
        from datetime import datetime, timezone
        import time
        import random
        if not lang: lang = await get_lang(userid)

        count_dct, permissions = {}, {}
        messages_models = await MessageLog.find(MessageLog.userid == userid).to_list()
        messages = [m.dict() for m in messages_models]

        comps_models = await cls.find(cls.status == True, cls.langs == lang).to_list()
        comps = [c.dict() for c in comps_models]

        for i in comps:
            try:
                max_c = int(i['max_count'])
            except:
                max_c = 0
            try:
                t_end = int(i['time_end'])
            except:
                t_end = 0

            if max_c != 0 and i['show_count'] >= max_c:
                await cls.end_company(i['_id'])
            elif t_end != 0 and int(time.time()) > t_end:
                await cls.end_company(i['_id'])
            else:
                count_dct[i['_id']] = 0
                permissions[i['_id']] = {'one_message': i['one_message'],
                                        'min_timeout': i['min_timeout'],
                                        'last_send': -1
                                        }

        if count_dct:
            for mes in messages:
                if mes['advert_id'] in count_dct:
                    count_dct[mes['advert_id']] += 1

                    send_time = mes['_id'].generation_time
                    now = datetime.now(timezone.utc)
                    delta = now - send_time

                    if delta.seconds < permissions[mes['advert_id']]['last_send'] or \
                        permissions[mes['advert_id']]['last_send'] == -1:
                        permissions[mes['advert_id']]['last_send'] = delta.seconds

            result_dct = count_dct.copy()
            for key, value in count_dct.items():
                if value > 0:
                    if not await cls.user_reg_min(userid, key):
                        del result_dct[key]
                        continue
                    if permissions[key]['one_message']: 
                        del result_dct[key]
                        continue
                    if permissions[key]['last_send'] < permissions[key]['min_timeout']:
                        if key in result_dct:
                            del result_dct[key]

            if result_dct.values():
                min_value = min(count_dct.values())
                min_keys = list(filter(lambda k: count_dct[k] == min_value, count_dct))
                r_key = random.choice(min_keys)
                return r_key
        return None

    @classmethod
    async def priority_and_timeout(cls, companie_id: ObjectId):
        f = await cls.find_one(cls.id == companie_id)
        if f: return f.priority, f.ignore_system_timeout
        return False, False

    @classmethod
    async def user_reg_min(cls, userid: int, companie_id: ObjectId) -> bool:
        from datetime import datetime, timezone
        user = await User.find_one(User.userid == userid)
        if user:
            create = user.id.generation_time
            now = datetime.now(timezone.utc)
            delta = now - create

            companie = await cls.find_one(cls.id == companie_id)
            if companie:
                if delta.total_seconds() >= companie.min_reg_time:
                    return True
        return False

    @classmethod
    async def info(cls, companie_id: ObjectId, lang = None):
        from bot.modules.localization import t, get_lang
        from bot.modules.data_format import seconds_to_str, list_to_inline, get_data
        import time
        from bson import ObjectId
        if isinstance(companie_id, str) and ObjectId.is_valid(companie_id):
            companie_id = ObjectId(companie_id)
        c = await cls.find_one(cls.id == companie_id)
        text, mrk = '', None

        if c:
            min_time = 0
            if c.min_reg_time > 0:
                min_time = seconds_to_str(c.min_reg_time, lang)

            if not lang: lang = await get_lang(c.owner)

            try:
                end_val = int(c.time_end)
            except:
                end_val = c.time_end

            if end_val == 0:
                end_str = '♾'
            else:
                if isinstance(end_val, int):
                    end_str = seconds_to_str(end_val - int(time.time()), lang)
                else:
                    end_str = str(end_val)

            try:
                max_c_val = int(c.max_count)
            except:
                max_c_val = c.max_count

            if max_c_val == 0:
                max_c_str = '♾'
            else:
                max_c_str = str(max_c_val)

            text = t('companies.info', lang,
                     name=c.name,
                     end=end_str,
                     delta=seconds_to_str(int(time.time())-c.time_start, lang),
                     show=c.show_count,
                     max_c=max_c_str,
                     coin=c.coin_price,
                     priority=c.priority,
                     pin=c.pin_message,
                     timeout=c.min_timeout,
                     sys_timeout=c.ignore_system_timeout,
                     dlete_after=c.delete_after,
                     status=c.status,
                     min_time=min_time,
                     )

            btn = get_data('companies.buttons', lang)
            new_btn = {}
            for key, value in btn.items():
                new_btn[value] = f'company_info {key} {c.alt_id}'

            mrk = list_to_inline([new_btn])

        return text, mrk


class MessageLog(PrivateModelMixin, Document):
    userid: int = 0
    advert_id: Optional[Union[str, PydanticObjectId]] = None
    message_id: Optional[int] = None
    message_log: int = 0

    class Settings:
        name = "message_log"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid"),
            IndexModel([("advert_id", ASCENDING)], name="advert_id"),
            IndexModel([("message_log", ASCENDING)], name="message_log")
        ]

    async def set_message_log(self, val: int) -> None:
        self.message_log = val
        await self.save()

    @classmethod
    async def save_message(cls, advert_id: ObjectId, userid: int, message_id: int):
        from bot.models.user import Ad
        import time
        data = {
            'advert_id': str(advert_id),
            'userid': userid,
            'message_id': message_id,
        }
        await cls(**data).insert()

        c_obj = await Company.find_one(Company.id == advert_id)
        if c_obj:
            c_obj.show_count += 1
            await c_obj.save()

        ads_cabinet = await Ad.find_one(Ad.userid == userid)
        if ads_cabinet:
            ads_cabinet.last_ads = int(time.time())
            await ads_cabinet.save()

class Booster(PrivateModelMixin, Document):
    userid: int = 0
    end_time: int = 0
    time: int = 0

    class Settings:
        name = "boosters"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid")
        ]

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
        check = await cls.find_one(cls.userid == userid)
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
        check = await cls.find_one(cls.userid == userid)
        if check:
            return check

        boost = cls(
            userid=userid,
            end_time=end_time,
            time=int(time.time())
        )
        await boost.insert()
        return boost

    @classmethod
    async def delete_boost(cls, userid: int) -> bool:
        res = await cls.user_boost_channel_status(userid)
        if not res:
            await cls.find(cls.userid == userid).delete()
            return True
        return False

    async def set_end_time(self, end_time: int) -> None:
        self.end_time = end_time
        await self.save()


class OnetimeReward(PrivateModelMixin, Document):
    userid: int = 0
    coins: int
    type: str

    class Settings:
        name = "onetime_rewards"
        indexes = [
            IndexModel([("userid", ASCENDING)], name="userid")
        ]

    @classmethod
    async def check_for_entry(cls, user_id: int, en_type: str) -> bool:
        from bot.const import GAME_SETTINGS as GS
        from bot.modules.user.user import user_in_chat

        assert en_type in ['channel', 'forum'], "Invalid en_type provided"
        chat_id = GS['channel_id'] if en_type == 'channel' else GS['forum_id']
        return await user_in_chat(user_id, chat_id)

    @classmethod
    async def check_award(cls, user_id: int, en_type: str):
        return await cls.find_one(cls.userid == user_id, cls.type == en_type)

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
                await user_doc.add_super_coins(coins)

            log(f'User {user_id} entered {en_type} and received {coins} super_coins', 1, 'award_for_entry')

            data = cls(
                userid=user_id,
                coins=coins,
                type=en_type
            )
            await data.insert()
            return True
        return False



class Donation(PrivateModelMixin, Document):
    code: str
    userid: int = 0
    user_first_name: str
    amount: int
    product: Optional[str] = None
    issued_reward: bool = False
    send_notification: bool = False
    time: int
    col: Union[int, str]
    donation_id: Optional[str] = None
    status: str = "done"

    class Settings:
        name = "donations"
        indexes = [
            IndexModel([("code", ASCENDING)], name="code", unique=True),
            IndexModel([("userid", ASCENDING)], name="userid")
        ]

    async def set_issued_reward(self, val: bool) -> None:
        self.issued_reward = val
        await self.save()

    async def set_send_notification(self, val: bool) -> None:
        self.send_notification = val
        await self.save()

    async def set_status(self, status: str) -> None:
        self.status = status
        await self.save()
