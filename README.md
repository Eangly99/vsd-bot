# ⚡ High-Tech Telegram Video Downloader Bot (`vsd-bot`)

A state-of-the-art Telegram Bot built with Python `aiogram 3`, `yt-dlp`, `asyncio`, `FFmpeg`, and `Pydantic Settings`. Automatically downloads videos from YouTube, Shorts, TikTok, Instagram Reels, Twitter/X, Reddit, and 1000+ sites in **Original High Quality** and sends them directly as native, streamable Telegram videos.

---

## 🔥 Features

- 🎥 **Original High Quality**: Merges best video stream (`bestvideo`) and best audio stream (`bestaudio`) into high-bitrate MP4 containers.
- ⚡ **Stream FastStart**: Embeds MP4 `+faststart` atom flags via FFmpeg so videos start playing immediately inline in Telegram.
- 🖼 **Auto Metadata & Thumbnail**: Probes exact resolution (width x height), duration, and generates crisp poster frame thumbnails.
- ⚙️ **Async Task Queue**: Concurrency worker pool manages concurrent heavy downloads to prevent server overload.
- 📊 **Real-time UX**: Dynamic progress updates (`📥 Downloading` -> `⚙️ Processing` -> `📤 Uploading`).
- 🦖 **Pterodactyl Ready**: Includes dedicated egg configuration (`pterodactyl-egg.json`), static FFmpeg fallback, and setup guide (`PTERODACTYL.md`).

---

## 🛠 Project Structure

```
vsd-bot/
├── config/
│   └── settings.py          # Pydantic environment configuration
├── bot/
│   ├── middlewares/
│   │   └── throttling.py    # Rate-limiting anti-spam middleware
│   ├── handlers/
│   │   ├── start.py         # /start and /help command handlers
│   │   └── downloader.py    # Link detector, progress updater & telegram uploader
│   └── keyboards/
│       └── inline.py        # Original link source buttons
├── services/
│   ├── yt_downloader.py     # Async yt-dlp wrapper & stream extractor
│   ├── ffmpeg_service.py    # Metadata probe & faststart remuxer
│   └── queue_manager.py     # Worker pool & task queue
├── utils/
│   ├── link_parser.py       # Regex extractor for video links
│   ├── helpers.py           # Size & duration formatters, temp file cleanup
│   └── logger.py            # Loguru logging
├── .env.example             # Environment variables template
├── Dockerfile               # Production multi-stage Docker setup
├── docker-compose.yml       # Docker compose deployment
├── main.py                  # Main entrypoint
├── PTERODACTYL.md           # Pterodactyl Panel deployment guide
└── pterodactyl-egg.json     # Pterodactyl Egg export
```

---

## 🚀 Quick Start (Local / VPS)

1. **Clone repository & copy `.env`**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and insert your Telegram Bot Token**:
   ```env
   BOT_TOKEN=your_token_from_botfather
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the bot**:
   ```bash
   python main.py
   ```

---

## 🦕 Deploying on Pterodactyl Panel

See the step-by-step guide in [`PTERODACTYL.md`](file:///f:/Projects/vsd-bot/PTERODACTYL.md) or import [`pterodactyl-egg.json`](file:///f:/Projects/vsd-bot/pterodactyl-egg.json) into your Pterodactyl Panel!

---

## 🐳 Docker Deployment

```bash
docker-compose up -d --build
```
