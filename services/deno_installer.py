"""
Auto-downloads a portable Deno binary for yt-dlp's JavaScript n-challenge solver.
Required because YouTube encrypts video stream URLs with a JS cipher that must be
executed by a real JS engine. Without this, yt-dlp can only see image thumbnails.

On Pterodactyl containers where the daemon strips execute permissions,
we use the Linux dynamic linker (ld-linux) to invoke the binary without +x.
"""
import os
import platform
import shutil
import stat
import subprocess
import zipfile
import tempfile
from pathlib import Path
from typing import List
from urllib.request import urlopen, Request

from utils.logger import logger

DENO_VERSION = "v2.1.4"
DENO_DIR = Path("./bin")
DENO_BINARY = "deno.exe" if platform.system() == "Windows" else "deno"

# Cache: resolved command prefix for executing deno
_deno_cmd: List[str] | None = None


def _find_ld_linux() -> str | None:
    """Find the Linux dynamic linker for executing binaries without +x."""
    candidates = [
        "/lib64/ld-linux-x86-64.so.2",
        "/lib/ld-linux-x86-64.so.2",
        "/lib/ld-linux-aarch64.so.1",
        "/lib64/ld-linux-aarch64.so.1",
    ]
    for ld in candidates:
        if os.path.exists(ld):
            return ld
    return None


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


def _try_make_executable(path: Path) -> bool:
    """Try to set execute permission. Returns True if successful."""
    if platform.system() == "Windows":
        return True
    try:
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except PermissionError:
        return False


def _can_execute(deno_path: str) -> bool:
    """Test if we can actually execute the deno binary directly."""
    try:
        result = subprocess.run(
            [deno_path, "--version"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (PermissionError, OSError):
        return False


def _can_execute_via_ld(ld_path: str, deno_path: str) -> bool:
    """Test if we can execute deno through the dynamic linker."""
    try:
        result = subprocess.run(
            [ld_path, deno_path, "--version"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (PermissionError, OSError):
        return False


def get_deno_command() -> List[str]:
    """Returns the command prefix to execute deno.

    On normal systems: ["/path/to/deno"]
    On Pterodactyl (no +x): ["/lib64/ld-linux-x86-64.so.2", "/path/to/deno"]

    This is the function all other services should use to run deno.
    """
    global _deno_cmd

    if _deno_cmd is not None:
        return _deno_cmd

    deno_path = get_deno_path()

    # Try direct execution first
    if _can_execute(deno_path):
        _deno_cmd = [deno_path]
        logger.info(f"Deno executable directly: {deno_path}")
        return _deno_cmd

    # Fallback: use Linux dynamic linker (bypasses missing execute permission)
    ld_path = _find_ld_linux()
    if ld_path and _can_execute_via_ld(ld_path, deno_path):
        _deno_cmd = [ld_path, deno_path]
        logger.info(f"Deno executable via dynamic linker: {ld_path} {deno_path}")
        return _deno_cmd

    raise RuntimeError(
        f"Cannot execute Deno binary at {deno_path}. "
        "Neither direct execution nor ld-linux fallback worked."
    )


def get_deno_path() -> str:
    """Returns absolute path to the deno binary file.

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
        _try_make_executable(local_deno)
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

    _try_make_executable(target_bin)

    resolved = str(target_bin.resolve())
    logger.info(f"Deno {DENO_VERSION} installed to: {resolved}")
    return resolved
