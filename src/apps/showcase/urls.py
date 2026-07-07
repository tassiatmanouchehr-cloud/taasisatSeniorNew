"""URL configuration for the UI Component Showcase."""

from django.urls import path

from . import views

app_name = "showcase"

urlpatterns = [
    path("", views.index, name="index"),
    path("buttons/", views.buttons, name="buttons"),
    path("forms/", views.forms, name="forms"),
    path("cards/", views.cards, name="cards"),
    path("tables/", views.tables, name="tables"),
    path("modals/", views.modals, name="modals"),
    path("alerts/", views.alerts, name="alerts"),
    path("badges/", views.badges, name="badges"),
    path("dropdowns/", views.dropdowns, name="dropdowns"),
    path("navigation/", views.navigation, name="navigation"),
    path("loading/", views.loading, name="loading"),
    path("avatars/", views.avatars, name="avatars"),
    path("icons/", views.icons, name="icons"),
    path("empty-states/", views.empty_states, name="empty-states"),
    path("upload/", views.upload, name="upload"),
]
