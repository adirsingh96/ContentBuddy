import re, datetime
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
)

from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
)

import os, openai, json, textwrap, datetime,tiktoken,math
openai.api_key = os.getenv("OPENAI_API_KEY")
enc = tiktoken.encoding_for_model("o3")   # accurate token counter


def _tokens(text: str) -> int:
    return len(enc.encode(text))

def _normalise(obj):
    # map alternate field names → canonical names
    if "clip_start" in obj:
        obj["start"] = obj.pop("clip_start")
    if "clip_end" in obj:
        obj["end"] = obj.pop("clip_end")
    return obj

def _hms_to_sec(hms: str) -> int:
    """Accepts SS, MM:SS, or HH:MM:SS → seconds."""
    parts = list(map(int, hms.strip().split(":")))
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, (m, s) = 0, parts
    elif len(parts) == 1:
        h, m, s = 0, 0, parts[0]
    else:                    # unexpected format
        return 0
    return h * 3600 + m * 60 + s


def _sec_to_hms(s):
    return str(datetime.timedelta(seconds=s))

def _to_prompt(chunk):
    lines = [f"{s['time']} {s['text']}" for s in chunk]
    return "\n".join(lines)

def _ask_o3(prompt):
    rsp = openai.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": prompt}]
    )
    return rsp.choices[0].message.content.strip()

def _chunk_segments(segments, max_tokens=8000, overlap_seconds=15):
    """
    Yield lists of segments whose combined tokens ≦ max_tokens.
    Logs start/end time and token count for every chunk.
    """
    chunk, tokens = [], 0
    for seg in segments:
        line = f"{seg['time']} {seg['text']}\n"
        t = _tokens(line)

        # will adding this line overflow?
        if tokens + t > max_tokens and chunk:
            first, last = chunk[0]["time"], chunk[-1]["time"]
            print(f"Chunk #{_chunk_segments.idx}: {first} → {last}  "
                  f"({tokens} tokens)")
            _chunk_segments.idx += 1
            yield chunk

            # overlap handling
            tail = [s for s in reversed(chunk)
                    if _hms_to_sec(seg["time"]) - _hms_to_sec(s["time"]) < overlap_seconds]
            chunk, tokens = list(reversed(tail)), sum(_tokens(f"{x['time']} {x['text']}\n") for x in tail)

        chunk.append(seg)
        tokens += t

    if chunk:
        first, last = chunk[0]["time"], chunk[-1]["time"]
        print(f"Chunk #{_chunk_segments.idx}: {first} → {last}  "
              f"({tokens} tokens)")
        _chunk_segments.idx += 1
        yield chunk
# initialise a static counter
_chunk_segments.idx = 1

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
    
def _format_for_prompt(segments, limit=30000):
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
        Pick  highlight 10 clips suitable for Instagram Reels whuch can go viral (60-90 seconds each).
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


def suggest_reels_full(transcript, desired=5):
    print("\n=== Chunking transcript for reel suggestions ===")
    print(f"Transcript length: {len(transcript)} segments "
          f"({_tokens(_to_prompt(transcript))} tokens total)\n")

    all_candidates = []

    # ---------- 1. collect candidates from every chunk ----------
    for chunk in _chunk_segments(transcript):
        chunk_prompt = textwrap.dedent(f"""
            Below is a slice of a YouTube transcript.
            Suggest **UP TO 4** Instagram Reels (60-90 s).
            Return JSON with: {{ "title", "start", "end" }} only.
            No markdown.

            Transcript slice:
            {_to_prompt(chunk)}
        """)
        try:
            part = json.loads(_ask_o3(chunk_prompt))
            all_candidates.extend([_normalise(p) for p in part]) 
            #print("Chunk returned:", part)

            #all_candidates.extend(part)
        except Exception as e:
            print("⚠️  JSON parse failed for one chunk:", e)
            continue

    print(f"\nTotal candidate reels before dedupe: {len(all_candidates)}")

    # ---------- 2. de-duplicate and sort ----------
    seen   = set()
    unique = []
    for c in all_candidates:
        if not all(k in c for k in ("start", "end", "title")):
            print("⚠️  Skipping incomplete object:", c)
            continue
        key = (c["start"], c["end"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    # sort chronologically
    #unique.sort(key=lambda c: _hms_to_sec(c["start"]))
    unique.sort(key=lambda c: _hms_to_sec(c.get("start", "0")))


    print(f"Unique reels after dedupe: {len(unique)} (keeping first {desired})")

    # ---------- 3. return the best N ----------
    return unique

