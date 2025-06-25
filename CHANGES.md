### Core workflow for adding something new in Django

1. **Plan the page / component**

   * Decide what data it needs (if any) and whether that logic belongs in an existing view or a new one.

2. **Create or update a view** (`views.py`)

   ```python
   from django.shortcuts import render

   def about(request):
       context = {"team": ["Alice", "Bob", "Carol"]}
       return render(request, "analyzer/about.html", context)
   ```

3. **Map the view to a URL**
   *App-level* (`analyzer/urls.py`)

   ```python
   from django.urls import path
   from . import views

   urlpatterns = [
       path("", views.home,  name="home"),
       path("about/", views.about, name="about"),   # new line
   ]
   ```

   *Project-level* (`project/urls.py`) already includes the app, so nothing else to touch.

4. **Design the HTML template** (`templates/analyzer/about.html`)

   ```django
   {% extends "analyzer/base.html" %}
   {% block title %}About · Transcript App{% endblock %}
   {% block content %}
   <h2 class="brand-gradient mb-3">Who we are</h2>

   <div class="row row-cols-1 row-cols-md-3 g-4">
     {% for name in team %}
       <div class="col">
         <div class="card card-dark p-3 text-center">
           <img src="{% static 'img/avatar.svg' %}" class="mb-2" width="72" alt="Avatar">
           <h5>{{ name }}</h5>
         </div>
       </div>
     {% endfor %}
   </div>
   {% endblock %}
   ```

5. **Hook it into navigation (optional)**
   Add a link in `base.html` or wherever your nav lives:

   ```html
   <a href="{% url 'about' %}" class="nav-link">About</a>
   ```

6. **Static assets (images, JS, CSS)**

   * Put files under **`analyzer/static/analyzer/…`**
   * Load them in templates:

     ```django
     {% load static %}
     <link rel="stylesheet" href="{% static 'analyzer/css/custom.css' %}">
     ```

7. **Restart dev server if running into import errors**
   `CTRL-C` → `python manage.py runserver` (template changes auto-reload; code changes sometimes need a restart).

---

### Quick cheat-sheet

| Task                                 | Where                                                                                              | Minimal code                                     |
| ------------------------------------ | -------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| New page                             | `views.py` + `urls.py` + new template                                                              | See steps 2–4                                    |
| Add a button inside an existing page | Edit that template (`home.html`, etc.)                                                             | `<button class="btn btn-primary">Click</button>` |
| Include JS for a specific page       | Place `<script …>` at the end of that template or reference a static file                          |                                                  |
| Re-use layout                        | Keep everything inside `{% block content %}` so the navbar/brand from `base.html` stays consistent |                                                  |

---

### Pro tips while scaling

* **Group UI**: keep reusable snippets in **`templates/analyzer/partials/`** and include them with `{% include %}`.
* **URLs**: namespace long apps (`app_name = "analyzer"` at top of `analyzer/urls.py`) then call `{% url 'analyzer:about' %}`.
* **CSS/JS**: prefer a single bundled file in production; in dev you can link multiple small ones for speed.

With that flow—view → URL → template—you can bolt on any new UI element or page in minutes.
