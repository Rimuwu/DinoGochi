from IPython.core import pylabtools
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InputSticker
from aiogram.utils.formatting import CustomEmoji, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import dotenv
import os

dotenv.load_dotenv()

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
        " Бот DinoGochi на связи!\n\n"
        "Отправь мне премиум-эмодзи или команду `/pack <премиум-эмодзи>`, чтобы получить весь пак!"
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


@dp.message(Command("copy_pack", "copy"))
async def cmd_copy_pack(message: types.Message):
    custom_emoji_entity = None
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            if entity.type == "custom_emoji":
                custom_emoji_entity = entity
                break
                
    if not custom_emoji_entity:
        await message.answer(
            "Пожалуйста, используйте команду в формате: `/copy_pack <премиум-эмодзи>`"
        )
        return
        
    custom_emoji_id = custom_emoji_entity.custom_emoji_id
    status_msg = await message.answer("🔍 Получаю информацию о паке...")
    
    try:
        stickers = await message.bot.get_custom_emoji_stickers([custom_emoji_id])
        if not stickers:
            await status_msg.edit_text("❌ Не удалось получить информацию об этом эмодзи.")
            return
            
        sticker = stickers[0]
        set_name = sticker.set_name
        if not set_name:
            await status_msg.edit_text("❌ Этот эмодзи не принадлежит какому-либо паку.")
            return
            
        sticker_set = await message.bot.get_sticker_set(set_name)
        
        await status_msg.edit_text(f"📦 Копирую пак: *{sticker_set.title}* ({len(sticker_set.stickers)} эмодзи)...")
        
        input_stickers = []
        for s in sticker_set.stickers:
            if s.is_animated:
                fmt = "animated"
            elif s.is_video:
                fmt = "video"
            else:
                fmt = "static"
                
            input_stickers.append(
                InputSticker(
                    sticker=s.file_id,
                    format=fmt,
                    emoji_list=[s.emoji or "🦕"]
                )
            )
            
        if not input_stickers:
            await status_msg.edit_text("❌ В исходном паке не найдено подходящих стикеров/эмодзи.")
            return
            
        bot_user = await message.bot.get_me()
        bot_username = bot_user.username
        
        clean_prefix = "".join(c for c in sticker_set.name.split("_by_")[0] if c.isalnum() or c == "_")
        if not clean_prefix or not clean_prefix[0].isalpha():
            clean_prefix = "e" + clean_prefix
            
        new_set_name = f"e_{message.from_user.id}_{clean_prefix[:20]}_by_{bot_username}"
        new_title = f"{sticker_set.title} (Копия)"
        
        await message.bot.create_new_sticker_set(
            user_id=message.from_user.id,
            name=new_set_name,
            title=new_title,
            stickers=input_stickers,
            sticker_type="custom_emoji"
        )
        
        await status_msg.edit_text(
            f"✅ Пак успешно скопирован!\n"
            f"**Название:** {new_title}\n"
            f"**Ссылка:** t.me/addemoji/{new_set_name}"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Произошла ошибка при копировании: {str(e)}")


@dp.message(Command("create_all_packs"))
async def cmd_create_all_packs(message: types.Message):
    user_id = message.from_user.id
    
    await message.answer("🚀 Запуск процесса создания паков динозавров и яиц в фоновом режиме...\n"
                         "Это может занять очень много времени из-за лимитов Telegram.\n"
                         "Прогресс будет отправляться в этот чат.")
    
    async def report_progress(text: str):
        try:
            await message.answer(f"📢 [Загрузка]: {text}")
        except Exception as e:
            print(f"Failed to send progress report to user: {e}")
            
    from upload_assets import upload_all
    asyncio.create_task(upload_all(message.bot, user_id, report_progress))


@dp.message()
async def handle_emoji_pack(message: types.Message):
    custom_emoji_entity = None
    
    # Ищем сущность премиум-эмодзи в тексте или подписи
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            if entity.type == "custom_emoji":
                custom_emoji_entity = entity
                break
                
    if not custom_emoji_entity:
        if message.text and message.text.startswith("/"):
            await message.answer("Пожалуйста, отправьте премиум-эмодзи вместе с командой (например: `/pack 🦕` или просто отправьте эмодзи).")
        return

    custom_emoji_id = custom_emoji_entity.custom_emoji_id
    try:
        stickers = await message.bot.get_custom_emoji_stickers([custom_emoji_id])
        if not stickers:
            await message.answer("Не удалось получить информацию об этом эмодзи.")
            return
        
        sticker = stickers[0]
        set_name = sticker.set_name
        if not set_name:
            await message.answer("Этот эмодзи не принадлежит какому-либо паку.")
            return
            
        sticker_set = await message.bot.get_sticker_set(set_name)
        
        lines = []
        for s in sticker_set.stickers:
            if s.custom_emoji_id:
                # Формат: премиум эмоджи, альтернатива
                lines.append(
                    Text(
                        CustomEmoji(s.emoji, custom_emoji_id=s.custom_emoji_id),
                        f" , {s.emoji} (ID: `{s.custom_emoji_id}`)"
                    )
                )
        
        if not lines:
            await message.answer("В этом паке не найдено премиум-эмодзи.")
            return

        await message.answer(f"Пак: {sticker_set.title} (`{sticker_set.name}`)\nВсего эмодзи: {len(lines)}")
        
        # Отправляем частями по 30 штук, чтобы избежать превышения лимитов
        from aiogram.utils.formatting import as_list
        chunk_size = 30
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i+chunk_size]
            content = as_list(*chunk)
            await message.answer(**content.as_kwargs())
            
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


async def main():
    print("Бот DinoGochi успешно запущен через автоматический UTF-16 Builder...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())