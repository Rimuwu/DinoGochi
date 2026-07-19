from bot.config import conf
from bot.modules.logs import log

def log_startup_banners():
    log('# ====== Inicialization Start ====== #', 2)
    log('Привет! Я вижу ты так и не починил тот самый баг на 46-ой строчке...')
    log('Это не баг, а фича!')
    log('Ваша фича наминирована на оскар!')
    log('Спасибо, но я все равно перепишу все с нуля...')
    log('У вас логи не логятся :/')
    log('Не вижу ошибок == нет ошибок!')
    log('Кстати, в создании бота поучаствовал ChatGPT')
    log('Ой, да что там ваш ChatGPT?! *Stable Diffusion подключился*')

def initialize_assets():
    # Прегенерация изображений предметов и автогенерация конфига эмодзи
    try:
        from bot.modules.items.image_generator import pregenerate_item_images, auto_generate_items_emojis_json
        if getattr(conf, 'pregenerate_images', True):
            pregenerate_item_images()
        if getattr(conf, 'sync_custom_emojis', False):
            auto_generate_items_emojis_json()
        from bot.const import reload_const
        reload_const()
    except Exception as e:
        log(f"Ошибка при инициализации изображений/эмодзи предметов: {e}", lvl=3)
