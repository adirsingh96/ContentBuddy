import re, datetime
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
)

from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
)

import os, openai, json, textwrap, datetime
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    
def _format_for_prompt(segments, limit=3000):
    """
    Turns [{time:'0:00:01',text:'hi'}...] into a compact string.
    Cuts off after ~limit characters to stay inside context.
    """
    lines = [f"{s['time']} {s['text']}" for s in segments]
    joined = "\n".join(lines)
    return joined[:limit]    

def suggest_reels(segments, model="o3"):
    """
    Ask the LLM for 5 reels (60-90 s) and return python objects:
    [{title,start,end}, …]
    """
    prompt = textwrap.dedent(f"""
        Below is a YouTube transcript (time + text per line).
        Pick FIVE highlight clips suitable for Instagram Reels (60-90 seconds each).
        Make Sure the language which you return is HINGLISH and keep the letters in ENGLISH only                     
        Return JSON list, each object = {{
          "title":  short catchy title,
          "start":  start timestamp HH:MM:SS,
          "end":    end timestamp HH:MM:SS
        }}.
        JSON only, no markdown.

        Transcript:
        { _format_for_prompt(segments) }
    """)

    rsp = openai.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":prompt}],
        #temperature=0.3
    )
    raw = rsp.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # fallback: empty list avoids template crash
        return []