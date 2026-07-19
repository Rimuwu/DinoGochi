"""
Referral image generator.
Draws coins/SC icons and item icons onto the referral_image.png template (1920x1080)
using PixelAzureBonds font and _generate_dynamic_rare_icon.
"""

import asyncio
import io
import json
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

# Cached generated image bytes
_referral_image_cache: Optional[bytes] = None

INVITER_BOXES = {
    1:  (154, 209, 460, 300),
    5:  (464, 700, 760, 859),
    15: (774, 209, 1090, 300),
    30: (1130, 700, 1460, 859),
    50: (1394, 209, 1770, 300),
}

INVITEE_ZONES = {
    1:  (155, 335, 460, 415),
    5:  (460, 638, 755, 678),
    15: (775, 335, 1090, 415),
    30: (1385, 540, 1490, 670),
    50: (1395, 335, 1770, 415),
}


def _fmt(n: int) -> str:
    if n >= 1000:
        return f"{n:,}".replace(",", ".")
    return str(n)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype('fonts/PixelAzureBonds.ttf', size=size)
    except Exception:
        return ImageFont.load_default()


def _generate_sync(levels_cfg: dict) -> bytes:
    from bot.modules.images import _generate_dynamic_rare_icon

    base = Image.open('images/remain/referral_image.png').convert('RGBA')
    coin_img = Image.open('images/emojis/coin.png').convert('RGBA')
    sc_img = Image.open('images/emojis/super_coin.png').convert('RGBA')

    font_large = _load_font(32)
    font_medium = _load_font(18)

    draw = ImageDraw.Draw(base)

    for lvl in [1, 5, 15, 30, 50]:
        lvl_data = levels_cfg.get(str(lvl), {})
        coins = lvl_data.get('inviter_coins', 0)
        sc = lvl_data.get('inviter_sc', 0)
        invited_items = lvl_data.get('invited_items', [])

        # --- Inviter Box ---
        if lvl in INVITER_BOXES:
            ix1, iy1, ix2, iy2 = INVITER_BOXES[lvl]
            iw = ix2 - ix1
            ih = iy2 - iy1

            entries = []
            if coins > 0:
                entries.append(('coin', _fmt(coins), (255, 215, 80)))
            if sc > 0:
                entries.append(('sc', str(sc), (100, 220, 255)))

            icon_dim = 36
            spacing = 8

            if len(entries) == 1:
                etype, etext, ecolor = entries[0]
                icon = coin_img if etype == 'coin' else sc_img
                icon_resized = icon.resize((icon_dim, icon_dim), Image.Resampling.LANCZOS)
                bbox = draw.textbbox((0, 0), etext, font=font_large)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                total_w = icon_dim + spacing + tw
                start_x = ix1 + (iw - total_w) // 2
                start_y = iy1 + (ih - icon_dim) // 2

                base.paste(icon_resized, (start_x, start_y), icon_resized)
                draw.text((start_x + icon_dim + spacing, start_y + (icon_dim - th) // 2 - 4), etext, font=font_large, fill=ecolor)

            elif len(entries) == 2:
                total_h = 2 * icon_dim + 4
                top_y = iy1 + (ih - total_h) // 2
                for idx, (etype, etext, ecolor) in enumerate(entries):
                    icon = coin_img if etype == 'coin' else sc_img
                    icon_resized = icon.resize((icon_dim, icon_dim), Image.Resampling.LANCZOS)
                    bbox = draw.textbbox((0, 0), etext, font=font_large)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]

                    total_w = icon_dim + spacing + tw
                    start_x = ix1 + (iw - total_w) // 2
                    curr_y = top_y + idx * (icon_dim + 4)

                    base.paste(icon_resized, (start_x, curr_y), icon_resized)
                    draw.text((start_x + icon_dim + spacing, curr_y + (icon_dim - th) // 2 - 4), etext, font=font_large, fill=ecolor)

        # --- Invitee Box ---
        if lvl in INVITEE_ZONES:
            zx1, zy1, zx2, zy2 = INVITEE_ZONES[lvl]
            zw = zx2 - zx1
            zh = zy2 - zy1

            item_counts = {}
            for item_id in invited_items:
                item_counts[item_id] = item_counts.get(item_id, 0) + 1

            unique_items = list(item_counts.items())
            num_unique = len(unique_items)

            if num_unique > 0:
                icon_sz = min(52, zh, (zw - (num_unique - 1) * 4) // num_unique)
                item_gap = 4
                total_items_w = num_unique * icon_sz + (num_unique - 1) * item_gap
                start_item_x = zx1 + (zw - total_items_w) // 2
                start_item_y = zy1 + (zh - icon_sz) // 2

                for i, (item_id, count) in enumerate(unique_items):
                    item_icon = _generate_dynamic_rare_icon(item_id).resize((icon_sz, icon_sz), Image.Resampling.LANCZOS)
                    curr_x = start_item_x + i * (icon_sz + item_gap)
                    base.paste(item_icon, (curr_x, start_item_y), item_icon)

                    if count > 1:
                        cnt_str = f'x{count}'
                        bbox = draw.textbbox((0, 0), cnt_str, font=font_medium)
                        cw = bbox[2] - bbox[0]
                        ch = bbox[3] - bbox[1]
                        badge_x = curr_x + icon_sz - cw
                        badge_y = start_item_y + icon_sz - ch
                        draw.text((badge_x + 1, badge_y + 1), cnt_str, font=font_medium, fill=(0, 0, 0, 255))
                        draw.text((badge_x, badge_y), cnt_str, font=font_medium, fill=(255, 230, 100, 255))

    out = io.BytesIO()
    base.convert('RGB').save(out, 'JPEG', quality=95)
    out.seek(0)
    return out.read()


async def generate_referral_image() -> bytes:
    """Generate and cache referral info image. Returns raw JPEG bytes."""
    global _referral_image_cache
    if _referral_image_cache is not None:
        return _referral_image_cache

    from bot.const import GAME_SETTINGS as gs
    levels_cfg = gs.get('referal', {}).get('levels', {})

    loop = asyncio.get_running_loop()
    image_bytes = await loop.run_in_executor(None, _generate_sync, levels_cfg)
    _referral_image_cache = image_bytes
    return image_bytes


def invalidate_referral_image_cache() -> None:
    """Invalidate cached image."""
    global _referral_image_cache
    _referral_image_cache = None
