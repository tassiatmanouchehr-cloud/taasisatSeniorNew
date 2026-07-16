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
    path("pricing/", views.pricing, name="pricing"),
    path("trust-safety/", views.trust_safety, name="trust-safety"),
    path("caregivers/", views.caregivers, name="caregivers"),
    path("find-a-caregiver/", views.find_a_caregiver, name="find-a-caregiver"),
    path("find-a-caregiver/<uuid:supplier_id>/", views.caregiver_profile, name="caregiver-profile"),
    path("organizations/", views.organizations, name="organizations"),
    path("find-an-organization/", views.find_an_organization, name="organization-directory"),
    path("find-an-organization/<uuid:supplier_id>/", views.organization_profile, name="organization-profile"),
    path("faq/", views.faq, name="faq"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("accessibility/", views.accessibility, name="accessibility"),
    path("support/", views.support, name="support"),
    path("service-areas/", views.service_areas, name="service-areas"),
]
