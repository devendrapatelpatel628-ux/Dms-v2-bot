# ============================================================
#         ZENKAI DMS FORWARDING BOT - MAIN ENTRY POINT
# ============================================================

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ChatJoinRequest

from config import BOT_TOKEN, OWNER_ID, BOT_NAME, BOT_VERSION
from database import (
    init_db,
    add_proxy_source,
    get_proxy_sources,
    add_pending_request,
)
from config import PROXY_SOURCES
from middlewares import (
    UserRegistrationMiddleware,
    BanCheckMiddleware,
    ForceSubscribeMiddleware,
    PrivateChatMiddleware,
    APIConfiguredMiddleware,
    LoggingMiddleware,
)
from handlers import router
from admin import admin_router
from engine import (
    hunt_proxies,
    init_semaphore,
)

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "zenkai_bot.log",
            encoding="utf-8"
        ),
    ]
)

logger = logging.getLogger(__name__)


# ============================================================
# STARTUP TASKS
# ============================================================

async def on_startup(bot: Bot):
    """
    Runs on bot startup.
    Initializes DB, semaphore, proxy sources,
    and notifies owner.
    """
    logger.info(f"Starting {BOT_NAME} v{BOT_VERSION}...")

    # Initialize database
    await init_db()
    logger.info("Database initialized.")

    # Ensure pending_requests table exists
    import aiosqlite
    from config import DATABASE_NAME
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_requests (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                channel_id   INTEGER NOT NULL,
                requested_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, channel_id)
            )
        """)
        await db.commit()
    logger.info("pending_requests table ensured.")

    # Initialize concurrency semaphore
    await init_semaphore()
    logger.info("Semaphore initialized.")

    # Seed default proxy sources into DB
    existing_sources = await get_proxy_sources()
    existing_urls = [s["url"] for s in existing_sources]

    for url in PROXY_SOURCES:
        if url not in existing_urls:
            await add_proxy_source(url)

    logger.info(
        f"Proxy sources seeded: {len(PROXY_SOURCES)} sources."
    )

    # Notify owner
    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"✅ <b>{BOT_NAME}</b> is now online!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 <b>Version:</b> {BOT_VERSION}\n"
                f"🕐 <b>Status:</b> All systems running\n"
                f"🌐 <b>Proxy Hunter:</b> Starting...\n"
                f"⚡ <b>Semaphore:</b> Initialized\n\n"
                f"Use <b>⚙️ Admin Panel</b> to manage."
            )
        )
        logger.info("Owner notified of startup.")
    except Exception as e:
        logger.warning(f"Could not notify owner: {e}")


# ============================================================
# SHUTDOWN TASKS
# ============================================================

async def on_shutdown(bot: Bot):
    """
    Runs on bot shutdown.
    Notifies owner and cleans up.
    """
    logger.info("Bot shutting down...")

    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"🔴 <b>{BOT_NAME}</b> is going offline.\n\n"
                f"All tasks have been stopped."
            )
        )
    except Exception:
        pass

    logger.info("Bot shutdown complete.")


# ============================================================
# BACKGROUND TASK RUNNER
# ============================================================

async def start_background_tasks():
    """Start all background tasks."""
    logger.info("Starting background tasks...")

    # Proxy hunter
    asyncio.create_task(
        hunt_proxies(),
        name="proxy_hunter"
    )

    # FIX: Connection pool cleanup
    from userbot import cleanup_idle_connections
    asyncio.create_task(
        cleanup_idle_connections(),
        name="pool_cleanup"
    )

    logger.info(
        "Proxy hunter and pool cleanup started."
    )

async def on_chat_join_request(
    event: ChatJoinRequest
):
    """Track pending join requests to allow
    force-sub bypass for users who requested."""
    try:
        await add_pending_request(
            user_id=event.from_user.id,
            channel_id=event.chat.id,
        )
        logger.info(
            f"Tracked pending: "
            f"user={event.from_user.id} "
            f"channel={event.chat.id}"
        )
    except Exception as e:
        logger.warning(
            f"Failed to track pending: {e}"
        )

# ============================================================
# MAIN FUNCTION
# ============================================================

async def main():
    """
    Main entry point.
    Sets up bot, dispatcher, middlewares,
    routers, and starts polling.
    """

    # --------------------------------------------------------
    # Validate config
    # --------------------------------------------------------
    if not BOT_TOKEN:
        logger.critical(
            "BOT_TOKEN is not set in .env file!"
        )
        sys.exit(1)

    if not OWNER_ID:
        logger.critical(
            "OWNER_ID is not set in .env file!"
        )
        sys.exit(1)

    # --------------------------------------------------------
    # Initialize Bot
    # --------------------------------------------------------
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # --------------------------------------------------------
    # Initialize Dispatcher with FSM Storage
    # --------------------------------------------------------
    dp = Dispatcher(storage=MemoryStorage())

    # --------------------------------------------------------
    # Register Middlewares (Order matters!)
    # --------------------------------------------------------

    # 1. Private chat only
    dp.message.middleware(PrivateChatMiddleware())
    dp.callback_query.middleware(PrivateChatMiddleware())

    # 2. Register/update user
    dp.message.middleware(UserRegistrationMiddleware())
    dp.callback_query.middleware(
        UserRegistrationMiddleware()
    )

    # 3. Ban check
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    # 4. Force subscribe check
    dp.message.middleware(ForceSubscribeMiddleware())
    dp.callback_query.middleware(
        ForceSubscribeMiddleware()
    )

    # 5. API configured check
    dp.message.middleware(APIConfiguredMiddleware())
    dp.callback_query.middleware(
        APIConfiguredMiddleware()
    )

    # 6. Logging
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # --------------------------------------------------------
    # Register Routers (Order matters!)
    # Admin router first (owner filter applied inside)
    # --------------------------------------------------------
    dp.include_router(admin_router)
    dp.include_router(router)
    dp.chat_join_request.register(on_chat_join_request)

    # --------------------------------------------------------
    # Register Startup/Shutdown hooks
    # --------------------------------------------------------
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # --------------------------------------------------------
    # Start background tasks
    # --------------------------------------------------------
    await start_background_tasks()

    # --------------------------------------------------------
    # Start polling
    # --------------------------------------------------------
    logger.info(
        f"{BOT_NAME} v{BOT_VERSION} is running..."
    )

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    except Exception as e:
        logger.critical(f"Polling failed: {e}")
        raise
    finally:
        await bot.session.close()
        logger.info("Bot session closed.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)