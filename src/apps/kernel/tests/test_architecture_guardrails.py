"""
Architecture guardrails — Module 18 (Architecture Consolidation).

Lightweight, source-inspection-based checks (no import-time side
effects) enforcing the rules documented under docs/architecture/.
Deliberately conservative — broad allowlists — to avoid false
positives per the Module 18 brief. These are structural checks, not a
replacement for code review.

Mirrors the existing structural-test precedent in this file's sibling
test_rbac_structural.py (Module 08), which already imports across
several apps to verify a cross-cutting architectural property.

Most checks here are simple substring/regex matching (no AST), per the
Module 18 brief. `ProfileStatusTransitionSoleWriterTest` is a deliberate
exception (independent pre-merge review of PR #18, Required Fix 6): a
plain regex on `.status = ProfileStatus.X` cannot see a status write
passed as a keyword argument (`.create(status=...)`, `.update(status=...)`,
`.update_or_create(defaults={"status": ...})`), so that one guardrail
walks the AST instead — mirroring the AST-based import-detection already
used by apps.kernel.tests.test_supplier_registry
._module_imports_accounts()/apps.accounts.tests.test_supplier_bridge's
own copy of it, so AST-based structural inspection is not a new pattern
in this codebase, only new to this file.
"""

import ast
import re
from pathlib import Path

from django.apps import apps as django_apps
from django.test import SimpleTestCase

APPS_DIR = Path(django_apps.get_app_config("kernel").path).parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _python_files(*, under: Path, exclude_dirs: tuple[str, ...] = ()) -> list[Path]:
    files = []
    for path in under.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        files.append(path)
    return files


# Shared by every thin-controller surface (apps.api, apps.admin_portal, and any future
# one) — a single-row `.objects.get(...)` lookup is the only ORM access a view may
# perform directly; everything else belongs in the service layer.
THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS = (
    r"\.objects\.filter\(",
    r"\.objects\.exclude\(",
    r"\.objects\.annotate\(",
    r"\.objects\.aggregate\(",
    r"\.objects\.all\(\)",
    r"\.objects\.create\(",
    r"\.objects\.update\(",
    r"\.objects\.bulk_create\(",
    r"\.objects\.bulk_update\(",
    r"\.save\(",
    r"\.delete\(\)",
)


class ApiViewOrmDisciplineTest(SimpleTestCase):
    """
    docs/architecture/api-guidelines.md + ADR-007: apps/api/views/*.py may
    only touch the ORM via a single-row `.objects.get(...)` lookup — never
    a multi-row query or a direct mutation. Business logic and multi-row
    ORM access belong in the service layer.
    """

    FORBIDDEN_PATTERNS = THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS

    def test_no_forbidden_orm_calls_in_api_views(self):
        views_dir = APPS_DIR / "api" / "views"
        self.assertTrue(views_dir.is_dir(), f"expected {views_dir} to exist")

        violations = []
        for path in _python_files(under=views_dir):
            source = _read(path)
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, source):
                    violations.append(f"{path.relative_to(APPS_DIR)}: matched {pattern!r}")

        self.assertEqual(violations, [], "Forbidden ORM usage found in apps/api/views/:\n" + "\n".join(violations))

    def test_api_views_only_use_single_row_get_lookups(self):
        """Sanity check on the check itself: .objects.get( is expected to appear (tenant-scoped lookups)."""
        views_dir = APPS_DIR / "api" / "views"
        combined = "\n".join(_read(p) for p in _python_files(under=views_dir))
        self.assertIn(".objects.get(", combined)


class AdminPortalOrmDisciplineTest(SimpleTestCase):
    """
    Module 19: apps/admin_portal/views.py follows the same thin-controller
    rule as apps/api/views/*.py (ADR-007) — every view calls exactly one
    apps.reporting service method (or the reused health-check helpers) and
    renders a template. No ORM access of any kind is expected here (unlike
    apps.api, no view needs to resolve a request-body ID into an object),
    so this check is stricter: any ORM call at all is a violation.
    """

    def test_no_orm_calls_in_admin_portal_views(self):
        views_file = APPS_DIR / "admin_portal" / "views.py"
        self.assertTrue(views_file.is_file(), f"expected {views_file} to exist")

        source = _read(views_file)
        violations = [pattern for pattern in THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS if re.search(pattern, source)]
        if re.search(r"\.objects\.\w+\(", source):
            violations.append(".objects. call found — admin_portal views should call services only")

        self.assertEqual(violations, [], f"Forbidden ORM usage found in apps/admin_portal/views.py: {violations}")


class PortalOrmDisciplineTest(SimpleTestCase):
    """
    Customer Experience Phase 1 (remediation): apps/portal/views.py follows
    the same thin-controller rule as apps/admin_portal/views.py — every
    view calls a service method (apps.accounts, apps.orders,
    apps.notifications, apps.finance, apps.wallet, apps.pricing —
    including the read/query services added specifically so this app
    would have something to call instead of the ORM: OrderQueryService,
    CatalogQueryService, OrderTimelineService, NotificationQueryService)
    and renders a template. Like admin_portal, any ORM call at all here is
    a violation — this is the guardrail an earlier review of this same
    module found missing.
    """

    def test_no_orm_calls_in_portal_views(self):
        views_file = APPS_DIR / "portal" / "views.py"
        self.assertTrue(views_file.is_file(), f"expected {views_file} to exist")

        source = _read(views_file)
        violations = [pattern for pattern in THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS if re.search(pattern, source)]
        if re.search(r"\.objects\.\w+\(", source):
            violations.append(".objects. call found — portal views should call services only")

        self.assertEqual(violations, [], f"Forbidden ORM usage found in apps/portal/views.py: {violations}")


class ProviderPortalOrmDisciplineTest(SimpleTestCase):
    """
    Epic 02 (Marketplace Operational Experience): apps/provider_portal/views.py
    holds to the same zero-ORM standard as apps/portal/views.py — every view
    calls a service/query-service method (apps.booking, apps.execution,
    apps.availability, apps.finance, apps.wallet, apps.reporting,
    apps.reviews, apps.notifications) and renders a template.
    """

    def test_no_orm_calls_in_provider_portal_views(self):
        views_file = APPS_DIR / "provider_portal" / "views.py"
        self.assertTrue(views_file.is_file(), f"expected {views_file} to exist")

        source = _read(views_file)
        violations = [pattern for pattern in THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS if re.search(pattern, source)]
        if re.search(r"\.objects\.\w+\(", source):
            violations.append(".objects. call found — provider_portal views should call services only")

        self.assertEqual(violations, [], f"Forbidden ORM usage found in apps/provider_portal/views.py: {violations}")


class OrganizationPortalOrmDisciplineTest(SimpleTestCase):
    """
    Epic 02 (Marketplace Operational Experience): apps/organization_portal
    /views.py holds to the same zero-ORM standard as apps/portal/views.py.
    """

    def test_no_orm_calls_in_organization_portal_views(self):
        views_file = APPS_DIR / "organization_portal" / "views.py"
        self.assertTrue(views_file.is_file(), f"expected {views_file} to exist")

        source = _read(views_file)
        violations = [pattern for pattern in THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS if re.search(pattern, source)]
        if re.search(r"\.objects\.\w+\(", source):
            violations.append(".objects. call found — organization_portal views should call services only")

        self.assertEqual(
            violations,
            [],
            f"Forbidden ORM usage found in apps/organization_portal/views.py: {violations}",
        )


class PublicSiteOrmDisciplineTest(SimpleTestCase):
    """
    Epic 06 (Marketplace Profiles & Discovery): apps/public_site/views.py
    holds to the same zero-ORM standard as apps/portal/views.py — every
    view calls a service method (HomePageService, CaregiverDirectoryService,
    CaregiverPublicProfileService) and renders a template.
    """

    def test_no_orm_calls_in_public_site_views(self):
        views_file = APPS_DIR / "public_site" / "views.py"
        self.assertTrue(views_file.is_file(), f"expected {views_file} to exist")

        source = _read(views_file)
        violations = [pattern for pattern in THIN_CONTROLLER_FORBIDDEN_ORM_PATTERNS if re.search(pattern, source)]
        if re.search(r"\.objects\.\w+\(", source):
            violations.append(".objects. call found — public_site views should call services only")

        self.assertEqual(violations, [], f"Forbidden ORM usage found in apps/public_site/views.py: {violations}")


class NoReverseApiImportTest(SimpleTestCase):
    """
    docs/architecture/dependency-graph.md: apps.api sits at the top of the
    dependency graph. Nothing else may import it.
    """

    def test_nothing_imports_apps_api_except_apps_api_itself(self):
        pattern = re.compile(r"^\s*(from|import)\s+apps\.api\b")
        violations = []

        for path in _python_files(under=APPS_DIR, exclude_dirs=("api",)):
            for lineno, line in enumerate(_read(path).splitlines(), start=1):
                if pattern.match(line):
                    violations.append(f"{path.relative_to(APPS_DIR)}:{lineno}: {line.strip()}")

        self.assertEqual(violations, [], "Found imports of apps.api outside apps/api/:\n" + "\n".join(violations))


class NoDuplicateWalletModelTest(SimpleTestCase):
    """
    docs/architecture/wallet-finance-boundary.md + ADR-004: exactly two
    locations may define a model literally named Wallet/WalletTransaction
    — the canonical apps.wallet and the documented-legacy
    apps.finance.models.wallet. A third would mean a new, undocumented
    wallet concept has been introduced.
    """

    ALLOWED_FILES = {
        APPS_DIR / "wallet" / "models.py",
        APPS_DIR / "finance" / "models" / "wallet.py",
    }

    def test_only_the_documented_files_define_wallet_models(self):
        pattern = re.compile(r"^class (Wallet|WalletTransaction)\(", re.MULTILINE)
        offenders = []

        for path in _python_files(under=APPS_DIR, exclude_dirs=("tests",)):
            if path in self.ALLOWED_FILES:
                continue
            if pattern.search(_read(path)):
                offenders.append(str(path.relative_to(APPS_DIR)))

        self.assertEqual(
            offenders,
            [],
            "A new Wallet/WalletTransaction model was found outside the two documented "
            f"locations {sorted(str(p.relative_to(APPS_DIR)) for p in self.ALLOWED_FILES)}: {offenders}",
        )


class EventSystemSeparationTest(SimpleTestCase):
    """
    docs/architecture/event-architecture.md: DomainEvent (in-memory,
    apps.kernel.events) and EventOutbox/CES (persisted,
    apps.kernel.models.event_outbox) are separate systems.
    EventPublisher is the sole writer of EventOutbox.
    """

    def test_only_the_publisher_and_the_outbox_worker_touch_event_outbox(self):
        """EventPublisher creates rows; kernel.tasks (the Celery outbox worker) is the sole
        reader/dispatcher (polls PENDING, marks PUBLISHED/FAILED/DEAD_LETTER). No business
        module should read or write EventOutbox directly."""
        pattern = re.compile(r"EventOutbox\.objects\.")
        allowed_files = {
            APPS_DIR / "kernel" / "services" / "event_publisher.py",
            APPS_DIR / "kernel" / "tasks.py",
        }
        offenders = []

        for path in _python_files(under=APPS_DIR, exclude_dirs=("tests", "migrations")):
            if path in allowed_files:
                continue
            if pattern.search(_read(path)):
                offenders.append(str(path.relative_to(APPS_DIR)))

        self.assertEqual(
            offenders, [], f"Found direct EventOutbox access outside EventPublisher/kernel.tasks: {offenders}"
        )

    def test_domain_event_module_does_not_import_event_outbox(self):
        for filename in ("base.py", "publisher.py", "registry.py"):
            path = APPS_DIR / "kernel" / "events" / filename
            source = _read(path)
            self.assertNotIn(
                "kernel.models.event_outbox import",
                source,
                f"{filename} should not import the EventOutbox model — the two event systems are separate.",
            )


class ServiceSupplierProfileCouplingTest(SimpleTestCase):
    """
    docs/architecture/bounded-contexts.md: business modules use
    kernel.ServiceSupplier, never CaregiverProfile/OrganizationProfile
    directly. Allowlist is deliberately broad (tests, seed scripts, the
    owning app, and the two documented backward-compat/reporting call
    sites) to avoid false positives — this checks for *new*, undocumented
    direct coupling, not every historical reference.
    """

    ALLOWED_DIR_PARTS = ("tests", "management")
    ALLOWED_APP_DIRS = ("accounts",)
    ALLOWED_FILES = {
        APPS_DIR / "orders" / "models.py",
        APPS_DIR / "reporting" / "services" / "marketplace_report_service.py",
    }

    def test_no_new_direct_profile_imports_outside_the_documented_allowlist(self):
        pattern = re.compile(r"import\s+.*\b(CaregiverProfile|OrganizationProfile)\b")
        offenders = []

        for path in _python_files(under=APPS_DIR):
            relative_parts = path.relative_to(APPS_DIR).parts
            if relative_parts[0] in self.ALLOWED_APP_DIRS:
                continue
            if any(part in self.ALLOWED_DIR_PARTS for part in relative_parts):
                continue
            if path in self.ALLOWED_FILES:
                continue
            if pattern.search(_read(path)):
                offenders.append(str(path.relative_to(APPS_DIR)))

        self.assertEqual(
            offenders,
            [],
            "Found a direct CaregiverProfile/OrganizationProfile import outside the documented "
            f"allowlist — use kernel.ServiceSupplier instead: {offenders}",
        )


class OrderOrganizationEligibilitySoleWriterTest(SimpleTestCase):
    """
    Epic 04 (Enterprise Organization Isolation): OrderOrganizationEligibility
    must have exactly one writer — apps.orders.services.eligibility_service
    .OrderEligibilityService (System Architect Decision 1: "No caller may
    create OrderOrganizationEligibility directly."). Allowlist is the
    service's own file, the model's migration, and test files (which
    legitimately construct rows directly for fixture/constraint testing).
    """

    ALLOWED_DIR_PARTS = ("tests", "migrations")
    ALLOWED_FILES = {
        APPS_DIR / "orders" / "services" / "eligibility_service.py",
    }

    def test_no_writes_outside_the_eligibility_service(self):
        pattern = re.compile(
            r"OrderOrganizationEligibility\.objects\.(create|get_or_create|update_or_create|bulk_create)\("
        )
        offenders = []

        for path in _python_files(under=APPS_DIR):
            relative_parts = path.relative_to(APPS_DIR).parts
            if any(part in self.ALLOWED_DIR_PARTS for part in relative_parts):
                continue
            if path in self.ALLOWED_FILES:
                continue
            if pattern.search(_read(path)):
                offenders.append(str(path.relative_to(APPS_DIR)))

        self.assertEqual(
            offenders,
            [],
            "OrderOrganizationEligibility must only be written by "
            f"OrderEligibilityService — found direct writes in: {offenders}",
        )


# CaregiverProfile/OrganizationProfile ACTIVE/SUSPENDED/ARCHIVED are the
# lifecycle-significant transitions ProfileActivationService (and,
# eventually, its future BG-019 siblings) must exclusively own. DRAFT is
# deliberately excluded: RegistrationService/ensure_caregiver_profile()
# legitimately create DRAFT profiles directly, and that must stay a
# non-event for this guardrail rather than requiring a blanket file
# allowlist that could just as easily hide an unauthorized ACTIVE write.
_GUARDED_PROFILE_STATUS_VALUES = {"ACTIVE", "SUSPENDED", "ARCHIVED"}
_PROFILE_STATUS_WRITE_METHODS = {"create", "update", "update_or_create", "get_or_create", "bulk_create", "bulk_update"}


def _is_profile_status_value(node: ast.AST) -> bool:
    """True for an AST node shaped like `ProfileStatus.ACTIVE` (or any of
    its other guarded sibling values)."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr in _GUARDED_PROFILE_STATUS_VALUES
        and isinstance(node.value, ast.Name)
        and node.value.id == "ProfileStatus"
    )


def _find_profile_status_writes(source: str) -> list[int]:
    """Line numbers of every AST-detected `status` write to a guarded
    ProfileStatus value: a direct attribute assignment
    (`x.status = ProfileStatus.ACTIVE`), a `status=` keyword argument to
    `.create()`/`.update()`/`.get_or_create()`/`.bulk_create()`/
    `.bulk_update()`, or a `"status"` key inside a `defaults={...}` dict
    literal passed to `.update_or_create()`/`.get_or_create()` — every
    shape that could set `CaregiverProfile`/`OrganizationProfile.status`
    to ACTIVE/SUSPENDED/ARCHIVED without going through
    ProfileActivationService. Returns [] on a syntax error (never crashes
    the suite on an unparseable file — that is a different problem)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "status"
                    and _is_profile_status_value(node.value)
                ):
                    offenders.append(node.lineno)
        elif isinstance(node, ast.Call):
            func = node.func
            method_name = func.attr if isinstance(func, ast.Attribute) else None
            if method_name not in _PROFILE_STATUS_WRITE_METHODS:
                continue
            for kw in node.keywords:
                if kw.arg == "status" and _is_profile_status_value(kw.value):
                    offenders.append(node.lineno)
                elif kw.arg == "defaults" and isinstance(kw.value, ast.Dict):
                    for key, value in zip(kw.value.keys, kw.value.values):
                        if (
                            isinstance(key, ast.Constant)
                            and key.value == "status"
                            and _is_profile_status_value(value)
                        ):
                            offenders.append(node.lineno)
    return offenders


class ProfileStatusTransitionSoleWriterTest(SimpleTestCase):
    """
    Core Profile-ServiceSupplier Invariant Remediation, approved decision 1:
    ProfileActivationService remains the sole owner of the
    CaregiverProfile/OrganizationProfile DRAFT -> ACTIVE transition (and,
    symmetrically, the only place ACTIVE/SUSPENDED/ARCHIVED may be
    written at all — see `_GUARDED_PROFILE_STATUS_VALUES`). Modeled
    structurally on OrderOrganizationEligibilitySoleWriterTest; strengthened
    (independent pre-merge review of PR #18, Required Fix 6) from a plain
    `.status = ProfileStatus.X` regex — which could not see a status
    write passed as a keyword argument — to the AST walk in
    `_find_profile_status_writes()`.

    ProfileStatus is also used (independently, out of scope for this
    remediation) by CustomerProfile/ElderProfile/TrustedContact — an AST
    walk still can't distinguish which *model* a given `.status = ` or
    `status=` write targets from source alone. Rather than a fragile
    heuristic, this test's allowlist explicitly names every current real
    production match repository-wide (confirmed by direct search at the
    time this guardrail was written) — `profile_activation_service.py` is
    the one sanctioned CaregiverProfile/OrganizationProfile writer;
    `care_recipients.py` writes an unrelated ElderProfile's own `status`
    field, sharing only the enum, not the model. Any new match anywhere
    else in the repository fails this test.

    `seed_product_walkthrough.py` was added to the allowlist when this
    guardrail was strengthened to AST (independent pre-merge review of
    PR #18, Required Fix 6) — the old regex never saw its
    `OrganizationProfile.objects.get_or_create(..., defaults={"status":
    ProfileStatus.ACTIVE, ...})` because the key/value pair sits inside a
    multi-line dict literal, not a `status=` keyword on one line. This is
    not a newly-introduced violation: the command already, unconditionally,
    calls `get_or_create_supplier_for_organization()` right after this
    creation regardless of whether the row was just created (verified by
    direct inspection) — the ACTIVE-profile/ACTIVE-supplier invariant
    already holds for this seed command's output, it just establishes
    ACTIVE directly (a deliberate, already-reviewed demo-data shortcut,
    the same pattern `seed_demo_accounts.py`/`seed_demo_people.py` use via
    the model's own default rather than an explicit keyword) instead of
    through a real reviewer-driven activation workflow, which a demo/
    walkthrough dataset has no use for.
    """

    ALLOWED_DIR_PARTS = ("tests", "migrations")
    ALLOWED_FILES = {
        APPS_DIR / "accounts" / "services" / "profile_activation_service.py",
        APPS_DIR / "accounts" / "services" / "care_recipients.py",
        APPS_DIR / "kernel" / "management" / "commands" / "seed_product_walkthrough.py",
    }

    def test_no_writes_outside_the_activation_service(self):
        offenders = []

        for path in _python_files(under=APPS_DIR):
            relative_parts = path.relative_to(APPS_DIR).parts
            if any(part in self.ALLOWED_DIR_PARTS for part in relative_parts):
                continue
            if path in self.ALLOWED_FILES:
                continue
            if _find_profile_status_writes(_read(path)):
                offenders.append(str(path.relative_to(APPS_DIR)))

        self.assertEqual(
            offenders,
            [],
            "CaregiverProfile/OrganizationProfile.status (ACTIVE/SUSPENDED/ARCHIVED) must only be "
            f"written by ProfileActivationService — found writes in: {offenders}",
        )


class ProfileStatusGuardrailDetectorSelfTest(SimpleTestCase):
    """Proves `_find_profile_status_writes()` actually catches the shapes
    ProfileStatusTransitionSoleWriterTest is supposed to guard against —
    the exact three patterns the independent pre-merge review of PR #18
    named (direct assignment, `.create(status=ACTIVE)`,
    `.update(status=ACTIVE)`), plus `update_or_create(defaults={...})`,
    and proves it correctly leaves legitimate DRAFT writes and unrelated
    calls alone (so this guardrail's allowlist stays minimal, not a
    blanket exemption for every ORM write)."""

    def test_detects_direct_attribute_assignment(self):
        source = "profile.status = ProfileStatus.ACTIVE\n"
        self.assertEqual(_find_profile_status_writes(source), [1])

    def test_detects_create_with_status_keyword(self):
        source = "CaregiverProfile.objects.create(status=ProfileStatus.ACTIVE, phone=phone)\n"
        self.assertEqual(_find_profile_status_writes(source), [1])

    def test_detects_queryset_update_with_status_keyword(self):
        source = "CaregiverProfile.objects.filter(id=x).update(status=ProfileStatus.ACTIVE)\n"
        self.assertEqual(_find_profile_status_writes(source), [1])

    def test_detects_update_or_create_defaults_dict(self):
        source = (
            "OrganizationProfile.objects.update_or_create(\n"
            "    code=code, defaults={'status': ProfileStatus.ACTIVE}\n"
            ")\n"
        )
        self.assertEqual(_find_profile_status_writes(source), [1])

    def test_detects_suspended_and_archived_too(self):
        source = "profile.status = ProfileStatus.SUSPENDED\nprofile.status = ProfileStatus.ARCHIVED\n"
        self.assertEqual(_find_profile_status_writes(source), [1, 2])

    def test_does_not_flag_draft_writes(self):
        source = "CaregiverProfile.objects.create(status=ProfileStatus.DRAFT)\n"
        self.assertEqual(_find_profile_status_writes(source), [])

    def test_does_not_flag_unrelated_status_reads_or_comparisons(self):
        source = "if profile.status == ProfileStatus.ACTIVE:\n    pass\n"
        self.assertEqual(_find_profile_status_writes(source), [])

    def test_does_not_flag_unrelated_create_calls(self):
        source = "Order.objects.create(status=OrderStatus.ACTIVE)\n"
        self.assertEqual(_find_profile_status_writes(source), [])


class ServiceSupplierSoleWriterTest(SimpleTestCase):
    """
    Core Profile-ServiceSupplier Invariant Remediation: ServiceSupplier
    rows must only ever be created through
    apps.kernel.services.supplier_registry.SupplierRegistry — never
    directly. Modeled structurally on
    OrderOrganizationEligibilitySoleWriterTest. Allowlist covers the
    registry itself, migrations (schema/data operations legitimately use
    the historical model manager), and test files (which legitimately
    construct fixture rows directly).
    """

    ALLOWED_DIR_PARTS = ("tests", "migrations")
    ALLOWED_FILES = {
        APPS_DIR / "kernel" / "services" / "supplier_registry.py",
    }

    def test_no_writes_outside_the_supplier_registry(self):
        pattern = re.compile(r"ServiceSupplier\.objects\.(create|get_or_create|update_or_create|bulk_create)\(")
        offenders = []

        for path in _python_files(under=APPS_DIR):
            relative_parts = path.relative_to(APPS_DIR).parts
            if any(part in self.ALLOWED_DIR_PARTS for part in relative_parts):
                continue
            if path in self.ALLOWED_FILES:
                continue
            if pattern.search(_read(path)):
                offenders.append(str(path.relative_to(APPS_DIR)))

        self.assertEqual(
            offenders,
            [],
            f"ServiceSupplier must only be written by SupplierRegistry — found direct writes in: {offenders}",
        )
