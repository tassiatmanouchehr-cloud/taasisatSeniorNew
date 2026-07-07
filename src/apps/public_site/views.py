"""Public marketing website views.

These pages are server-rendered, Persian-first, RTL, and contain no business logic.
They only consume the Enterprise UI Foundation and public templates.
"""

from django.shortcuts import render


def home(request):
    return render(request, "public_site/home.html")


def about(request):
    return render(request, "public_site/about.html")


def services(request):
    return render(request, "public_site/services.html")


def how_it_works(request):
    return render(request, "public_site/how_it_works.html")


def contact(request):
    return render(request, "public_site/contact.html")
