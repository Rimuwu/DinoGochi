
from bot.exec import bot
from bot.modules.images import async_open
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor

users = DBconstructor(mongo_client.user.users)

async def get_avatar(user_id: int):
    """Возвращает аватарку пользователя, если файл устарел - обновляет и возвращает новую."""
    user = await users.find_one({'userid': user_id}, comment='get_avatar') or {}

    if not user.get('avatar'):
        # Если аватар не установлен, пробуем получить новый
        photos = await bot.get_user_profile_photos(user.get('userid', 0), limit=1)
        if photos.photos:
            photo_id = photos.photos[0][0].file_id
            user['avatar'] = photo_id
            await users.update_one({'userid': user_id}, {'$set': {'avatar': photo_id}})
        else:
            avatar = await async_open('images/remain/dinogochi_user.png', True)
            await users.update_one({'userid': user_id}, {'$set': {'avatar': ''}})
            return avatar

    try:
        await bot.get_file(user['avatar'])
    except Exception:
        # Если файл не найден или устарел, сбрасываем аватар и возвращаем дефолт
        avatar = await async_open('images/remain/dinogochi_user.png', True)
        await users.update_one({'userid': user_id}, {'$set': {'avatar': ''}})
        return avatar

    return user['avatar']