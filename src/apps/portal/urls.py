"""/portal/ routing — Customer Experience Phase 1. Does not conflict with
/admin-portal/, /accounts/, or /api/v1/."""

from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("care-recipients/", views.care_recipients_list_view, name="care-recipients"),
    path("care-recipients/new/", views.care_recipient_create_view, name="care-recipient-create"),
    path("care-recipients/<uuid:care_recipient_id>/edit/", views.care_recipient_edit_view, name="care-recipient-edit"),
    path("care-recipients/<uuid:care_recipient_id>/archive/", views.care_recipient_archive_view, name="care-recipient-archive"),
    path("requests/", views.requests_list_view, name="requests"),
    path("requests/<uuid:order_id>/", views.request_detail_view, name="request-detail"),
    path("requests/<uuid:order_id>/share/", views.share_link_create_view, name="share-link-create"),
    path("requests/<uuid:order_id>/share/<uuid:link_id>/revoke/", views.share_link_revoke_view, name="share-link-revoke"),
    path("requests/new/care-recipient/", views.wizard_care_recipient_view, name="request-wizard-care-recipient"),
    path("requests/new/service/", views.wizard_service_view, name="request-wizard-service"),
    path("requests/new/schedule/", views.wizard_schedule_view, name="request-wizard-schedule"),
    path("requests/new/address/", views.wizard_address_view, name="request-wizard-address"),
    path("requests/new/notes/", views.wizard_notes_view, name="request-wizard-notes"),
    path("requests/new/review/", views.wizard_review_view, name="request-wizard-review"),
    path("requests/new/submit/", views.wizard_submit_view, name="request-wizard-submit"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("share/<str:token>/", views.shared_order_view, name="shared-order"),
]
