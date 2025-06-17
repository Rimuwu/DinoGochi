
# from bot.modules.add_product.auction import auction

# from bot.modules.market.market import generate_sell_pages, generate_items_pages

# from bot.modules.add_product.general import coins_stock
# from bot.modules.add_product.items_coins import circle_data as is_circle_data
# from bot.modules.add_product.coins_items import circle_data as si_circle_data
# from bot.modules.add_product.auction import circle_data as au_circle_data
# from bot.modules.add_product.items_items import items_items, trade_circle
# from bot.modules.states_fabric.state_handlers import ChooseStepHandler

# MAX_PRICE = 10_000_000


# """ Старт всех проверок
# """
# async def prepare_data_option(option, transmitted_data):
#     chatid = transmitted_data['chatid']
#     userid = transmitted_data['userid']
#     lang = transmitted_data['lang']
    

#     if option == 'items_coins': 
#         ret_function = coins_stock
#         items, exclude = await generate_sell_pages(userid)
#         circle_fun = is_circle_data

#     elif option == 'coins_items':
#         ret_function = coins_stock
#         items, exclude = generate_items_pages()
#         circle_fun = si_circle_data

#     elif option == 'items_items':
#         ret_function = items_items
#         items, exclude = await generate_sell_pages(userid)
#         circle_fun = trade_circle

#     else: # auction
#         ret_function = auction
#         items, exclude = await generate_sell_pages(userid)
#         circle_fun = au_circle_data

#     transmitted_data = {
#         'exclude': exclude, 'option': option
#     }

#     steps = circle_fun(lang, items, option)
#     # await ChooseStepState(ret_function, userid, chatid, 
#     #                       lang, steps, 
#     #                       transmitted_data=transmitted_data)
#     await ChooseStepHandler(ret_function, userid, chatid,
#                             lang, steps,
#                             transmitted_data=transmitted_data).start()