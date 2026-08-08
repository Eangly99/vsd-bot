"""
Cobalt API Integration Service (https://github.com/imputnet/cobalt/tree/main/api)

Uses the official Cobalt processing endpoint (POST /) to fetch direct video
stream links for YouTube, TikTok, Twitter/X, Instagram, and 40+ platforms,
bypassing bot-checks and datacenter IP blocks.
"""
import asyncio
import time
import uuid
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import aiohttp

from config.settings import settings
from services.ffmpeg_service import ffmpeg_service
from utils.logger import logger
from utils.helpers import cleanup_file


class CobaltService:
    def __init__(self):
        self.download_dir = settings.get_download_path()

    def get_api_instances(self) -> List[str]:
        """Returns list of Cobalt API instances to try in order."""
        instances = []
        if settings.cobalt_api_url:
            instances.append(settings.cobalt_api_url.rstrip("/"))
        
        # Default public / community instances
        default_instances = [
            "https://api.cobalt.tools",
            "https://cobalt-api.kwiatekm.pl",
            "https://api.cobalt.74.82.28.16.sslip.io",
        ]
        for inst in default_instances:
            if inst not in instances:
                instances.append(inst)
        return instances

    async def fetch_media_info(self, url: str) -> Dict[str, Any]:
        """
        Calls Cobalt API POST / to retrieve stream download details.
        https://github.com/imputnet/cobalt/tree/main/api#post-
        """
        payload = {
            "url": url,
            "videoQuality": "1080",
            "audioFormat": "mp3",
            "downloadMode": "auto",
            "filenameStyle": "basic"
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "vsd-bot/1.0"
        }
        if settings.cobalt_api_key:
            headers["Authorization"] = f"Api-Key {settings.cobalt_api_key}"

        instances = self.get_api_instances()
        last_error = None

        async with aiohttp.ClientSession() as session:
            for instance_url in instances:
                api_endpoint = f"{instance_url}/"
                logger.info(f"Requesting media stream from Cobalt API: {api_endpoint}")
                try:
                    async with session.post(
                        api_endpoint,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            status = data.get("status")

                            if status in ("redirect", "tunnel"):
                                logger.info(f"Cobalt API success ({status}): {data.get('url')[:60]}...")
                                return data
                            elif status == "picker":
                                items = data.get("picker", [])
                                if items and "url" in items[0]:
                                    logger.info(f"Cobalt API picker success: returned {len(items)} items")
                                    return {"status": "redirect", "url": items[0]["url"], "filename": "video.mp4"}
                            elif status == "error":
                                err_code = data.get("error", {}).get("code", "unknown_error")
                                logger.warning(f"Cobalt API at {instance_url} returned error: {err_code}")
                                last_error = RuntimeError(f"Cobalt error: {err_code}")
                        else:
                            resp_text = await resp.text()
                            logger.warning(f"Cobalt API HTTP {resp.status} from {instance_url}: {resp_text[:150]}")
                            last_error = RuntimeError(f"Cobalt HTTP {resp.status}")
                except Exception as e:
                    logger.warning(f"Failed to reach Cobalt instance {instance_url}: {e}")
                    last_error = e

        if last_error:
            raise last_error
        raise RuntimeError("All Cobalt API instances failed to process the request.")

    async def download_video(
        self,
        url: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Fetches stream link via Cobalt API and streams the file to local disk.
        Returns dictionary with file_path, title, duration, etc.
        """
        task_id = str(uuid.uuid4())[:8]
        info = await self.fetch_media_info(url)

        stream_url = info.get("url")
        if not stream_url:
            raise ValueError("Cobalt API did not return a valid download URL.")

        file_name = info.get("filename") or f"{task_id}_video.mp4"
        ext = Path(file_name).suffix or ".mp4"
        dest_path = self.download_dir / f"{task_id}_cobalt{ext}"

        logger.info(f"Downloading stream from Cobalt: {dest_path.name}")

        start_time = time.time()
        downloaded = 0
        total_size = 0

        async with aiohttp.ClientSession() as session:
            async with session.get(
                stream_url,
                headers={"User-Agent": "Mozilla/5.0 vsd-bot"},
                timeout=aiohttp.ClientTimeout(total=600)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to stream video file from Cobalt URL: HTTP {resp.status}")

                total_size = int(resp.headers.get("Content-Length", 0))

                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(256 * 1024):
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            elapsed = time.time() - start_time
                            speed_bps = (downloaded / elapsed) if elapsed > 0 else 0
                            speed_mbps = speed_bps / (1024 * 1024)
                            speed_str = f"{speed_mbps:.1f} MB/s"
                            percent = (downloaded / total_size) * 100.0
                            progress_callback(percent, speed_str)

        if not dest_path.exists() or dest_path.stat().st_size == 0:
            raise FileNotFoundError("Cobalt video file download resulted in an empty file.")

        logger.info(f"Cobalt download complete: {dest_path.name} ({downloaded / 1024 / 1024:.1f} MB)")

        return {
            "file_path": str(dest_path),
            "task_id": task_id,
            "original_filename": file_name
        }


cobalt_service = CobaltService()
