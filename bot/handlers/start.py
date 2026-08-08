from aiogram import Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_first = html.bold(message.from_user.first_name if message.from_user else "User")
    welcome_text = (
        f"👋 Welcome {user_first} to <b>High Quality Video Downloader Bot</b>!\n\n"
        "⚡ <b>How to use:</b>\n"
        "Simply send me any video URL from platforms like:\n"
        "• YouTube / Shorts\n"
        "• TikTok / Douyin\n"
        "• Instagram Reels / Posts\n"
        "• Twitter / X\n"
        "• Reddit, Facebook, Pinterest & 1000+ sites!\n\n"
        "🎯 I will extract the original high-quality video and send it right back to you with fast-start streaming support!\n\n"
        "<i>Send a video link to begin!</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "💡 <b>Help & Instructions</b>\n\n"
        "1. Copy a video link from any app or browser.\n"
        "2. Paste and send the link to this bot chat.\n"
        "3. Wait a few seconds for downloading, remuxing & uploading.\n\n"
        "⚙️ <b>Features:</b>\n"
        "• Original Audio & Video stream merging\n"
        "• Inline Telegram playable videos with thumbnail & metadata\n"
        "• High speed multi-threaded downloader\n"
        "• Concurrency queue protection"
    )
    await message.answer(help_text, parse_mode="HTML")
