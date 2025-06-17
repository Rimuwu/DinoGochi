# from bot.dbmanager import mongo_client
# from bot.modules.add_product.general import end

# from bot.modules.markup import answer_markup, cancel_markup, count_markup

# from bot.modules.market.market import generate_sell_pages
# from bot.modules.states_fabric.state_handlers import ChooseStepHandler
# from bot.modules.states_fabric.steps_datatype import BaseUpdateType, ConfirmStepData, IntStepData, InventoryStepData, StepMessage, TimeStepData

# MAX_PRICE = 10_000_000
# from bot.modules.overwriting.DataCalsses import DBconstructor
# items = DBconstructor(mongo_client.items.items)

# # Все функции расположены в порядке вызова

# def circle_data(lang, items, option):
#     """ Создай данные для запроса: предмета, количества, надо ли повторить
#     """

#     steps = [
#         InventoryStepData('items', StepMessage(
#             text=f'add_product.chose_item.{option}',
#             translate_message=True,
#             ),
#             inventory=items
#         ),
#         BaseUpdateType(update_col),
#         IntStepData('col', StepMessage(
#             text='add_product.wait_count',
#             translate_message=True,
#             markup=count_markup(1, lang)
#         )),
#         BaseUpdateType(check_items)
#     ]

#     return steps

# async def update_col(transmitted_data):
#     """ Определяет сколько можно предметов можно выставить
#     """
#     userid = transmitted_data['userid']
#     lang = transmitted_data['lang']
#     step = transmitted_data['process']

#     if type(transmitted_data['return_data']['items']) == list:
#         item_data = transmitted_data['return_data']['items'][-1]
#     else:
#         item_data = transmitted_data['return_data']['items']

#     items_res = await items.find({'items_data': item_data, 
#                             "owner_id": userid}, comment="update_col_items_res")
#     if items_res:
#         max_count = 0
#         for i in items_res: max_count += i['count']
#         if max_count > 100: max_count = 100

#         # Добавление данных для выбора количества
#         transmitted_data['steps'][step+1]['data']['max_int'] = max_count
#         transmitted_data['steps'][step+1]['message']['markup'] = count_markup(max_count, lang).model_dump()
#         transmitted_data['exclude'].append(item_data['item_id'])

#         return transmitted_data, True
#     else: return transmitted_data, False

# def check_items(transmitted_data):
#     """ Функция создаёт проверку на дополнительные предметы, 
#         если предметов меньше чем 3 то спрашивает - добавить ли ещё предмет
#     """
#     lang = transmitted_data['lang']
#     userid = transmitted_data['userid']
#     chatid = transmitted_data['chatid']

#     res = True
#     if type(transmitted_data['return_data']['items']) == list and len(transmitted_data['return_data']['items']) >= 3: res = False

#     if res:

#         steps = [
#             ConfirmStepData('add_item', StepMessage(
#                 text='add_product.add_item',
#                 translate_message=True,
#                 markup=answer_markup(lang)
#             )),
#             BaseUpdateType(new_circle)
#         ]
#         transmitted_data['steps'] += steps

#     return transmitted_data, True

# async def new_circle(transmitted_data):
#     """ Функция создаёт круг запроса (активируется когда человек хочет добавить 2-ой и 3-ий товар в продукт)
#     """
#     lang = transmitted_data['lang']
#     userid = transmitted_data['userid']
#     chatid = transmitted_data['chatid']
#     add_res = transmitted_data['return_data']['add_item']
#     exclude_ids = transmitted_data['exclude']
#     option = transmitted_data['option']
    

#     if add_res:
#         items, exclude = await generate_sell_pages(userid, exclude_ids)
#         steps = circle_data(lang, items, option)

#         transmitted_data['exclude'] = exclude

#         transmitted_data['steps'].clear()
#         transmitted_data['steps'] = steps
#         del transmitted_data['return_data']['add_item']

#         transmitted_data['process'] = -1

#         return transmitted_data, True
#     return transmitted_data, False

# """ Функция для получения нач. цены, запаса, времени для типа auction
# """
# async def auction(return_data, transmitted_data):
#     chatid = transmitted_data['chatid']
#     userid = transmitted_data['userid']
#     lang = transmitted_data['lang']
    

#     if type(return_data['items']) != list:
#         return_data['items'] = [return_data['items']]
#         return_data['col'] = [return_data['col']]

#     steps = [
#         IntStepData('price', StepMessage(
#             text='add_product.coins.auction',
#             translate_message=True,
#             markup=cancel_markup(lang)),
#             max_int=MAX_PRICE
#         ),
#         IntStepData('min_add', StepMessage(
#             text='add_product.min_add',
#             translate_message=True,
#             markup=cancel_markup(lang)),
#             max_int=1_000_000
#         ),
#         TimeStepData('time_end', StepMessage(
#             text='add_product.time_end',
#             translate_message=True,
#             markup=cancel_markup(lang)),
#             max_int=2_592_000
#         )
#     ]

#     transmitted_data = {
#         'items': return_data['items'],
#         'col': return_data['col'],
#         'option': transmitted_data['option'],
#         'in_stock': 1
#     }

#     # await ChooseStepState(end, userid, chatid, 
#     #                       lang, steps, 
#     #                       transmitted_data=transmitted_data)
#     await ChooseStepHandler(end, userid, chatid,
#                           lang, steps,
#                           transmitted_data=transmitted_data).start()