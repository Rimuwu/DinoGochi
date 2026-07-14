import io
import os
from PIL import Image
from bot.exec import bot
from bot.modules.user.avatar import get_avatar
from bot.modules.images_creators.lvl_up import crop_circle
from bot.modules.images import trans_paste

BG_IMAGES = {
    'lvl': 'images/rayting/rayting_image_lvl.png',
    'coins': 'images/rayting/rayting_image_coins.png',
    'super': 'images/rayting/rayting_image_super_coins.png',
    'dontaion_all': 'images/rayting/rayting_image_support.png',
    'dontaion_30d': 'images/rayting/rayting_image_support.png',
}

async def generate_rayting_image(rating_type: str, top_users: list[dict]) -> str:
    """
    Generates a rating image with top-3 users' avatars and saves it to temp/ directory.
    Returns the absolute path to the generated image.
    """
    os.makedirs('temp', exist_ok=True)
    out_path = f'temp/rayting_{rating_type}.png'
    
    bg_path = BG_IMAGES.get(rating_type, 'images/rayting/rayting_image_lvl.png')
    
    with Image.open(bg_path) as bg_img:
        img = bg_img.convert("RGBA")
        
    # Coords for top-3:
    # 1st place: x=88.5, y=83.5
    # 2nd place: x=317.5, y=83.5
    # 3rd place: x=546.5, y=83.5
    coords = [
        (88, 83),  # 1st place
        (317, 83), # 2nd place
        (546, 83)  # 3rd place
    ]
    
    for i, box in enumerate(coords):
        user_id = None
        if i < len(top_users):
            user_id = top_users[i].get('userid')
            
        avatar_img = None
        if user_id:
            try:
                avatar_res = await get_avatar(user_id)
                if isinstance(avatar_res, str) and avatar_res:
                    file_info = await bot.get_file(avatar_res)
                    if file_info and file_info.file_path:
                        imageBinaryBytes = await bot.download_file(file_info.file_path)
                        if imageBinaryBytes:
                            imageStream = io.BytesIO(imageBinaryBytes.read())
                            avatar_img = Image.open(imageStream).convert('RGBA')
            except Exception:
                pass
                
        if avatar_img is None:
            avatar_img = Image.open('images/remain/dinogochi_user.png').convert('RGBA')
            
        # Crop to circle of size 85x85
        avatar_cropped = crop_circle(avatar_img, 85)
        
        # Paste onto background
        img = trans_paste(avatar_cropped, img, alpha=1.0, box=box)
        
    # Convert RGBA to RGB and save
    final_img = img.convert("RGB")
    final_img.save(out_path, "PNG")
    return os.path.abspath(out_path)
