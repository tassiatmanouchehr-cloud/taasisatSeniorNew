"""Phase 2 (Caregiver Professional Profile) end-to-end acceptance —
Sprint 2.6 (Public Profile Finalization and Phase 2 Acceptance).

Cross-app integration coverage proving the whole caregiver-profile slice
works together as one coherent capability: activation, editable owner
data, per-item visibility, verified credentials, availability, the public
profile page, directory/search discovery, dashboard isolation, private
data never leaking publicly, and bounded query behavior. Deliberately does
not re-prove every lower-level unit test already covered in
apps.accounts/apps.availability/apps.provider_portal/apps.public_site's
own Sprint 2.1-2.5 suites — those remain the source of truth for each
slice's own internal correctness. This file proves the slices compose."""

import datetime
import io
import uuid
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models.media import DocumentType
from apps.accounts.models.profiles import CaregiverProfile, CustomerProfile, ProfileStatus
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE
from apps.accounts.services.caregiver_gallery_service import CaregiverGalleryService
from apps.accounts.services.caregiver_professional_profile_service import (
    CaregiverExperienceService,
    CaregiverSkillService,
)
from apps.accounts.services.caregiver_profile_service import CaregiverProfileUpdateService
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.profile_activation_service import ProfileActivationService
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.availability.models import DayOfWeek
from apps.availability.services.mutation_service import AvailabilityMutationService
from apps.kernel.models import Person, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions
from apps.orders.models import CatalogStatus, ServiceCategory

from ..services.directory_service import CaregiverDirectoryService
from ..services.home_service import HomePageService
from ..services.profile_service import CaregiverPublicProfileService
from .helpers import PublicSiteTestCase

PDF_BYTES = b"%PDF-1.4 fake test content"


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _image_file(name="photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _png_bytes(), content_type="image/png")


class Phase2FullLifecycleAcceptanceTest(PublicSiteTestCase):
    """Points 1-11 and 15 of the Sprint 2.6 governance's 15-point
    acceptance list, exercised as one continuous caregiver lifecycle:
    DRAFT -> activated, bio edited, skills/experience managed with mixed
    visibility, gallery managed with mixed visibility, weekly availability
    set, a credential approved and a second left pending, then verified
    from the public profile page, the directory, and search."""

    def _make_reviewer(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230099", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW, ACCOUNTS_PROFILE_ACTIVATE])
        return reviewer

    def test_full_caregiver_lifecycle_composes_correctly_on_every_public_surface(self):
        reviewer = self._make_reviewer()

        # 1) Start as an unpublished DRAFT profile — invisible everywhere.
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="مراقب چرخه کامل")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        caregiver = CaregiverProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name="مراقب چرخه کامل",
            city="tehran",
            specialty="مراقبت سالمند",
            status=ProfileStatus.DRAFT,
        )
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver

        supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=self.tenant.id)
        supplier.service_categories = [str(self.category.id)]
        supplier.save(update_fields=["service_categories"])

        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))
        directory_before = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertNotIn("مراقب چرخه کامل", {c.display_name for c in directory_before.caregivers})

        # 2) Edit bio/specialty (owner-only mutation boundary: only this caregiver's own row changes).
        CaregiverProfileUpdateService.update_professional_info(
            caregiver,
            bio="سال‌ها تجربه در مراقبت از سالمندان.",
            specialty="مراقبت تخصصی سالمند",
            years_experience=6,
            service_radius_km=15,
        )

        # 3) Skills — one visible, one hidden.
        CaregiverSkillService.add_skill(caregiver, name="مراقبت پس از جراحی")
        hidden_skill = CaregiverSkillService.add_skill(caregiver, name="مهارت پنهان")
        CaregiverSkillService.toggle_visibility(caregiver, skill_id=hidden_skill.id)

        # 4) Experience — one visible, one hidden.
        CaregiverExperienceService.create(
            caregiver,
            title="پرستار خانگی",
            organization_name="کلینیک نمونه",
            start_date=datetime.date(2020, 1, 1),
            end_date=None,
            is_current=True,
            description="مراقبت روزانه از سالمندان.",
            is_visible=True,
        )
        hidden_experience = CaregiverExperienceService.create(
            caregiver,
            title="سابقه پنهان",
            organization_name="",
            start_date=datetime.date(2018, 1, 1),
            end_date=datetime.date(2019, 1, 1),
            is_current=False,
            description="",
            is_visible=True,
        )
        CaregiverExperienceService.update(
            caregiver,
            experience_id=hidden_experience.id,
            title="سابقه پنهان",
            start_date=datetime.date(2018, 1, 1),
            end_date=datetime.date(2019, 1, 1),
            is_current=False,
            is_visible=False,
        )

        # 5) Gallery — one visible, one hidden.
        CaregiverGalleryService.add_item(caregiver, image=_image_file(), caption="نمونه کار")
        hidden_item = CaregiverGalleryService.add_item(caregiver, image=_image_file("hidden.png"))
        CaregiverGalleryService.update_item(caregiver, item_id=hidden_item.id, is_visible=False)

        # 6) Weekly availability — a working window on Monday.
        AvailabilityMutationService.add_working_window(
            supplier=supplier,
            day_of_week=DayOfWeek.MONDAY,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
        )

        # 7) Both required documents (IDENTITY, BACKGROUND_CHECK) approved — required for
        # activation itself, and each contributes a public credential summary once approved.
        identity_doc = DocumentService.upload_caregiver_document(
            caregiver,
            document_type=DocumentType.IDENTITY,
            file=SimpleUploadedFile("identity.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        VerificationReviewService.approve(document_id=identity_doc.id, tenant_id=self.tenant.id, reviewer=reviewer)
        background_doc = DocumentService.upload_caregiver_document(
            caregiver,
            document_type=DocumentType.BACKGROUND_CHECK,
            file=SimpleUploadedFile("bg.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        VerificationReviewService.approve(document_id=background_doc.id, tenant_id=self.tenant.id, reviewer=reviewer)

        # 8) A third, non-required credential (QUALIFICATION) left pending — never public.
        pending_doc = DocumentService.upload_caregiver_document(
            caregiver,
            document_type=DocumentType.QUALIFICATION,
            file=SimpleUploadedFile("qualification.pdf", PDF_BYTES, content_type="application/pdf"),
        )

        # Not yet activated: still hidden everywhere despite all the data above.
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

        # Activate — the only transition that makes it publicly discoverable.
        result = ProfileActivationService.activate_caregiver(caregiver.id, tenant_id=self.tenant.id, actor=reviewer)
        self.assertEqual(result.status, ProfileStatus.ACTIVE)

        # 9) A public customer can now view the profile.
        cust_person = Person.objects.create(tenant=self.tenant, full_name="مشتری")
        cust_user = UserAccount.objects.create_user(phone="09121110099", person=cust_person, tenant=self.tenant)
        CustomerProfile.objects.create(user=cust_user, person=cust_person, phone="09121110099", display_name="مشتری")
        self.client.force_login(cust_user)

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]),
            {"tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn("مراقب چرخه کامل", content)
        self.assertIn("سال‌ها تجربه در مراقبت از سالمندان.", content)
        self.assertIn("مراقبت پس از جراحی", content)
        self.assertNotIn("مهارت پنهان", content)
        self.assertIn("پرستار خانگی", content)
        self.assertNotIn("سابقه پنهان", content)
        self.assertIn("نمونه کار", content)
        self.assertIn("احراز هویت", content)  # IDENTITY credential label (approved)
        self.assertIn("بررسی سوءپیشینه", content)  # BACKGROUND_CHECK credential label (approved)
        self.assertNotIn("مدرک تخصصی", content)  # QUALIFICATION credential label (still pending)
        self.assertIn("دوشنبه", content)  # Monday availability summary

        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(len(profile.gallery), 1)
        self.assertEqual(len(profile.skills), 1)
        self.assertEqual(len(profile.experience), 1)
        self.assertEqual(len(profile.credentials), 2)
        self.assertTrue(profile.schedule_summary.has_schedule)
        self.assertEqual(profile.schedule_summary.available_day_labels, ("دوشنبه",))

        # 12) No exact working hours, no time-off/blocked-period data, no pending-document
        # evidence, no reviewer identity, no document file path or number anywhere in the response.
        self.assertNotIn("09:00", content)
        self.assertNotIn("17:00", content)
        self.assertNotIn(pending_doc.file.name if pending_doc.file else "__no_file__", content)
        self.assertNotIn("qualification.pdf", content)
        self.assertNotIn(str(identity_doc.id), content)
        self.assertNotIn(reviewer.person.full_name, content)
        self.assertNotIn(caregiver.phone, content)

        # 10) Directory and search now find this caregiver.
        directory_after = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertIn("مراقب چرخه کامل", {c.display_name for c in directory_after.caregivers})
        search_page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, text="چرخه کامل")
        self.assertEqual(search_page.pagination.total_count, 1)

        home = HomePageService.get_home_view(tenant_id=self.tenant.id)
        self.assertIn("مراقب چرخه کامل", {c.display_name for c in home.featured_caregivers})

        # 11) A second, ineligible (unverified) caregiver appears nowhere publicly.
        hidden_supplier, _ = self._create_caregiver_supplier(
            display_name="مراقب پنهان",
            verification_status="unverified",
        )
        self.assertIsNone(CaregiverPublicProfileService.get_profile(hidden_supplier.id, tenant_id=self.tenant.id))
        self.assertNotIn(
            "مراقب پنهان",
            {c.display_name for c in CaregiverDirectoryService.search(tenant_id=self.tenant.id).caregivers},
        )
        self.assertNotIn(
            "مراقب پنهان",
            {c.display_name for c in HomePageService.get_home_view(tenant_id=self.tenant.id).featured_caregivers},
        )
        hidden_response = self.client.get(
            reverse("public_site:caregiver-profile", args=[hidden_supplier.id]),
            {"tenant": self.tenant.slug},
        )
        self.assertEqual(hidden_response.status_code, 404)

        # 15) Theme-independent template: renders cleanly (no server error) regardless
        # of populated/empty sections — already proven by the 200 above; confirm the
        # directory and home pages also render with this same populated data present.
        directory_response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})
        self.assertEqual(directory_response.status_code, 200)
        home_response = self.client.get(reverse("public_site:home"), {"tenant": self.tenant.slug})
        self.assertEqual(home_response.status_code, 200)


class Phase2DashboardIsolationAcceptanceTest(PublicSiteTestCase):
    """Point 13: the caregiver dashboard shows only the signed-in
    caregiver's own summaries, never another supplier's — proven across
    the public/provider-portal boundary in one place (the underlying
    per-selector isolation is already unit-tested in
    apps.provider_portal.tests.test_professional_dashboard)."""

    def test_dashboard_never_shows_another_suppliers_data(self):
        from apps.provider_portal.services.dashboard_service import CaregiverDashboardPresentationService
        from apps.reporting.services.provider_report_service import ProviderReportService
        from apps.reviews.services.reputation_service import ReputationService

        supplier_a, caregiver_a = self._create_caregiver_supplier(display_name="مراقب الف")
        supplier_b, caregiver_b = self._create_caregiver_supplier(display_name="مراقب ب")
        CaregiverSkillService.add_skill(caregiver_b, name="مهارت ب")

        dashboard_a = CaregiverDashboardPresentationService.build_for_supplier(
            supplier=supplier_a,
            caregiver=caregiver_a,
            tenant_id=self.tenant.id,
            reputation=ReputationService.get_reputation_summary(supplier_a),
            performance=ProviderReportService.get_report_for_supplier(self.tenant.id, supplier_a.id),
        )
        self.assertNotIn("مراقب ب", str(dashboard_a))
        self.assertNotIn("مهارت ب", str(dashboard_a))


class Phase2QueryBudgetAcceptanceTest(PublicSiteTestCase):
    """Point 14: query counts bounded with populated data, for the
    directory-with-many-caregivers, search-with-filters, and home
    featured-providers surfaces (the public profile detail, provider
    dashboard, and provider profile-management pages already each have a
    dedicated assertNumQueries test — see
    apps.public_site.tests.test_professional_profile_public,
    apps.provider_portal.tests.test_professional_dashboard, and
    apps.provider_portal.tests.test_profile).

    KL-012 remediation (quality/DEFECT_AND_RISK_REGISTER.md): directory/
    home query counts previously grew by one (or two) queries per
    matching candidate, from two independent per-candidate sources —
    DiscoveryRankingService's per-candidate CapacityService.
    is_capacity_exceeded() call, and SupplierSearchService's per-candidate
    resolve_supplier_entity() call inside its city filter. Both are now
    batched (CapacityService.bulk_is_capacity_exceeded(),
    resolve_supplier_entities_bulk()) — see ARCHITECTURE_DECISION_LOG.md
    ADM-022's remediation note. These tests assert the resulting query
    count is a stable maximum (bounded by PAGE_SIZE/`limit`, not by total
    candidate count), not merely record whatever the current count is."""

    def _seed(self, count, *, city="tehran", name_prefix="caregiver"):
        for i in range(count):
            self._create_caregiver_supplier(
                display_name=f"{name_prefix}-{i}",
                city=city,
                verification_status="verified",
            )

    def _query_count(self, callable_):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            callable_()
        return len(ctx.captured_queries)

    # -- 1 & 2: directory query count does not grow with candidate count --

    def test_directory_query_count_does_not_grow_from_1_to_5_caregivers(self):
        self._seed(1)
        count_at_1 = self._query_count(lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id))
        self._seed(4)  # 5 total
        count_at_5 = self._query_count(lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id))
        self.assertEqual(count_at_1, count_at_5)

    def test_directory_query_count_does_not_grow_materially_from_5_to_20_caregivers(self):
        self._seed(5)
        count_at_5 = self._query_count(lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id))
        self._seed(15)  # 20 total
        count_at_20 = self._query_count(lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id))
        # Growth from 5 to 20 candidates is bounded by PAGE_SIZE=12 card
        # construction only (5 cards built -> 12 cards built), never by
        # the remaining 15 candidates beyond a page. A further increase to
        # 100 candidates (below) proves this saturates completely.
        self.assertLessEqual(count_at_20 - count_at_5, 20)

    def test_directory_query_count_is_a_stable_maximum_beyond_one_page(self):
        self._seed(20)
        count_at_20 = self._query_count(lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id))
        self._seed(80)  # 100 total
        count_at_100 = self._query_count(lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id))
        self.assertEqual(count_at_20, count_at_100)

    # -- 3: text search remains bounded --

    def test_text_search_query_count_is_a_stable_maximum(self):
        self._seed(20)
        count_at_20 = self._query_count(
            lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id, text="caregiver"),
        )
        self._seed(80)  # 100 total
        count_at_100 = self._query_count(
            lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id, text="caregiver"),
        )
        self.assertEqual(count_at_20, count_at_100)

    # -- 4: service/category filtering remains bounded --

    def test_service_category_filter_query_count_is_a_stable_maximum(self):
        for i in range(20):
            self._create_caregiver_supplier(
                display_name=f"cat-{i}",
                service_category_ids=[str(self.category.id)],
                verification_status="verified",
            )
        count_at_20 = self._query_count(
            lambda: CaregiverDirectoryService.search(
                tenant_id=self.tenant.id, service_category_id=str(self.category.id)
            ),
        )
        for i in range(80):
            self._create_caregiver_supplier(
                display_name=f"cat-more-{i}",
                service_category_ids=[str(self.category.id)],
                verification_status="verified",
            )
        count_at_100 = self._query_count(
            lambda: CaregiverDirectoryService.search(
                tenant_id=self.tenant.id, service_category_id=str(self.category.id)
            ),
        )
        self.assertEqual(count_at_20, count_at_100)

    # -- 5: city filtering remains bounded --

    def test_city_filter_query_count_is_a_stable_maximum(self):
        self._seed(20, city="tehran")
        count_at_20 = self._query_count(
            lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id, city="tehran"),
        )
        self._seed(80, city="tehran", name_prefix="more")  # 100 total
        count_at_100 = self._query_count(
            lambda: CaregiverDirectoryService.search(tenant_id=self.tenant.id, city="tehran"),
        )
        self.assertEqual(count_at_20, count_at_100)

    def test_directory_search_with_filters_returns_correct_bounded_page(self):
        self._seed(15)
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, city="tehran", text="caregiver")
        self.assertEqual(page.pagination.total_count, 15)
        self.assertLessEqual(len(page.caregivers), 12)  # PAGE_SIZE

    # -- 6: home-page featured cards remain bounded --

    def test_home_featured_query_count_is_a_stable_maximum(self):
        self._seed(3)
        count_at_3 = self._query_count(lambda: HomePageService.get_home_view(tenant_id=self.tenant.id))
        self._seed(17)  # 20 total
        count_at_20 = self._query_count(lambda: HomePageService.get_home_view(tenant_id=self.tenant.id))
        self._seed(80)  # 100 total
        count_at_100 = self._query_count(lambda: HomePageService.get_home_view(tenant_id=self.tenant.id))
        # featured() has a fixed limit=4 output regardless of candidate
        # count, so once candidates >= 4 the count must be fully flat.
        self.assertEqual(count_at_20, count_at_100)
        self.assertLessEqual(count_at_20 - count_at_3, 15)

    # -- 7: pagination count remains correct --

    def test_pagination_total_count_and_page_count_remain_correct(self):
        self._seed(25)
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, page=1)
        self.assertEqual(page.pagination.total_count, 25)
        self.assertEqual(page.pagination.total_pages, 3)  # ceil(25 / 12)
        self.assertEqual(len(page.caregivers), 12)
        last_page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, page=3)
        self.assertEqual(len(last_page.caregivers), 1)

    # -- 8: hidden/ineligible caregivers remain excluded --

    def test_hidden_ineligible_caregivers_remain_excluded_from_bounded_results(self):
        self._seed(20)
        self._create_caregiver_supplier(display_name="hidden-unverified", verification_status="unverified")
        self._create_caregiver_supplier(display_name="hidden-draft", profile_status="draft")
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        home = HomePageService.get_home_view(tenant_id=self.tenant.id)
        self.assertEqual(page.pagination.total_count, 20)
        self.assertNotIn(
            "hidden-unverified",
            {c.display_name for c in page.caregivers} | {c.display_name for c in home.featured_caregivers},
        )
        self.assertNotIn(
            "hidden-draft",
            {c.display_name for c in page.caregivers} | {c.display_name for c in home.featured_caregivers},
        )

    # -- 9: rating/review summary remains correct --

    def test_rating_summary_remains_correct_at_scale(self):
        self._seed(20)
        supplier, _ = self._create_caregiver_supplier(display_name="rated-caregiver")
        self._add_approved_review(supplier=supplier, rating="4.00")
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, text="rated-caregiver")
        self.assertEqual(page.pagination.total_count, 1)
        card = page.caregivers[0]
        self.assertEqual(card.rating.review_count, 1)
        self.assertEqual(card.rating.average, Decimal("4.00"))

    # -- 10: service-category information remains correct --

    def test_service_category_filter_returns_only_matching_caregivers(self):
        other_category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="خدمت دیگر",
            slug="other-service",
            status=CatalogStatus.ACTIVE,
        )
        self._create_caregiver_supplier(
            display_name="matches-category",
            service_category_ids=[str(self.category.id)],
        )
        self._create_caregiver_supplier(
            display_name="different-category",
            service_category_ids=[str(other_category.id)],
        )
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, service_category_id=str(self.category.id))
        names = {c.display_name for c in page.caregivers}
        self.assertIn("matches-category", names)
        self.assertNotIn("different-category", names)

    # -- 11: ordering/ranking remains unchanged --

    def test_ranking_order_unchanged_by_the_query_optimization(self):
        """DiscoveryRankingService's own unit tests already prove each
        scoring component (verification/reputation/availability/capacity)
        independently — apps.discovery.tests.test_ranking_service — this
        proves the batched capacity lookup this remediation introduced
        still ranks a capacity-exceeded caregiver below one that is not,
        exactly as the pre-remediation per-candidate lookup did."""
        from apps.availability.services import CapacityService

        supplier_ok, _ = self._create_caregiver_supplier(display_name="under-capacity")
        supplier_over, _ = self._create_caregiver_supplier(display_name="over-capacity")
        CapacityService.set_capacity_rule(supplier=supplier_over, max_concurrent_assignments=0)

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        names_in_order = [c.display_name for c in page.caregivers]
        self.assertLess(names_in_order.index("under-capacity"), names_in_order.index("over-capacity"))

    # -- 12: no private data is added to cards --

    def test_no_private_data_added_to_cards_at_scale(self):
        self._seed(20)
        supplier, caregiver = self._create_caregiver_supplier(display_name="private-data-check")
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, text="private-data-check")
        card = page.caregivers[0]
        card_fields = {f.name for f in card.__dataclass_fields__.values()}
        self.assertNotIn("phone", card_fields)
        self.assertNotIn("national_id", card_fields)
        self.assertNotIn("bio", card_fields)  # only bio_snippet is exposed, never the raw bio

    # -- 13: public detail behavior remains unchanged --

    def test_public_detail_page_behavior_unchanged_by_the_query_optimization(self):
        self._seed(20)
        supplier, _ = self._create_caregiver_supplier(display_name="detail-page-caregiver")
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.display_name, "detail-page-caregiver")
