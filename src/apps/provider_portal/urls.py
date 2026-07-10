"""/provider/ routing — Epic 02 (Marketplace Operational Experience).
Does not conflict with /portal/, /admin-portal/, /organization/, or /api/v1/."""

from django.urls import path

from . import views

app_name = "provider_portal"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("assignments/", views.assignments_list_view, name="assignments"),
    path("assignments/<uuid:order_id>/", views.assignment_detail_view, name="assignment-detail"),
    path("assignments/<uuid:order_id>/confirm/", views.assignment_confirm_view, name="assignment-confirm"),
    path("assignments/<uuid:order_id>/decline/", views.assignment_decline_view, name="assignment-decline"),
    path("assignments/<uuid:order_id>/start/", views.visit_start_view, name="visit-start"),
    path("assignments/<uuid:order_id>/complete/", views.visit_complete_view, name="visit-complete"),
    path("availability/", views.availability_view, name="availability"),
    path("availability/windows/<uuid:window_id>/remove/", views.working_window_remove_view, name="working-window-remove"),
    path("availability/blocked-periods/add/", views.blocked_period_create_view, name="blocked-period-create"),
    path("availability/blocked-periods/<uuid:blocked_period_id>/remove/", views.blocked_period_remove_view, name="blocked-period-remove"),
    path("earnings/", views.earnings_view, name="earnings"),
    path("notifications/", views.notifications_view, name="notifications"),
]
