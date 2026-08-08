import os
from pathlib import Path
from typing import Union
from .logger import logger


def format_bytes(size: Union[int, float]) -> str:
    """Format bytes into human-readable string (e.g. 15.4 MB)."""
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def format_seconds(seconds: Union[int, float, None]) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds <= 0:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """Get size of a file in Megabytes."""
    try:
        path = Path(file_path)
        if path.exists():
            return path.stat().st_size / (1024 * 1024)
    except Exception as e:
        logger.warning(f"Error checking file size for {file_path}: {e}")
    return 0.0


def cleanup_file(file_path: Union[str, Path, None]) -> None:
    """Safely remove a temporary file if it exists."""
    if not file_path:
        return
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug(f"Cleaned up temp file: {path.name}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
