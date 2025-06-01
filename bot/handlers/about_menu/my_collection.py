
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, progress_bar, seconds_to_str
from bot.modules.decorators import HDMessage
from bot.modules.localization import get_lang, t
from aiogram.types import CallbackQuery, Message
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F
import time
from aiogram.types import InputMediaPhoto
from bot.filters.translated_text import Text
from bot.modules.user.dinocollection import get_count_families_by_user, get_dino_collection_by_user
from bot.modules.images import async_open, create_dino_centered_image
import os
from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.modules.dinosaur.dino_count import families, all_dinos

async def get_collection_page_data(user_id, collection, page, lang):
    if page < 0 or page >= len(collection):
        page = 0
    entry = collection[page]

    data_id = entry["data_id"]
    image_path = f"bot/temp/dino_collection_{data_id}.png"

    if not os.path.exists(image_path):
        image = await create_dino_centered_image(data_id)
        with open(image_path, "wb") as f:
            f.write(image.data)
    else:
        image = await async_open(image_path, True)

    my_families = await get_count_families_by_user(user_id)

    text = t("dino_collection.info", lang, dino_id=data_id,
             uniq=await get_dino_uniqueness_factor(data_id),
             date=seconds_to_str(int(time.time()) - entry["date"], lang),
             rod=entry['familie'],
             all_families=f'{my_families}/{families}',
             all_dinos=f'{len(collection)}/{all_dinos}',
             rod_bar=progress_bar(
                 my_families,
                 families,
                 col_emoji=8,
                 activ_emoji='🦕',
                 passive_emoji='▫',
                 start_text='',
                 end_text=''
             ),
             dinos_bar=progress_bar(
                 len(collection), all_dinos,
                 col_emoji=8,
                 activ_emoji='🦖',
                 passive_emoji='▫',
                 start_text='',
                 end_text=''
             ))

    total_pages = max(1, len(collection))
    def wrap_page(p):
        if p < 0:
            return total_pages - 1
        if p >= total_pages:
            return 0
        return p

    prev10 = max(0, page - 10)
    next10 = min(total_pages - 1, page + 10)
    prev1 = wrap_page(page - 1)
    next1 = wrap_page(page + 1)

    buttons = [
        {
            "⏮️": f"mycol_page:{prev10}",
            "⏭️": f"mycol_page:{next10}"
        },
        {
            "⬅️": f"mycol_page:{prev1}",
            f"{page+1}/{total_pages}": "mycol_page:0",
            "➡️": f"mycol_page:{next1}",
        }
    ]
    kb = list_to_inline(buttons, 3)
    return image, text, kb


@HDMessage
@main_router.message(IsPrivateChat(), Command("my_collection"), 
                     IsAuthorizedUser())
@main_router.message(IsPrivateChat(), Text('commands_name.about.my_collection'), 
                     IsAuthorizedUser())
async def my_collection_message(message: Message):
    user_id = message.from_user.id

    collection = await get_dino_collection_by_user(user_id)
    lang = await get_lang(user_id)

    if message.text.startswith("/my_collection"):
        try:
            page = int(message.text.split()[1]) - 1
        except (IndexError, ValueError):
            page = 0

    if not collection:
        await message.answer(t("dino_collection.empty", lang))
        return

    image, text, kb = await get_collection_page_data(user_id, collection, page, lang)

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=image,
        caption=text,
        reply_markup=kb,
        parse_mode='Markdown'
    )


@main_router.callback_query(
    F.data.startswith("mycol_page:"),
    IsPrivateChat(),
    IsAuthorizedUser()
)
async def my_collection_page_callback(call: CallbackQuery):
    user_id = call.from_user.id
    collection = await get_dino_collection_by_user(user_id)
    lang = await get_lang(user_id)

    total_pages = max(1, len(collection))
    page = int(call.data.split(":")[1]) % total_pages

    if not collection:
        await call.answer(t("dino_collection.empty", lang), show_alert=True)
        return

    image, text, kb = await get_collection_page_data(user_id, 
                                                     collection, page, lang)

    await call.message.edit_media(
        media=InputMediaPhoto(media=image, caption=text, parse_mode='Markdown'),
        reply_markup=kb
    )
    await call.answer()
