from django import forms

class UrlForm(forms.Form):
    youtube_url = forms.URLField(
        label="YouTube Video URL",
        widget=forms.URLInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
    )
