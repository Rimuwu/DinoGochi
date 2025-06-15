from bson import ObjectId
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.items.item import AddItemToUser, CheckItemFromUser, ItemData, ItemInBase, RemoveItemFromUser, counts_items, get_items_names
from bot.modules.items.json_item import GetItem
from bot.modules.items.time_craft import add_time_craft
from bot.modules.localization import t
from bot.modules.markup import markups_menu as m


async def ns_craft(item_id: ObjectId, ns_id: str, count: int, 
                   chatid: int, lang: str):

    item = await ItemInBase().link_for_id(item_id)
    userid = item.owner_id

    nd_data = item.items_data.data.ns_craft[ns_id]

    materials: dict[str, int] = {}
    for i in nd_data['materials']: 
        if isinstance(i, str):
            materials[i] = materials.get(i, 0) + 1

        elif isinstance(i, dict):
            item_i = i['item_id']
            count_i = i['count']

            materials[item_i] = materials.get(item_i, 0) + count_i

    for key, col in materials.items(): materials[key] = col * count

    check_lst = []
    for key, value in materials.items():
        item_data = GetItem(key)

        res = await CheckItemFromUser(userid, 
                    item_data.item_id, item_data.abilities, value)

        check_lst.append(res['status'])

    if all(check_lst):
        craft_list = []

        if 'time_craft' in nd_data:

            for key, value in materials.items():
                item_data = ItemData(key)
                await RemoveItemFromUser(userid, item_data, value)

            items_tcraft = []

            for iid in nd_data['create']:

                if isinstance(iid, dict):
                    items_tcraft.append(
                        {'item': {
                            'item_id': iid['item_id'] 
                            },
                         'count': iid['count'] * count
                        }
                    )

                elif isinstance(iid, str):
                    items_tcraft.append(
                        {'item': {
                            'item_id': iid 
                            },
                         'count': 1 * count
                        }
                    )

            tt = nd_data['time_craft']
            tc = await add_time_craft(userid, 
                                 tt, 
                                 items_tcraft)
            text = t('time_craft.text_start', lang, 
                    items=get_items_names(items_tcraft, lang),
                    craft_time=seconds_to_str(tt, lang)
                    )
            markup = list_to_inline(
                [
                    {t('time_craft.button', lang): f"time_craft {tc['alt_code']}  send_dino"}
                ]
            )

            await bot.send_message(chatid, text, parse_mode='Markdown', 
                           reply_markup = markup)

            text = t('time_craft.text2', lang,
                    command='/craftlist')
            markup = await m(userid, 'last_menu', lang)
            await bot.send_message(chatid, text, parse_mode='Markdown', 
                            reply_markup = markup)

        else:
            for iid in nd_data['create']:

                if isinstance(iid, dict):
                    item_i = iid['item_id']
                    count_i = iid['count']
                    craft_list.append(item_i)

                    item_data = ItemData(item_i)

                    await AddItemToUser(userid, item_data, count_i * count)

                elif isinstance(iid, str):
                    craft_list.append(iid)
                    item_d = ItemData(iid)
                    await AddItemToUser(userid, item_d, count)

            for key, value in materials.items():
                item_data = ItemData(key)
                await RemoveItemFromUser(userid, item_data, value)

            text = t('ns_craft.create', lang, 
                    items = counts_items(craft_list, lang))
            await bot.send_message(chatid, text, 
                            reply_markup = await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('ns_craft.not_materials', lang),
                           reply_markup = await m(userid, 'last_menu', lang))