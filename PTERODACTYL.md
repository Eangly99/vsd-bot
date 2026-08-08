# 🦕 Deploying `vsd-bot` on Pterodactyl Panel

This guide walks you through deploying the **High-Tech Telegram Video Downloader Bot** on any Pterodactyl Panel instance.

---

## 🎯 Option A: Quick Upload to Existing Python Server (Easiest)

If you already have a **Generic Python** server running on Pterodactyl:

1. **Upload Files**:
   - Upload all files from this project directory (`main.py`, `config/`, `bot/`, `services/`, `utils/`, `requirements.txt`, etc.) to your server's root directory (`/home/container` or `/mnt/server`) using Pterodactyl's **File Manager** or SFTP.

2. **Configure Environment Variables**:
   - In Pterodactyl, go to **Settings** -> **Startup** (or edit the `.env` file in File Manager).
   - Set the environment variable:
     - `BOT_TOKEN`: `Your_Telegram_Bot_Token_From_BotFather`
     - `MAX_CONCURRENT_DOWNLOADS`: `3`
     - `MAX_FILE_SIZE_MB`: `2000`

3. **Install Dependencies & Run**:
   - Set Startup Command in Pterodactyl Panel to:
     ```bash
     pip install --no-cache-dir -r requirements.txt && python main.py
     ```
   - Click **Console** -> **Start**.

---

## 🦖 Option B: Import Custom Pterodactyl Egg (Admin / Host Owners)

If you own or manage the Pterodactyl Panel Admin dashboard:

1. Go to **Admin Panel** -> **Nests** -> **Import Egg**.
2. Upload the included [`pterodactyl-egg.json`](file:///f:/Projects/vsd-bot/pterodactyl-egg.json).
3. Select an existing nest (e.g. `Python` or `Generic`).
4. Create a new server using this newly imported **Telegram Video Downloader Bot** Egg.
5. Enter your `BOT_TOKEN` in the Environment Variables input field.
6. Launch the server!

---

## 💡 Key Features Active on Pterodactyl:

- 🛠 **FFmpeg Auto-Fallback**: If your Pterodactyl container doesn't have system `ffmpeg` pre-installed, `vsd-bot` automatically uses `imageio-ffmpeg` static binary fallback!
- ⚡ **Stream FastStart**: MP4 videos are automatically processed with `+faststart` metadata so users can watch them instantly in Telegram while buffering.
- 🧹 **Auto Storage Cleanup**: Temporary download chunks are automatically purged after sending to avoid filling up your Pterodactyl disk quota.
