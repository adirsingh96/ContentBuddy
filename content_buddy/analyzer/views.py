from django.shortcuts import render
from .forms import UrlForm
from .utils import fetch_transcript, _extract_video_id,suggest_reels
from django.contrib import messages

def home(request):
    transcript = None
    reels      = []      # ← initialise before the if-block
    video_id   = None

    if request.method == "POST":
        form = UrlForm(request.POST)
        if form.is_valid():
            url       = form.cleaned_data["youtube_url"]
            video_id  = _extract_video_id(url)
            transcript = fetch_transcript(url)

            try:
                reels = suggest_reels(transcript)
            except Exception as e:
                messages.error(request, f"Reel generation failed: {e}")
    else:
        form = UrlForm()

    return render(
        request,
        "analyzer/home.html",
        {
            "form": form,
            "transcript": transcript,
            "reels": reels,          # always defined
            "video_id": video_id,
        },
    )