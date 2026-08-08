"""
Manages the BgUtils Proof-of-Origin Token (POT) HTTP server.

This server generates PO tokens that yt-dlp uses to bypass YouTube's
"Sign in to confirm you're not a bot" challenge on datacenter IPs.

Architecture:
  1. Clones the bgutil-ytdlp-pot-provider repo (if not present)
  2. Installs Deno dependencies
  3. Launches the HTTP server on port 4416
  4. yt-dlp (via bgutil-ytdlp-pot-provider pip plugin) queries it automatically

Requires: Deno binary (auto-installed by deno_installer.py)
"""
import asyncio
import os
import subprocess
import shutil
from pathlib import Path

from utils.logger import logger
from services.deno_installer import get_deno_command

POT_SERVER_DIR = Path("./pot-server")
POT_REPO_URL = "https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git"
POT_REPO_TAG = "1.3.1"
POT_SERVER_PORT = 4416

_pot_process: asyncio.subprocess.Process | None = None


async def setup_pot_server() -> bool:
    """Clone and install the bgutil POT server if not already set up."""
    server_dir = POT_SERVER_DIR / "server"

    if server_dir.exists() and (server_dir / "deno.lock").exists():
        logger.info("POT server source already present.")
        return True

    # Resolve deno command (handles ld-linux fallback on Pterodactyl)
    try:
        deno_cmd = get_deno_command()
    except Exception as e:
        logger.error(f"Cannot set up POT server without Deno: {e}")
        return False

    # Clone repo
    if not POT_SERVER_DIR.exists():
        logger.info(f"Cloning bgutil POT provider (tag {POT_REPO_TAG})...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", "--single-branch", "--branch", POT_REPO_TAG,
                "--depth", "1", POT_REPO_URL, str(POT_SERVER_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(f"Failed to clone POT server repo: {stderr.decode()}")
                return False
            logger.info("POT server repo cloned successfully.")
        except FileNotFoundError:
            logger.error("git is not available. Cannot clone POT server repo.")
            return False

    # Install Deno deps
    logger.info("Installing POT server Deno dependencies...")
    try:
        proc = await asyncio.create_subprocess_exec(
            *deno_cmd, "install", "--allow-scripts=npm:canvas", "--frozen",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(server_dir)
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning(f"Deno install had issues: {stderr.decode()}")
            # Non-fatal — may still work
        else:
            logger.info("POT server Deno dependencies installed.")
        return True
    except Exception as e:
        logger.error(f"Failed to install POT server deps: {e}")
        return False


async def start_pot_server() -> bool:
    """Start the POT HTTP server as a background daemon on port 4416."""
    global _pot_process

    if _pot_process and _pot_process.returncode is None:
        logger.info(f"POT server already running (PID: {_pot_process.pid})")
        return True

    server_dir = POT_SERVER_DIR / "server"

    if not server_dir.exists():
        logger.error("POT server source not found. Run setup_pot_server() first.")
        return False

    try:
        deno_cmd = get_deno_command()
    except Exception as e:
        logger.error(f"Cannot start POT server without Deno command: {e}")
        return False

    main_ts = server_dir / "src" / "main.ts"

    if not main_ts.exists():
        logger.error(f"POT server entry point not found: {main_ts}")
        return False

    logger.info(f"Starting POT server on port {POT_SERVER_PORT}...")

    try:
        env = os.environ.copy()
        env["PORT"] = str(POT_SERVER_PORT)

        _pot_process = await asyncio.create_subprocess_exec(
            *deno_cmd, "run", "-A", str(main_ts),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(server_dir),
            env=env
        )

        # Give it a moment to start up
        await asyncio.sleep(2)

        if _pot_process.returncode is not None:
            _, stderr = await _pot_process.communicate()
            logger.error(f"POT server failed to start: {stderr.decode()}")
            return False

        logger.info(f"POT server started successfully (PID: {_pot_process.pid}) on port {POT_SERVER_PORT}")
        return True

    except Exception as e:
        logger.error(f"Failed to start POT server: {e}")
        return False


async def stop_pot_server():
    """Gracefully stop the POT server."""
    global _pot_process

    if _pot_process and _pot_process.returncode is None:
        logger.info("Stopping POT server...")
        _pot_process.terminate()
        try:
            await asyncio.wait_for(_pot_process.wait(), timeout=5)
        except asyncio.TimeoutError:
            _pot_process.kill()
        _pot_process = None
        logger.info("POT server stopped.")


async def ensure_pot_server_running() -> bool:
    """Full lifecycle: setup + start the POT server. Returns True if running."""
    setup_ok = await setup_pot_server()
    if not setup_ok:
        return False
    return await start_pot_server()
