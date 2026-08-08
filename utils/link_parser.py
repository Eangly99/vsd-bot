import re
from typing import List

# Comprehensive URL extraction pattern
URL_REGEX = re.compile(
    r"https?://(?:www\.|m\.|mobile\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
)

# Common video domain pattern matcher
KNOWN_VIDEO_DOMAINS = [
    "youtube.com", "youtu.be",
    "tiktok.com",
    "instagram.com", "instagr.am",
    "twitter.com", "x.com",
    "reddit.com", "redd.it",
    "facebook.com", "fb.watch", "fb.gg",
    "pinterest.com", "pin.it",
    "twitch.tv",
    "vimeo.com",
    "dailymotion.com",
    "bilibili.com",
    "vk.com",
    "douyin.com",
    "likee.video",
    "rumble.com"
]


def extract_urls(text: str) -> List[str]:
    """Extract all valid HTTP/HTTPS URLs from a given text string."""
    if not text:
        return []
    return URL_REGEX.findall(text)


def is_supported_url(url: str) -> bool:
    """
    Checks if a URL is likely supported.
    yt-dlp supports 1000+ sites, so we check general HTTP validity
    and highlight known video domains for faster matching.
    """
    if not url.startswith(("http://", "https://")):
        return False
    
    url_lower = url.lower()
    return any(domain in url_lower for domain in KNOWN_VIDEO_DOMAINS) or bool(URL_REGEX.match(url))
