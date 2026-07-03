import json
import re
import sys
from urllib.parse import urlparse
import httpx



# --- НАСТРОЙКИ ---
BOT_TOKEN = input("Введите токен бота: ")
# Ссылка может быть вида t.me/addstickers/ИМЯ_ПАКА или просто ИМЯ_ПАКА
EMOJI_PACK_URL = "https://t.me/addemoji/Dino_Emojis"
OUTPUT_FILE = "emojis.json"
# -----------------


def extract_pack_name(url_or_name: str) -> str:
    """Извлекает уникальное имя пака из ссылки Telegram (addstickers или addemoji)."""
    if "t.me" in url_or_name or "telegram.me" in url_or_name:
        path = urlparse(url_or_name).path
        # Ищет как addstickers/name, так и addemoji/name
        match = re.search(r"(?:addstickers|addemoji)/([^/?#]+)", path)
        if match:
            return match.group(1)
    return url_or_name.strip()


def get_emoji_pack_json():
    pack_name = extract_pack_name(EMOJI_PACK_URL)
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    print(f"Запрашиваю данные для пака: {pack_name}...")

    with httpx.Client() as client:
        # 1. Получаем сам стикер-сет (эмодзи-паки в Телеграме — это разновидность стикер-сетов)
        try:
            response = client.get(
                f"{base_url}/getStickerSet", params={"name": pack_name}
            )
            data = response.json()
        except Exception as e:
            print(f"Ошибка при запросе к API: {e}")
            return

        if not data.get("ok"):
            print(f"API вернул ошибку: {data.get('description')}")
            print(
                "Убедись, что токен правильный, а бот запущен (нажат /start хотя бы раз кем-то)."
            )
            return

        result = data["result"]

        # Проверяем, что это именно пак с кастомными эмодзи
        if not result.get("is_custom_emojis", False):
            print(
                "⚠️ Предупреждение: Похоже, этот пак является обычным стикер-паком, а не премиум-эмодзи."
            )

        stickers = result.get("stickers", [])
        if not stickers:
            print("В паке не найдено эмодзи.")
            return

        # 2. Формируем структуру для JSON
        # ТГ отдаёт id в поле custom_emoji_id, а текстовую замену в поле emoji
        emoji_list = []
        for sticker in stickers:
            emoji_id = sticker.get("custom_emoji_id")
            alt_text = sticker.get("emoji")  # Стандартный эмодзи-заменитель

            if emoji_id:
                emoji_list.append({"id": emoji_id, "alternative": alt_text})

        # 3. Сохраняем результат
        with open("tools/emoji/{}.json".format(pack_name), "w", encoding="utf-8") as f:
            json.dump(emoji_list, f, ensure_ascii=False, indent=4)

        print(
            f"🎉 Успешно! Данные {len(emoji_list)} эмодзи сохранены в tools/emoji/{pack_name}.json"
        )


if __name__ == "__main__":
    if BOT_TOKEN == "ТВОЙ_ТОКЕН_БОТА":
        print("Сначала вставь свой BOT_TOKEN в скрипт!")
        sys.exit(1)
    get_emoji_pack_json()