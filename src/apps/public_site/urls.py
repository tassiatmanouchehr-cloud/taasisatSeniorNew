"""URL configuration for public website pages."""

from django.urls import path

from . import views

app_name = "public_site"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.services, name="services"),
    path("how-it-works/", views.how_it_works, name="how-it-works"),
    path("contact/", views.contact, name="contact"),
]
