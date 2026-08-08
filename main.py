import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.token import TokenValidationError

from config.settings import settings
from utils.logger import logger
from services.queue_manager import queue_manager
from services.ffmpeg_service import ffmpeg_service
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.handlers import start_router, downloader_router


async def main():
    if not settings.bot_token:
        logger.error("BOT_TOKEN is not configured! Set BOT_TOKEN in .env or environment variables.")
        sys.exit(1)

    # Initialize FFmpeg check
    try:
        ffmpeg_bin = ffmpeg_service.get_ffmpeg_path()
        logger.info(f"FFmpeg verified at: {ffmpeg_bin}")
    except Exception as e:
        logger.error(f"FFmpeg check failed: {e}")
        sys.exit(1)

    # Initialize Bot & Dispatcher
    try:
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    except TokenValidationError:
        logger.error(
            "❌ INVALID TELEGRAM BOT TOKEN!\n"
            "Please set a valid Telegram Bot Token from @BotFather.\n"
            "• On Pterodactyl Panel: Go to Startup / Startup Parameters -> BOT_TOKEN variable.\n"
            "• On VPS / Local: Edit your .env file and set BOT_TOKEN=your_token_here"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize Telegram Bot: {e}")
        sys.exit(1)

    dp = Dispatcher()

    # Register Middlewares
    dp.message.middleware(ThrottlingMiddleware(rate_limit_seconds=2.5))

    # Register Routers
    dp.include_router(start_router)
    dp.include_router(downloader_router)

    # Start Queue Manager Workers
    await queue_manager.start()

    # Delete Webhook & Start Polling
    logger.info("Bot starting long polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down bot...")
        await queue_manager.stop()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process stopped manually.")
