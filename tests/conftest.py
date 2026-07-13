import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import motor.motor_asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Reconfigure stdout/stderr to UTF-8 on Windows to prevent UnicodeEncodeError with emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from aiogram.methods import TelegramMethod, SendMessage, AnswerCallbackQuery, SendPhoto, EditMessageText, GetUserProfilePhotos, GetStickerSet, GetMe, EditMessageMedia, GetFile
from aiogram.types import User as TGUser, Chat, Message, Update, CallbackQuery, UserProfilePhotos, StickerSet, Sticker, InlineKeyboardMarkup, File

import bot.config
# Determine MongoDB test URL. If MONGO_TEST_URL is not set, replace docker hostname 'mongo' with 'localhost'
test_mongo_url = os.environ.get("MONGO_TEST_URL")
if not test_mongo_url:
    test_mongo_url = bot.config.conf.mongo_url.replace("@mongo:", "@localhost:")

bot.config.conf.mongo_url = test_mongo_url
bot.config.conf.redis_url = bot.config.conf.redis_url.replace("@redis:", "@localhost:")

# Redirect "dinogochi" to "dinogochi_test" in Motor Client to isolate tests
class TestMotorClient(motor.motor_asyncio.AsyncIOMotorClient):
    def __getitem__(self, name):
        if name == "dinogochi":
            return super().__getitem__("dinogochi_test")
        return super().__getitem__(name)

# Patch the dbmanager clients
import bot.dbmanager
test_client = TestMotorClient(bot.config.conf.mongo_url)
bot.dbmanager.real_mongo_client = test_client
bot.dbmanager.mongo_client = bot.dbmanager.UnifiedMongoClientWrapper(test_client)

# Patch dispatch FSM storage to MemoryStorage
import bot.exec
mem_storage = MemoryStorage()
bot.exec.STORAGE = mem_storage
bot.exec.dp.fsm.storage = mem_storage

import bot.modules.get_state
bot.modules.get_state.STORAGE = mem_storage
import bot.redismanager

# Setup Mock Bot class-wide to intercept all instances including already imported references
if not hasattr(Bot, "_original_call"):
    Bot._original_call = Bot.__call__

async def mocked_call(self, method: TelegramMethod, request_timeout=None, **kwargs):
    if not hasattr(self, "sent_requests"):
        self.sent_requests = []
    self.sent_requests.append(method)
    
    # Return mocked responses depending on request type
    if isinstance(method, SendMessage):
        user_id = int(method.chat_id) if not isinstance(method.chat_id, Chat) else int(method.chat_id.id)
        return Message(
            message_id=999,
            date=asyncio.get_event_loop().time(),
            chat=method.chat_id if isinstance(method.chat_id, Chat) else Chat(id=user_id, type="private"),
            text=method.text,
            from_user=TGUser(id=user_id, is_bot=False, first_name="Test"),
            reply_markup=method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None
        )
    elif isinstance(method, SendPhoto):
        user_id = int(method.chat_id) if not isinstance(method.chat_id, Chat) else int(method.chat_id.id)
        return Message(
            message_id=999,
            date=asyncio.get_event_loop().time(),
            chat=method.chat_id if isinstance(method.chat_id, Chat) else Chat(id=user_id, type="private"),
            photo=[],
            caption=method.caption,
            from_user=TGUser(id=user_id, is_bot=False, first_name="Test"),
            reply_markup=method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None
        )
    elif isinstance(method, EditMessageText):
        return Message(
            message_id=method.message_id or 999,
            date=asyncio.get_event_loop().time(),
            chat=method.chat_id if isinstance(method.chat_id, Chat) else Chat(id=1, type="private"),
            text=method.text,
            reply_markup=method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None
        )
    elif isinstance(method, AnswerCallbackQuery):
        return True
    elif isinstance(method, GetUserProfilePhotos):
        return UserProfilePhotos(total_count=0, photos=[])
    elif isinstance(method, GetStickerSet):
        return StickerSet(
            name=method.name,
            title="Mock Sticker Set",
            sticker_type="regular",
            stickers=[
                Sticker(
                    file_id="mock_sticker_id",
                    file_unique_id="mock_sticker_uniq",
                    width=512,
                    height=512,
                    is_animated=False,
                    is_video=False,
                    type="regular"
                )
            ]
        )
    elif isinstance(method, EditMessageMedia):
        return Message(
            message_id=999,
            date=asyncio.get_event_loop().time(),
            chat=Chat(id=1, type="private"),
            text="[Edited Media Message]",
            reply_markup=method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None
        )
    elif isinstance(method, GetFile):
        return File(
            file_id=method.file_id,
            file_unique_id="mock_file_uniq",
            file_size=12345,
            file_path=None
        )
    elif isinstance(method, GetMe):
        return TGUser(id=self.id, is_bot=True, first_name="DinoGochiBot", username="DinoGochiBot")
        
    return True

Bot.__call__ = mocked_call

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    # Run the standard check_db to initialize Beanie and collections
    await bot.dbmanager.check_db(bot.dbmanager.mongo_client)
    yield
    # Drop database after session runs
    await test_client.drop_database("dinogochi_test")

@pytest.fixture(autouse=True)
async def clean_db():
    # Clean collections before each test to guarantee isolated state
    collections = await test_client["dinogochi_test"].list_collection_names()
    for col in collections:
        if not col.startswith("system."):
            # We don't delete system indexes, just wipe the user data
            await test_client["dinogochi_test"][col].delete_many({})
    # Re-populate defaults
    await bot.dbmanager.create_necessary_documents(bot.dbmanager.mongo_client)
    
    # Wipe FSM memory storage to ensure complete test isolation
    if hasattr(bot.exec.STORAGE, "storage"):
        bot.exec.STORAGE.storage.clear()

    # Clean redis keys
    try:
        await bot.redismanager.init_redis()
        r = bot.redismanager.get_redis()
        for pattern in ["file_id:*", "delete_cooldown:*", "it:*"]:
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)
    except Exception:
        pass

@pytest.fixture
def test_bot():
    b = bot.exec.bot
    if not hasattr(b, "sent_requests"):
        b.sent_requests = []
    b.sent_requests.clear()
    return b

@pytest.fixture
def test_dp():
    return bot.exec.dp

# Bypass AntifloodMiddleware during testing
from bot.middlewares.antiflood import AntifloodMiddleware
async def patched_antiflood_call(self, handler, event, data):
    return await handler(event, data)
AntifloodMiddleware.__call__ = patched_antiflood_call

from bot.middlewares.callback_antiflood import CallbackQueryAntiFloodMiddleware
async def patched_callback_antiflood_call(self, handler, event, data):
    return await handler(event, data)
CallbackQueryAntiFloodMiddleware.__call__ = patched_callback_antiflood_call
