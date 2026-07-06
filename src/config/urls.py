"""URL configuration for the Enterprise Service Marketplace Platform."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
