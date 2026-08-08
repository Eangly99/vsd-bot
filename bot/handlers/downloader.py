import asyncio
import os
import uuid
from pathlib import Path
from aiogram import Router, Bot, html
from aiogram.types import Message, FSInputFile
from config.settings import settings
from services.yt_downloader import yt_downloader, DownloadResult
from services.queue_manager import queue_manager
from utils.link_parser import extract_urls, is_supported_url
from utils.helpers import format_bytes, format_seconds, get_file_size_mb, cleanup_file
from utils.logger import logger
from bot.keyboards.inline import get_source_keyboard

router = Router()


async def process_download_job(bot: Bot, status_msg: Message, task_id: str, user_id: int, url: str):
    """
    Executes the video download, metadata extraction, video uploading, and cleanup.
    """
    last_update_percent = 0.0

    async def progress_callback(percent: float, speed_str: str):
        nonlocal last_update_percent
        if abs(percent - last_update_percent) >= 15.0 or percent == 100.0:
            last_update_percent = percent
            blocks = int(percent // 10)
            bar = "■" * blocks + "□" * (10 - blocks)
            try:
                await status_msg.edit_text(
                    f"📥 <b>Downloading Video...</b>\n\n"
                    f"<code>[{bar}] {percent:.1f}%</code>\n"
                    f"🚀 Speed: <b>{speed_str}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    download_result: DownloadResult = None
    try:
        # Step 1: Download
        await status_msg.edit_text("📥 <b>Starting high-quality download...</b>", parse_mode="HTML")
        download_result = await yt_downloader.download_video(url, progress_callback)

        # Step 2: Check File Size
        file_size_mb = get_file_size_mb(download_result.file_path)
        if file_size_mb > settings.max_file_size_mb:
            await status_msg.edit_text(
                f"❌ <b>File too large for Telegram upload!</b>\n\n"
                f"File size: <b>{format_bytes(download_result.file_size_bytes)}</b>\n"
                f"Telegram Bot Upload Limit: <b>{settings.max_file_size_mb} MB</b>",
                parse_mode="HTML"
            )
            return

        # Step 3: Uploading status
        await status_msg.edit_text("📤 <b>Uploading high-quality video to Telegram...</b>", parse_mode="HTML")

        # Prepare Telegram Inputs
        video_input = FSInputFile(download_result.file_path)
        thumb_input = FSInputFile(download_result.thumbnail_path) if download_result.thumbnail_path and os.path.exists(download_result.thumbnail_path) else None

        # Build Caption
        clean_title = html.bold(download_result.title)
        clean_uploader = html.code(download_result.uploader)
        clean_platform = html.code(download_result.platform)
        duration_str = format_seconds(download_result.duration)
        size_str = format_bytes(download_result.file_size_bytes)

        caption = (
            f"🎬 {clean_title}\n\n"
            f"👤 <b>Author:</b> {clean_uploader}\n"
            f"🌐 <b>Platform:</b> {clean_platform}\n"
            f"⏱ <b>Duration:</b> {duration_str} | 📦 <b>Size:</b> {size_str}"
        )

        keyboard = get_source_keyboard(download_result.original_url)

        # Step 4: Send Native Telegram Video
        await bot.send_video(
            chat_id=user_id,
            video=video_input,
            caption=caption,
            parse_mode="HTML",
            duration=download_result.duration,
            width=download_result.width,
            height=download_result.height,
            thumbnail=thumb_input,
            supports_streaming=True,
            reply_markup=keyboard
        )

        # Delete progress message
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error processing video download for {url}: {e}")
        err_str = str(e)
        try:
            if "Sign in to confirm" in err_str or "cookies" in err_str.lower():
                user_err = (
                    "⚠️ <b>YouTube Server IP Authentication Required!</b>\n\n"
                    "Google has flagged this hosting server's IP address and requires YouTube account cookies.\n\n"
                    "💡 <b>To fix this on Pterodactyl Panel:</b>\n"
                    "1. Log into YouTube in your desktop browser.\n"
                    "2. Use the Chrome extension <b>'Get cookies.txt LOCALLY'</b> to export your cookies.\n"
                    "3. Upload the <code>cookies.txt</code> file to your Pterodactyl server root folder.\n"
                    "4. Click <b>Restart</b> on your server console!"
                )
            else:
                user_err = (
                    f"❌ <b>Download Failed!</b>\n\n"
                    f"Error: <code>{html.escape(err_str[:300])}</code>\n\n"
                    f"<i>Please verify the link is public and accessible.</i>"
                )
            await status_msg.edit_text(user_err, parse_mode="HTML")
        except Exception:
            pass
    finally:
        # Cleanup temporary files
        if download_result and not settings.keep_temp_files:
            cleanup_file(download_result.file_path)
            cleanup_file(download_result.thumbnail_path)


@router.message()
async def handle_video_link(message: Message, bot: Bot):
    if not message.text:
        return

    urls = extract_urls(message.text)
    if not urls:
        return

    target_url = urls[0]
    if not is_supported_url(target_url):
        return

    task_id = str(uuid.uuid4())[:8]
    status_msg = await message.reply("⏳ <b>Adding request to processing queue...</b>", parse_mode="HTML")

    async def _queue_job(t_id: str, u_id: int, url: str):
        await process_download_job(bot, status_msg, t_id, u_id, url)

    pos = await queue_manager.add_task(task_id, message.chat.id, target_url, _queue_job)
    if pos > 1:
        try:
            await status_msg.edit_text(f"⏳ <b>Queued! Position in queue: #{pos}</b>", parse_mode="HTML")
        except Exception:
            pass
