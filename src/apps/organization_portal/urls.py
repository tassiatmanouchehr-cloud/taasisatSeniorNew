"""/organization/ routing — Epic 02 (Marketplace Operational Experience).
Does not conflict with /portal/, /admin-portal/, /provider/, or /api/v1/."""

from django.urls import path

from . import views

app_name = "organization_portal"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("staff/", views.staff_list_view, name="staff"),
    path("staff/<uuid:membership_id>/approve/", views.staff_approve_view, name="staff-approve"),
    path("staff/<uuid:membership_id>/suspend/", views.staff_suspend_view, name="staff-suspend"),
    path("assignments/", views.assignment_center_view, name="assignment-center"),
    path("assignments/<uuid:order_id>/assign/", views.assign_staff_view, name="assign-staff"),
    path("capacity/", views.capacity_view, name="capacity"),
    path("reports/", views.reports_view, name="reports"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile-edit"),
    path("profile/edit/services/", views.profile_edit_services_view, name="profile-edit-services"),
    path("profile/logo/", views.logo_upload_view, name="profile-logo-upload"),
    path("profile/logo/remove/", views.logo_remove_view, name="profile-logo-remove"),
    path("profile/cover/", views.cover_upload_view, name="profile-cover-upload"),
    path("profile/cover/remove/", views.cover_remove_view, name="profile-cover-remove"),
    path("documents/<str:document_type>/", views.document_manage_view, name="document-manage"),
]
