
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, progress_bar, seconds_to_str
from bot.modules.localization import get_lang, t
from aiogram.types import CallbackQuery, Message
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F
import time
from aiogram.types import InputMediaPhoto
from bot.filters.translated_text import Text
from bot.models.user import DinoCollection
from bot.models.dinosaur import Dino
from bot.modules.images import create_dino_centered_image
from bot.modules.dinosaur.dino_count import families, all_dinos

async def get_collection_page_data(user_id, collection, page, lang):
    if page < 0 or page >= len(collection):
        page = 0
    entry = collection[page]
    entry_data = entry.dict()

    data_id = entry_data["data_id"]
    redis_key = f"file_id:dino_col:{data_id}"

    from bot.redismanager import redis_get, redis_set
    from aiogram.types import BufferedInputFile
    from bot.exec import bot as _bot

    cached_file_id = await redis_get(redis_key)
    if cached_file_id:
        image = cached_file_id  # Use Telegram file_id directly
    else:
        # Generate and upload to get file_id
        generated = await create_dino_centered_image(data_id)
        # Send to Telegram to get file_id, then store it
        try:
            tmp_msg = await _bot.send_photo(
                chat_id=user_id,
                photo=generated,
            )
            new_file_id = tmp_msg.photo[-1].file_id
            await redis_set(redis_key, new_file_id)
            await tmp_msg.delete()
            image = new_file_id
        except Exception:
            # Fallback: return raw image bytes if upload fails
            image = generated

    my_families = await DinoCollection.get_count_families(user_id)

    # Load and retrieve family metadata from families.json
    import json
    with open('bot/json/families.json', encoding='utf-8') as f:
        families_data = json.load(f)

    fam_key = next((k for k in families_data if k.lower() == entry_data['familie'].lower()), entry_data['familie'])
    fam_data = families_data.get(fam_key, {})

    raw_cat = fam_data.get('category', 'Herbivore')
    raw_size = fam_data.get('size', 'medium')
    raw_aggr = fam_data.get('aggression', 'medium')
    raw_behav = fam_data.get('behavior', 'solitary')
    raw_period = fam_data.get('period', 'Middle Jurassic')
    length_m = fam_data.get('length_meters', 0.0)

    # Localize values
    loc_cat = t(f"dino_collection.categories.{raw_cat}", lang, default=raw_cat)
    loc_size = t(f"dino_collection.sizes.{raw_size}", lang, default=raw_size)
    loc_aggr = t(f"dino_collection.aggressions.{raw_aggr}", lang, default=raw_aggr)
    loc_behav = t(f"dino_collection.behaviors.{raw_behav}", lang, default=raw_behav)
    loc_period = t(f"dino_collection.periods.{raw_period}", lang, default=raw_period)

    text = t("dino_collection.info", lang, dino_id=data_id,
             uniq=await Dino.get_uniqueness_factor(data_id),
             date=seconds_to_str(int(time.time()) - entry_data["date"], lang),
             rod=entry_data['familie'],
             category=loc_cat,
             size=loc_size,
             length_meters=length_m,
             period=loc_period,
             behavior=loc_behav,
             aggression=loc_aggr,
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


@main_router.message(IsPrivateChat(), Command("my_collection"), 
                     IsAuthorizedUser())
@main_router.message(IsPrivateChat(), Text('commands_name.info_menu.my_collection'), 
                     IsAuthorizedUser())
async def my_collection_message(message: Message):
    user_id = message.from_user.id

    collection = await DinoCollection.get_collection(user_id)
    lang = await get_lang(user_id)
    page = 0


    if message.text.startswith("/my_collection"):
        try:
            page = int(message.text.split()[1]) - 1
        except (IndexError, ValueError):
            page = 0

    if not collection:
        await message.answer(t("dino_collection.empty", lang))
        return

    image, text, kb = await get_collection_page_data(
        user_id, collection, page, lang)

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
    collection = await DinoCollection.get_collection(user_id)
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
