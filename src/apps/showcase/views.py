"""
UI Component Showcase views.

Each view renders a showcase page for a component category.
No business logic — only design system demonstration.
"""

from django.shortcuts import render


def index(request):
    """Showcase index — links to all component demos."""
    sections = [
        {"name": "دکمه‌ها", "slug": "buttons", "icon": "cursor-arrow-rays", "count": 6},
        {"name": "فرم‌ها", "slug": "forms", "icon": "pencil-square", "count": 7},
        {"name": "کارت‌ها", "slug": "cards", "icon": "rectangle-stack", "count": 4},
        {"name": "جداول", "slug": "tables", "icon": "table-cells", "count": 3},
        {"name": "مودال‌ها", "slug": "modals", "icon": "window", "count": 5},
        {"name": "هشدارها", "slug": "alerts", "icon": "bell-alert", "count": 4},
        {"name": "نشان‌ها", "slug": "badges", "icon": "tag", "count": 7},
        {"name": "منوها", "slug": "dropdowns", "icon": "chevron-down", "count": 3},
        {"name": "ناوبری", "slug": "navigation", "icon": "bars-3", "count": 4},
        {"name": "بارگذاری", "slug": "loading", "icon": "arrow-path", "count": 8},
        {"name": "آواتار", "slug": "avatars", "icon": "user-circle", "count": 5},
        {"name": "آیکون‌ها", "slug": "icons", "icon": "squares-2x2", "count": 24},
        {"name": "حالات خالی", "slug": "empty-states", "icon": "inbox", "count": 8},
        {"name": "آپلود فایل", "slug": "upload", "icon": "cloud-arrow-up", "count": 4},
    ]
    return render(request, "showcase/index.html", {"sections": sections})


def buttons(request):
    """Button component showcase."""
    return render(request, "showcase/buttons.html")


def forms(request):
    """Form components showcase."""
    return render(request, "showcase/forms.html")


def cards(request):
    """Card component showcase."""
    return render(request, "showcase/cards.html")


def tables(request):
    """Table component showcase."""
    return render(request, "showcase/tables.html")


def modals(request):
    """Modal/overlay component showcase."""
    return render(request, "showcase/modals.html")


def alerts(request):
    """Alert/feedback component showcase."""
    return render(request, "showcase/alerts.html")


def badges(request):
    """Badge/chip component showcase."""
    return render(request, "showcase/badges.html")


def dropdowns(request):
    """Dropdown/menu component showcase."""
    return render(request, "showcase/dropdowns.html")


def navigation(request):
    """Navigation component showcase."""
    return render(request, "showcase/navigation.html")


def loading(request):
    """Loading/skeleton component showcase."""
    return render(request, "showcase/loading.html")


def avatars(request):
    """Avatar component showcase."""
    return render(request, "showcase/avatars.html")


def icons(request):
    """Icon system showcase."""
    return render(request, "showcase/icons.html")


def empty_states(request):
    """Empty state component showcase."""
    return render(request, "showcase/empty_states.html")


def upload(request):
    """File upload component showcase."""
    return render(request, "showcase/upload.html")
