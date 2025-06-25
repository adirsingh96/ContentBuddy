import re, datetime
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
)

from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
)

def _extract_video_id(url: str) -> str | None:
    """
    Robustly pulls the 11-char video ID from any normal YouTube link.
    """
    url = url.strip()           # handles stray spaces / new-lines
    p = urlparse(url)

    #  youtu.be/VIDEO_ID
    if p.hostname in ("youtu.be", "www.youtu.be"):
        return p.path.lstrip("/")

    #  youtube.com/watch?v=VIDEO_ID
    if p.path == "/watch":
        return parse_qs(p.query).get("v", [None])[0]

    #  youtube.com/embed/VIDEO_ID
    if p.path.startswith("/embed/"):
        return p.path.split("/")[2]

    #  youtube.com/shorts/VIDEO_ID
    if p.path.startswith("/shorts/"):
        return p.path.split("/")[2]

    return None


def _sec_to_hhmmss(seconds: float) -> str:
    """0-pad to HH:MM:SS (YouTube style)."""
    return str(datetime.timedelta(seconds=int(seconds)))

def fetch_transcript(url: str, langs=None):
    preferred = ['hi', 'en'] if langs is None else langs
    vid = _extract_video_id(url)

    if not vid or len(vid) != 11:
        raise ValueError("Invalid YouTube URL")

    try:
        raw = YouTubeTranscriptApi.get_transcript(vid, languages=preferred)
        return [{"time": _sec_to_hhmmss(s["start"]), "text": s["text"]} for s in raw]

    except NoTranscriptFound:
        return [{"time": "", "text": "No transcript in requested languages."}]
    except TranscriptsDisabled:
        return [{"time": "", "text": "Transcripts are disabled for this video."}]