from django.shortcuts import render
from .forms import UrlForm
from .utils import fetch_transcript, _extract_video_id

def home(request):
    transcript = video_id = None
    if request.method == "POST":
        form = UrlForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data["youtube_url"]
            video_id = _extract_video_id(url)          # keep this
            transcript = fetch_transcript(url)
    else:
        form = UrlForm()
    return render(
        request,
        "analyzer/home.html",
        {"form": form, "transcript": transcript, "video_id": video_id},
    )