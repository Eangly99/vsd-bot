import asyncio
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import yt_dlp

from config.settings import settings
from services.ffmpeg_service import ffmpeg_service
from utils.logger import logger
from utils.helpers import cleanup_file


@dataclass
class DownloadResult:
    file_path: str
    title: str
    uploader: str
    platform: str
    duration: int
    width: Optional[int]
    height: Optional[int]
    thumbnail_path: Optional[str]
    file_size_bytes: int
    original_url: str


class YtDownloader:
    def __init__(self):
        self.download_dir = settings.get_download_path()

    def _get_ydl_opts(
        self,
        output_template: str,
        use_cookies: bool = True,
        player_clients: Optional[list] = None,
        progress_hook: Optional[Callable] = None
    ) -> Dict[str, Any]:
        ffmpeg_bin = ffmpeg_service.get_ffmpeg_path()
        ffmpeg_dir = str(Path(ffmpeg_bin).parent)

        if player_clients is None:
            # Optimal default clients for cloud/datacenter IPs
            player_clients = ["tv_embedded", "android_vr", "android", "ios", "mweb"]

        opts: Dict[str, Any] = {
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg_dir,
            "updatetime": False,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": False,
            "writethumbnail": True,
            "concurrent_fragment_downloads": 5,
            "extractor_args": {
                "youtube": {
                    "player_client": player_clients
                }
            },
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                }
            ]
        }

        # Check for cookies file if requested
        if use_cookies:
            cookies_path = Path(settings.cookies_file)
            if cookies_path.exists() and cookies_path.stat().st_size > 0:
                logger.info(f"Loaded YouTube cookies from: {cookies_path.name}")
                opts["cookiefile"] = str(cookies_path.resolve())
            elif Path("cookies.txt").exists() and Path("cookies.txt").stat().st_size > 0:
                logger.info("Loaded YouTube cookies from: cookies.txt")
                opts["cookiefile"] = str(Path("cookies.txt").resolve())

        # Proxy support for datacenter IP bypass
        if settings.youtube_proxy:
            logger.info(f"Using YouTube Proxy: {settings.youtube_proxy}")
            opts["proxy"] = settings.youtube_proxy

        # OAuth2 support
        if settings.youtube_oauth2:
            opts["extractor_args"]["youtube"]["oauth2"] = True

        if progress_hook:
            opts["progress_hooks"] = [progress_hook]

        return opts

    async def download_video(
        self,
        url: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> DownloadResult:
        """
        Extracts info and downloads video from URL in original high quality with automatic multi-tier fallbacks.
        """
        task_id = str(uuid.uuid4())[:8]
        raw_output_tmpl = str(self.download_dir / f"{task_id}_%(id)s.%(ext)s")

        loop = asyncio.get_running_loop()

        def _progress_hook(d: Dict[str, Any]):
            if progress_callback and d.get("status") == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                percent = (downloaded / total_bytes * 100) if total_bytes > 0 else 0.0
                speed = d.get("_speed_str", "N/A")
                loop.call_soon_threadsafe(progress_callback, percent, speed)

        def _exec_download():
            # Define fallback execution tiers tailored for datacenter & cloud hosting environments
            tiers = [
                {
                    "name": "Tier 1 (Cookies + Multi-Client [tv_embedded, android_vr, android, ios, mweb])",
                    "use_cookies": True,
                    "player_clients": ["tv_embedded", "android_vr", "android", "ios", "mweb"]
                },
                {
                    "name": "Tier 2 (No Cookies + Multi-Client [tv_embedded, android_vr, android, ios, mweb])",
                    "use_cookies": False,
                    "player_clients": ["tv_embedded", "android_vr", "android", "ios", "mweb"]
                },
                {
                    "name": "Tier 3 (No Cookies + Embedded/VR Specialized [tv_embedded, android_vr])",
                    "use_cookies": False,
                    "player_clients": ["tv_embedded", "android_vr"]
                },
                {
                    "name": "Tier 4 (No Cookies + Standard Default yt-dlp Extractor)",
                    "use_cookies": False,
                    "player_clients": None
                }
            ]

            last_exception = None

            for tier in tiers:
                logger.info(f"Attempting download with {tier['name']}...")
                opts = self._get_ydl_opts(
                    raw_output_tmpl,
                    use_cookies=tier["use_cookies"],
                    player_clients=tier["player_clients"],
                    progress_hook=_progress_hook
                )
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.sanitize_info(info)
                except Exception as e:
                    last_exception = e
                    err_msg = str(e)
                    logger.warning(f"{tier['name']} failed ({err_msg}). Trying next fallback tier...")

            if last_exception:
                raise last_exception
            raise RuntimeError("Download failed across all fallback tiers.")

        logger.info(f"Starting download for URL: {url}")
        info_dict = await asyncio.to_thread(_exec_download)

        # Locate downloaded file
        title = info_dict.get("title", "Video")
        uploader = info_dict.get("uploader") or info_dict.get("extractor_key", "Unknown")
        platform = info_dict.get("extractor_key", "Video")
        duration = int(info_dict.get("duration") or 0)
        width = info_dict.get("width")
        height = info_dict.get("height")

        # Find matching downloaded video file in folder
        matching_files = list(self.download_dir.glob(f"{task_id}_*"))
        video_file: Optional[Path] = None
        thumb_file: Optional[Path] = None

        for file_p in matching_files:
            if file_p.suffix.lower() in [".mp4", ".mkv", ".webm", ".mov"]:
                video_file = file_p
            elif file_p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                thumb_file = file_p

        if not video_file or not video_file.exists():
            raise FileNotFoundError("Downloaded video file was not found after yt-dlp execution.")

        # Ensure container is faststart MP4
        faststart_path = self.download_dir / f"{task_id}_faststart.mp4"
        remux_ok = await ffmpeg_service.faststart_remux(str(video_file), str(faststart_path))
        if remux_ok and faststart_path.exists():
            cleanup_file(video_file)
            final_video_path = str(faststart_path)
        else:
            final_video_path = str(video_file)

        # Retrieve exact metadata via FFmpeg if missing from yt-dlp
        if not width or not height or not duration:
            meta = await ffmpeg_service.get_video_metadata(final_video_path)
            width = width or meta.get("width")
            height = height or meta.get("height")
            duration = duration or meta.get("duration") or 0

        # Generate thumbnail if not downloaded directly
        final_thumb_path: Optional[str] = None
        if thumb_file and thumb_file.exists():
            final_thumb_path = str(thumb_file)
        else:
            generated_thumb = self.download_dir / f"{task_id}_thumb.jpg"
            gen_ok = await ffmpeg_service.generate_thumbnail(final_video_path, str(generated_thumb))
            if gen_ok:
                final_thumb_path = str(generated_thumb)

        file_size = Path(final_video_path).stat().st_size

        return DownloadResult(
            file_path=final_video_path,
            title=title,
            uploader=uploader,
            platform=platform,
            duration=duration,
            width=width,
            height=height,
            thumbnail_path=final_thumb_path,
            file_size_bytes=file_size,
            original_url=url
        )


yt_downloader = YtDownloader()
