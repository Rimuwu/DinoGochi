from bot.models.user import User

from io import BufferedReader
from bot.exec import bot
from bot.modules.images import async_open
from bot.dbmanager import mongo_client

async def get_avatar(user_id: int):
    """Возвращает file_id аватара пользователя или файл, если file_id устарел. Если аватара нет — возвращает дефолт."""
    user = await User.find_one(User.userid == user_id)
    user_dict = user.dict() if user else {}

    avatar_id = user_dict.get('avatar')
    if avatar_id:
        return avatar_id

    # Если аватар не установлен или file_id сброшен/устарел
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.photos:
            photo_id = photos.photos[0][0].file_id
            if user:
                await user.set_avatar(photo_id)
            return photo_id
    except Exception:
        pass

    # Если обновить не удалось или у пользователя нет фото, возвращаем дефолт
    avatar: BufferedReader = await async_open('images/remain/dinogochi_user.png', True)  # type: ignore
    if user:
        await user.set_avatar('')
    return avatar