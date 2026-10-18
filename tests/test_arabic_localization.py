import pytest
import json
import os
from bot.modules.localization import (
    load,
    languages,
    available_locales,
    alternative_language,
    get_all_locales,
    t,
    get_data
)

def test_arabic_localization_integrity():
    load()
    assert 'ar' in available_locales, "Arabic ('ar') should be in available_locales"
    assert 'ar' in languages, "Arabic ('ar') should be in loaded languages dict"

    ru_path = os.path.normpath("./bot/localization/ru.json")
    ar_path = os.path.normpath("./bot/localization/ar.json")

    with open(ru_path, 'r', encoding='utf-8') as f:
        ru_data = json.load(f)['ru']
    with open(ar_path, 'r', encoding='utf-8') as f:
        ar_data = json.load(f)['ar']

    # 1. Check all critical top-level keys
    critical_keys = [
        'language_name', 'commands_name', 'buttons_name', 'settings_menu',
        'start_command', 'feed', 'collecting', 'all_skills', 'works',
        'put_to_bed', 'awaken', 'stop_game', 'entertainments', 'dino_auto_actions',
        'items_names', 'item_use'
    ]
    for ck in critical_keys:
        assert ck in ar_data, f"Critical key '{ck}' must be present in ar.json"

    # 2. Check language name and selection
    all_langs = get_all_locales('language_name')
    assert 'ar' in all_langs, "'ar' must be returned by get_all_locales('language_name')"
    assert all_langs['ar'] == "🇸🇾 العربية"

    # 3. Test alternative_language resolution
    assert alternative_language('ar') == 'ar'
    assert alternative_language('ar-SA') == 'ar'
    assert alternative_language('ar-EG') == 'ar'
    assert alternative_language('AR_AE') == 'ar'
    assert alternative_language('ua') == 'ru'
    assert alternative_language('en-US') == 'en'

    # 4. Test translation of settings keys
    settings_title = t('settings_menu.title_main', 'ar')
    assert "الإعدادات" in settings_title
    select_lang_title = t('settings_menu.buttons.select_lang_title', 'ar')
    assert "اللغة" in select_lang_title or "اختر" in select_lang_title

    # 5. Check placeholder preservation
    dino_bday = t('dino_birthday.notification', 'ar', name='Рекс', years=2)
    assert 'Рекс' in dino_bday
    assert '2' in dino_bday

    # 6. Ensure no 'no_text_key' for settings_menu
    for btn_key in [
        'notif_dino', 'interface', 'account', 'notifications',
        'talk_mode', 'my_name', 'dino_name', 'lang', 'back_main'
    ]:
        val = t(f'settings_menu.buttons.{btn_key}', 'ar', status='ON')
        assert not val.startswith('no_text_key'), f"Missing translation for settings_menu.buttons.{btn_key}"
