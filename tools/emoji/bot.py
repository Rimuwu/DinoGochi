import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.formatting import CustomEmoji, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "-"
CUSTOM_EMOJI_ID = "5998907373534583499"  # Твой первый динозавр
# -----------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Используем утилиту форматирования aiogram. 
    # Она автоматически посчитает правильную длину UTF-16 для Telegram.
    content = Text(
        "Р-р-рау! ", 
        CustomEmoji("🦕", custom_emoji_id=CUSTOM_EMOJI_ID), 
        " Бот DinoGochi на связи!"
    )

    # Клавиатуры через официальные параметры
    inline_kb = InlineKeyboardBuilder()
    inline_kb.row(
        types.InlineKeyboardButton(
            text="Инлайн Дино",
            callback_data="dino_clicked",
            icon_custom_emoji_id=CUSTOM_EMOJI_ID  
        )
    )
    
    reply_kb = ReplyKeyboardBuilder()
    reply_kb.row(
        types.KeyboardButton(
            text="Кнопка Дино",
            icon_custom_emoji_id=CUSTOM_EMOJI_ID  
        )
    )

    # Метод as_kwargs() автоматически подставит правильный text и entities с нужными оффсетами
    await message.answer(
        **content.as_kwargs(),
        reply_markup=inline_kb.as_markup()
    )
    
    await message.answer(
        text="А вот и нижняя клавиатура:",
        reply_markup=reply_kb.as_markup(resize_keyboard=True)
    )


@dp.callback_query(lambda c: c.data == "dino_clicked")
async def process_callback(callback_query: types.CallbackQuery):
    await callback_query.answer("🦕 Динозавр передаёт тебе привет!")


async def main():
    print("Бот DinoGochi успешно запущен через автоматический UTF-16 Builder...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())