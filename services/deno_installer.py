"""
Auto-downloads a portable Deno binary for yt-dlp's JavaScript n-challenge solver.
Required because YouTube encrypts video stream URLs with a JS cipher that must be
executed by a real JS engine. Without this, yt-dlp can only see image thumbnails.
"""
import os
import platform
import shutil
import stat
import tarfile
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request

from utils.logger import logger

DENO_VERSION = "v2.1.4"
DENO_DIR = Path("./bin")
DENO_BINARY = "deno.exe" if platform.system() == "Windows" else "deno"


def _get_deno_url() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ("x86_64", "amd64"):
            return f"https://github.com/denoland/deno/releases/download/{DENO_VERSION}/deno-x86_64-unknown-linux-gnu.zip"
        elif machine in ("aarch64", "arm64"):
            return f"https://github.com/denoland/deno/releases/download/{DENO_VERSION}/deno-aarch64-unknown-linux-gnu.zip"
    elif system == "darwin":
        if machine in ("x86_64", "amd64"):
            return f"https://github.com/denoland/deno/releases/download/{DENO_VERSION}/deno-x86_64-apple-darwin.zip"
        elif machine in ("aarch64", "arm64"):
            return f"https://github.com/denoland/deno/releases/download/{DENO_VERSION}/deno-aarch64-apple-darwin.zip"
    elif system == "windows":
        return f"https://github.com/denoland/deno/releases/download/{DENO_VERSION}/deno-x86_64-pc-windows-msvc.zip"

    raise RuntimeError(f"Unsupported platform: {system} {machine}")


def get_deno_path() -> str:
    """Returns absolute path to a working deno binary.
    
    Priority:
    1. System PATH (deno already installed)
    2. Local ./bin/deno (previously downloaded)
    3. Auto-download from GitHub releases
    """
    # 1. Check system PATH
    system_deno = shutil.which("deno")
    if system_deno:
        logger.info(f"Deno found in system PATH: {system_deno}")
        return system_deno

    # 2. Check local binary
    local_deno = DENO_DIR / DENO_BINARY
    if local_deno.exists():
        logger.info(f"Deno found at: {local_deno.resolve()}")
        return str(local_deno.resolve())

    # 3. Auto-download
    logger.info("Deno not found. Downloading portable Deno binary for yt-dlp JS engine...")
    return _download_deno()


def _download_deno() -> str:
    """Downloads portable deno binary from GitHub releases."""
    url = _get_deno_url()
    DENO_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading Deno {DENO_VERSION} from: {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 vsd-bot"})

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with urlopen(req) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                tmp.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    if int(pct) % 25 == 0:
                        logger.info(f"  Deno download: {pct:.0f}% ({downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB)")

    # Extract
    target_bin = DENO_DIR / DENO_BINARY
    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            for member in zf.namelist():
                if member.endswith(DENO_BINARY) or member == DENO_BINARY:
                    with zf.open(member) as src, open(target_bin, "wb") as dst:
                        dst.write(src.read())
                    break
    finally:
        os.unlink(tmp_path)

    if not target_bin.exists():
        raise RuntimeError("Failed to extract Deno binary from archive.")

    # Make executable on Linux/macOS
    if platform.system() != "Windows":
        target_bin.chmod(target_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    resolved = str(target_bin.resolve())
    logger.info(f"Deno {DENO_VERSION} installed to: {resolved}")
    return resolved
