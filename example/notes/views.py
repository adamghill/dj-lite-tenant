from catalog.models import Movie
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Note


@login_required
def note_list(request):
    notes = Note.objects.all()
    return render(request, "notes/note_list.html", {"notes": notes})


@login_required
def note_add(request):
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            Note.objects.create(text=text)
        return redirect("note_list")
    return render(request, "notes/note_add.html")


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        note.delete()
        return redirect("note_list")
    return render(request, "notes/note_confirm_delete.html", {"note": note})


@login_required
def movie_list(request):
    movies = Movie.objects.using("default").all()
    return render(request, "notes/movie_list.html", {"movies": movies})
