from bot.modules.data_format import seconds_to_str
from bot.modules.egg import Egg
from bot.modules.localization import t
from bot.modules.markup import markups_menu as m
from bot.exec import bot

async def egg_profile(chatid: int, egg: Egg, lang: str):
    text = t('p_profile.incubation_text', lang, 
             time_end=seconds_to_str(
        egg.remaining_incubation_time(), lang)
        )
    img = await egg.image(lang)
    await bot.send_photo(chatid, img, caption=text, 
                         reply_markup=await m(chatid, 'last_menu', language_code=lang))