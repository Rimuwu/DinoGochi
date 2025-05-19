
from io import BufferedReader
from bot.exec import bot
from bot.modules.images import async_open
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor

users = DBconstructor(mongo_client.user.users)

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
            # file_id устарел, сбрасываем
            await users.update_one({'userid': user_id}, {'$set': {'avatar': ''}})
            avatar: BufferedReader = await async_open('images/remain/dinogochi_user.png', True)  # type: ignore
            return avatar

    # Если аватар не установлен или file_id сброшен
    photos = await bot.get_user_profile_photos(user_id, limit=1)
    if photos.photos:
        photo_id = photos.photos[0][0].file_id
        await users.update_one({'userid': user_id}, {'$set': {'avatar': photo_id}})
        return photo_id
    else:
        avatar: BufferedReader = await async_open('images/remain/dinogochi_user.png', True)  # type: ignore
        await users.update_one({'userid': user_id}, {'$set': {'avatar': ''}})
        return avatar