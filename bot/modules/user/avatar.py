from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import User

from io import BufferedReader
from bot.exec import bot
from bot.modules.images import async_open
from bot.dbmanager import mongo_client

users = LazyCollection(User)

async def get_avatar(user_id: int):
    """Возвращает file_id аватара пользователя или файл, если file_id устарел. Если аватара нет — возвращает дефолт."""
    user = await users.find_one({'userid': user_id}, comment='get_avatar') or {}

    avatar_id = user.get('avatar')
    if avatar_id:
        try:
            # Проверяем, доступен ли файл по file_id
            await bot.get_file(avatar_id)
            return avatar_id
        except Exception:
            # file_id устарел, пробуем обновить
            pass

    # Если аватар не установлен или file_id сброшен/устарел
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.photos:
            photo_id = photos.photos[0][0].file_id
            await users.update_one({'userid': user_id}, {'$set': {'avatar': photo_id}})
            return photo_id
    except Exception:
        pass

    # Если обновить не удалось или у пользователя нет фото, возвращаем дефолт
    avatar: BufferedReader = await async_open('images/remain/dinogochi_user.png', True)  # type: ignore
    await users.update_one({'userid': user_id}, {'$set': {'avatar': ''}})
    return avatar