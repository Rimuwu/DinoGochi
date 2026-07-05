from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.tavern import InsideShop

from random import choice, randint, choices
import time
import random

from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.modules.items.items_groups import get_group
from bot.modules.items.item import AddItemToUser, get_item_dict, get_item_endurance_max
from bot.modules.items.item import get_data as get_item_data

from bot.const import GAME_SETTINGS


from bot.modules.logs import log
from bot.models.user import User
inside_shop = LazyCollection(InsideShop)


ignore_items = GAME_SETTINGS['ignore_items_inside_shop']

async def create_shop(onwer_id):

    data = {
        "owner_id": onwer_id,
        "day_number": 0,
        "items": {}
    }

    res = await inside_shop.insert_one(data)
    items = await update_shop(res.inserted_id)
    return items


async def update_shop(ins_id: ObjectId) -> dict:

    shop = await inside_shop.find_one({'_id': ins_id})
    if shop:
        day_n = int(time.strftime("%j"))
        if day_n != shop['day_number']:
            items = {}

            # Load configurations
            inside_shop_config = GAME_SETTINGS.get('inside_shop', {})
            type_chances = inside_shop_config.get('type_chances', {
                "recipe": 40,
                "weapon": 20,
                "armor": 20,
                "backpack": 10,
                "material": 10
            })
            rank_chances = inside_shop_config.get('rank_chances', {
                "common": 50,
                "uncommon": 30,
                "rare": 15,
                "mystical": 4,
                "legendary": 1,
                "mythical": 0
            })
            stat_percentages = inside_shop_config.get('stat_percentages', {
                "uses": 10,
                "endurance": 20
            })

            chosen_items = []

            def get_random_item_by_chances(already_chosen):
                types = list(type_chances.keys())
                type_weights = list(type_chances.values())
                
                shuffled_types = choices(types, weights=type_weights, k=10)
                for chosen_type in shuffled_types:
                    items_in_type = get_group(chosen_type).copy()
                    valid_items = [i for i in items_in_type if i not in ignore_items and i not in already_chosen]
                    if not valid_items:
                        continue
                    
                    weights = []
                    for item_key in valid_items:
                        item_data = get_item_data(item_key)
                        rank = item_data.get('rank', 'common')
                        weight = rank_chances.get(rank, 1)
                        weights.append(weight)
                    
                    if sum(weights) == 0:
                        weights = [1] * len(valid_items)
                        
                    return choices(valid_items, weights=weights, k=1)[0]
                
                # Fallback to any item
                all_items = []
                for t_name in type_chances.keys():
                    all_items.extend(get_group(t_name))
                valid_items = [i for i in list(set(all_items)) if i not in ignore_items and i not in already_chosen]
                if valid_items:
                    return choice(valid_items)
                return None

            for _ in range(5):
                item = get_random_item_by_chances(chosen_items)
                if not item:
                    continue

                chosen_items.append(item)
                count = randint(1, 3)
                item_data = get_item_data(item)

                price = GAME_SETTINGS['buyer'].get(item_data.get('rank', 'common'), {}).get('price', 5)
                price_multiplier = inside_shop_config.get('price_multiplier', 3)
                new_price = int(int(price * price_multiplier) + randint(int(price * 0.1), price))

                item_dict = get_item_dict(item)
                
                # Apply stat percentages
                if 'abilities' in item_dict and 'uses' in item_dict['abilities']:
                    max_uses = item_dict['abilities']['uses']
                    pct = stat_percentages.get('uses', 10)
                    item_dict['abilities']['uses'] = max(1, int(max_uses * (pct / 100)))
                
                max_endurance = get_item_endurance_max(item_dict)
                if max_endurance is not None and max_endurance > 0:
                    pct = stat_percentages.get('endurance', 20)
                    item_dict.setdefault('abilities', {})['endurance'] = max(1, int(max_endurance * (pct / 100)))

                items[item] = {
                    'items_data': item_dict,
                    'count': count,
                    'price': new_price
                }

            await inside_shop.update_one({'_id': ins_id}, 
                                         {'$set': {'items': items, 
                                                   'day_number': day_n
                                                   }
                                          })
            return items
    return {}

async def get_content(owner_id: int): 
    shop = await inside_shop.find_one({'owner_id': owner_id})

    if shop:
        res = await update_shop(shop['_id'])
        if res != {}: return res
        else: return shop['items']

    else:
        return await create_shop(owner_id)

async def item_buyed(owner_id: int, item_key: str, col: int):
    shop = await inside_shop.find_one({'owner_id': owner_id})
    if shop:
        if item_key in shop['items']:
            item = shop['items'][item_key]
            if col <= item['count']:
                from bot.modules.overwriting.DataCalsses import Transaction
                async with Transaction():
                    user = await User.find_one(User.userid == owner_id)
                    if user and await user.remove_coins(col * item['price']):
                        await user.add_item(item_key, col, item['items_data'].get('abilities'))

                        await inside_shop.update_one({'_id': shop['_id']}, {
                            '$inc': {f'items.{item_key}.count': -col}
                        })

                        return True

    return False