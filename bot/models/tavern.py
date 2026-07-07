from typing import Dict, Any, Optional
from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING, TEXT
from bot.models.base_private import PrivateModelMixin

class Quest(PrivateModelMixin, Document):
    owner_id: int = 0
    alt_id: str = ""
    quest_id: str = ""
    stage: int = 0
    time_end: int = 0

    class Settings:
        name = "quests"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], name="owner_id"),
            IndexModel([("alt_id", TEXT)], unique=True, name="alt_id"),
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

    async def set_stage(self, stage: int) -> None:
        self.stage = stage
        await self.save()

    async def set_time_end(self, time_end: int) -> None:
        self.time_end = time_end
        await self.save()


class DailyAward(PrivateModelMixin, Document):
    owner_id: int = 0
    time_end: int = 0
    streak: int = 0

    class Settings:
        name = "daily_award"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], unique=True, name="owner_id"),
            IndexModel([("time_end", ASCENDING)], name="time_end")
        ]

    async def set_time_end(self, time_end: int) -> None:
        self.time_end = time_end
        await self.save()

    async def increment_streak(self) -> None:
        self.streak += 1
        await self.save()

    async def reset_streak(self) -> None:
        self.streak = 0
        await self.save()


class InsideShop(PrivateModelMixin, Document):
    owner_id: int = 0
    day_number: int = 0
    items: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "inside_shop"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], unique=True, name="owner_id")
        ]

    async def generate(self) -> Dict[str, Any]:
        """Regenerates the items for the inside shop if day_number has changed or force update."""
        import time
        from bot.const import GAME_SETTINGS
        from bot.modules.items.items_groups import get_group
        from bot.modules.items.item import get_item_dict, get_item_endurance_max
        from bot.modules.items.item import get_data as get_item_data
        from random import randint, choices, choice

        day_n = int(time.strftime("%j"))
        ignore_items = GAME_SETTINGS['ignore_items_inside_shop']
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

        chosen_items: list[str] = []
        new_items: Dict[str, Any] = {}

        def get_random_item_by_chances(already_chosen: list[str]):
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
            new_price = int(price * price_multiplier) + randint(int(price * 0.1), price)

            item_dict = get_item_dict(item)

            # Apply stat percentages
            if 'abilities' in item_dict and 'uses' in item_dict['abilities']:
                max_uses = item_dict['abilities']['uses']
                pct = stat_percentages.get('uses', 10)
                item_dict['abilities']['uses'] = max(1, int(max_uses * (pct / 100)))
            
            max_endurance = get_item_endurance_max(item_dict)
            if max_endurance is not None and max_endurance > 0:
                pct = stat_percentages.get('endurance', 20)
                item_dict.setdefault('abilities', {})['endurance'] = max(
                    1, int(max_endurance * (pct / 100)))

            new_items[item] = {
                'items_data': item_dict,
                'count': count,
                'price': new_price
            }

        self.items = new_items
        self.day_number = day_n
        await self.save()
        return new_items

    @classmethod
    async def get_content(cls, owner_id: int) -> Dict[str, Any]:
        import time
        day_n = int(time.strftime("%j"))

        shop = await cls.find_one(cls.owner_id == owner_id)

        if not shop:
            shop = cls(owner_id=owner_id, day_number=0, items={})
            await shop.insert()
            return await shop.generate()
            
        if shop.day_number != day_n:
            return await shop.generate()

        return shop.items

    @classmethod
    async def item_buyed(cls, owner_id: int, item_key: str, col: int) -> bool:
        from bot.models.user import User
        user = await User.find_one(User.userid == owner_id)

        if not user:
            return False

        shop = await cls.find_one(cls.owner_id == owner_id)
        if shop and item_key in shop.items:
            item = shop.items[item_key]
            if col <= item['count']:
                from bot.modules.overwriting.DataCalsses import Transaction

                async with Transaction():
                    if await user.remove_coins(col * item['price']):
                        await user.add_item(item_key, col, item['items_data'].get('abilities'))
                        shop.items[item_key]['count'] -= col
                        await shop.save()
                        return True
        return False
