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
    path(
        "availability/windows/<uuid:window_id>/remove/", views.working_window_remove_view, name="working-window-remove"
    ),
    path("availability/blocked-periods/add/", views.blocked_period_create_view, name="blocked-period-create"),
    path(
        "availability/blocked-periods/<uuid:blocked_period_id>/remove/",
        views.blocked_period_remove_view,
        name="blocked-period-remove",
    ),
    path("earnings/", views.earnings_view, name="earnings"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/basic/", views.profile_edit_basic_view, name="profile-edit-basic"),
    path("profile/edit/professional/", views.profile_edit_professional_view, name="profile-edit-professional"),
    path("profile/avatar/", views.avatar_upload_view, name="profile-avatar-upload"),
    path("profile/avatar/remove/", views.avatar_remove_view, name="profile-avatar-remove"),
    path("profile/cover/", views.cover_upload_view, name="profile-cover-upload"),
    path("profile/cover/remove/", views.cover_remove_view, name="profile-cover-remove"),
    path("profile/skills/", views.profile_skills_view, name="profile-skills"),
    path("profile/skills/<uuid:skill_id>/remove/", views.profile_skill_remove_view, name="profile-skill-remove"),
    path("profile/experience/", views.profile_experience_view, name="profile-experience"),
    path("profile/experience/add/", views.profile_experience_add_view, name="profile-experience-add"),
    path(
        "profile/experience/<uuid:experience_id>/edit/",
        views.profile_experience_edit_view,
        name="profile-experience-edit",
    ),
    path(
        "profile/experience/<uuid:experience_id>/delete/",
        views.profile_experience_delete_view,
        name="profile-experience-delete",
    ),
    path("documents/<str:document_type>/", views.document_manage_view, name="document-manage"),
]
