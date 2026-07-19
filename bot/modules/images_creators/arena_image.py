import io
import os
from typing import List, Optional
from PIL import Image
from aiogram.types import BufferedInputFile

def generate_arena_battle_image(team_x_dino_images: List[str], team_y_dino_images: List[str]) -> Optional[BufferedInputFile]:
    """Generates an arena battle image placing Team X (left) and Team Y (right) dinos in memory.

    team_x_dino_images: list of relative image paths (e.g. 'dino-rar/dino_1.png')
    team_y_dino_images: list of relative image paths (e.g. 'dino-rar/dino_2.png')
    returns: BufferedInputFile or None
    """
    try:
        bg_path = 'images/arena/arena.png'
        if not os.path.exists(bg_path):
            return None

        bg = Image.open(bg_path).convert('RGBA')
        W, H = bg.size

        num_x = len(team_x_dino_images)
        num_y = len(team_y_dino_images)

        target_size = 440

        def get_offsets(count):
            if count == 1:
                return [(0, 0)]
            elif count == 2:
                return [(-120, -30), (80, 30)]
            elif count == 3:
                return [(-160, -40), (0, 0), (160, 40)]
            else:  # 4
                return [(-200, -50), (-60, 40), (60, -30), (200, 30)]

        # Process Team X (Left side, facing right) - Feet baseline at Y=870
        center_lx, center_ly = 550, 870
        offsets_x = get_offsets(num_x)
        left_items = []
        for idx, rel_path in enumerate(team_x_dino_images):
            full_p = f"images/{rel_path}"
            if os.path.exists(full_p):
                with Image.open(full_p) as d_img:
                    d_rgba = d_img.convert('RGBA')
                    w_ratio = target_size / float(d_rgba.height)
                    target_w = int(d_rgba.width * w_ratio)
                    d_scaled = d_rgba.resize((target_w, target_size), Image.Resampling.LANCZOS)
                    # Flip to face right
                    d_flip = d_scaled.transpose(Image.FLIP_LEFT_RIGHT)
                    dx, dy = offsets_x[idx] if idx < len(offsets_x) else (0, 0)
                    left_items.append((d_flip, center_lx + dx - target_w // 2, center_ly + dy - target_size, center_ly + dy))

        left_items.sort(key=lambda item: item[3])
        for img, x, y, _ in left_items:
            bg.paste(img, (x, y), img)

        # Process Team Y (Right side, facing left) - Feet baseline at Y=870
        center_rx, center_ry = W - 550, 870
        offsets_y = get_offsets(num_y)
        right_items = []
        for idx, rel_path in enumerate(team_y_dino_images):
            full_p = f"images/{rel_path}"
            if os.path.exists(full_p):
                with Image.open(full_p) as d_img:
                    d_rgba = d_img.convert('RGBA')
                    w_ratio = target_size / float(d_rgba.height)
                    target_w = int(d_rgba.width * w_ratio)
                    d_scaled = d_rgba.resize((target_w, target_size), Image.Resampling.LANCZOS)
                    dx, dy = offsets_y[idx] if idx < len(offsets_y) else (0, 0)
                    right_items.append((d_scaled, center_rx - dx - target_w // 2, center_ry + dy - target_size, center_ry + dy))

        right_items.sort(key=lambda item: item[3])
        for img, x, y, _ in right_items:
            bg.paste(img, (x, y), img)

        bio = io.BytesIO()
        bg.save(bio, format='PNG')
        bio.seek(0)
        return BufferedInputFile(bio.getvalue(), filename="arena_battle.png")
    except Exception as e:
        from bot.modules.logs import log
        log(f"Error generating arena battle image: {e}", lvl=3, prefix="arena_image")
        return None
