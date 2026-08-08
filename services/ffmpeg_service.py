import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import imageio_ffmpeg
from config.settings import settings
from utils.logger import logger


class FFmpegService:
    def __init__(self):
        self._ffmpeg_bin: Optional[str] = None
        self._ffprobe_bin: Optional[str] = None

    def get_ffmpeg_path(self) -> str:
        """Returns valid path to FFmpeg executable, with fallback to imageio-ffmpeg static binary."""
        if self._ffmpeg_bin and os.path.exists(self._ffmpeg_bin):
            return self._ffmpeg_bin

        # 1. Custom specified path in settings
        if settings.ffmpeg_path != "auto" and os.path.exists(settings.ffmpeg_path):
            self._ffmpeg_bin = settings.ffmpeg_path
            return self._ffmpeg_bin

        # 2. System PATH check
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            self._ffmpeg_bin = system_ffmpeg
            return self._ffmpeg_bin

        # 3. Fallback to imageio-ffmpeg static binary (ideal for Pterodactyl Panel environments!)
        try:
            static_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            if static_ffmpeg and os.path.exists(static_ffmpeg):
                logger.info(f"Using imageio-ffmpeg static binary at: {static_ffmpeg}")
                self._ffmpeg_bin = static_ffmpeg
                return self._ffmpeg_bin
        except Exception as e:
            logger.warning(f"Could not load imageio-ffmpeg binary: {e}")

        raise RuntimeError("FFmpeg executable not found on system! Please install FFmpeg or set FFMPEG_PATH.")

    def get_ffprobe_path(self) -> Optional[str]:
        """Locates ffprobe binary if available."""
        if self._ffprobe_bin and os.path.exists(self._ffprobe_bin):
            return self._ffprobe_bin

        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            self._ffprobe_bin = system_ffprobe
            return self._ffprobe_bin

        # Attempt adjacent to ffmpeg
        try:
            ffmpeg_path = Path(self.get_ffmpeg_path())
            adjacent_ffprobe = ffmpeg_path.parent / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
            if adjacent_ffprobe.exists():
                self._ffprobe_bin = str(adjacent_ffprobe)
                return self._ffprobe_bin
        except Exception:
            pass

        return None

    async def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Probes video file to get width, height, duration in seconds."""
        ffprobe_bin = self.get_ffprobe_path()
        metadata = {"width": None, "height": None, "duration": None}

        if ffprobe_bin:
            cmd = [
                ffprobe_bin,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration:format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                lines = [line.strip() for line in stdout.decode("utf-8").splitlines() if line.strip()]
                
                # Parse lines (width, height, stream duration, format duration)
                parsed_nums = []
                for line in lines:
                    try:
                        parsed_nums.append(float(line))
                    except ValueError:
                        pass
                
                if len(parsed_nums) >= 2:
                    metadata["width"] = int(parsed_nums[0])
                    metadata["height"] = int(parsed_nums[1])
                if len(parsed_nums) >= 3:
                    metadata["duration"] = int(parsed_nums[2])
            except Exception as e:
                logger.warning(f"ffprobe metadata extraction failed for {video_path}: {e}")

        # Fallback to ffmpeg -i if ffprobe failed or wasn't found
        if not metadata["duration"]:
            ffmpeg_bin = self.get_ffmpeg_path()
            cmd = [ffmpeg_bin, "-i", video_path]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await proc.communicate()
                err_text = stderr.decode("utf-8", errors="ignore")
                
                # Extract Duration: 00:01:23.45
                import re
                dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err_text)
                if dur_match:
                    hours, mins, secs = dur_match.groups()
                    metadata["duration"] = int(int(hours) * 3600 + int(mins) * 60 + float(secs))
                
                # Extract resolution e.g. 1920x1080
                res_match = re.search(r",\s*(\d{2,5})x(\d{2,5})", err_text)
                if res_match:
                    metadata["width"] = int(res_match.group(1))
                    metadata["height"] = int(res_match.group(2))
            except Exception as e:
                logger.warning(f"ffmpeg -i fallback failed for {video_path}: {e}")

        return metadata

    async def generate_thumbnail(self, video_path: str, output_thumb_path: str, timestamp_sec: float = 1.0) -> bool:
        """Extracts a high quality JPEG frame from the video for Telegram preview."""
        ffmpeg_bin = self.get_ffmpeg_path()
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(timestamp_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_thumb_path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if os.path.exists(output_thumb_path) and os.path.getsize(output_thumb_path) > 0:
                return True
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")
        return False

    async def faststart_remux(self, input_path: str, output_path: str) -> bool:
        """Remuxes MP4 container with +faststart flag for instantaneous Telegram streaming playback."""
        ffmpeg_bin = self.get_ffmpeg_path()
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", input_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception as e:
            logger.warning(f"Faststart remuxing failed: {e}")
        return False


ffmpeg_service = FFmpegService()
