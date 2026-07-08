"""Tests for query_normalizer.normalize_query()."""

import uuid

from django.test import TestCase

from apps.discovery.services import normalize_query
from apps.discovery.services.configuration import DEFAULT_LIMIT, MAX_LIMIT


class NormalizeQueryTest(TestCase):
    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_collapses_whitespace_and_casefolds_text(self):
        query = normalize_query(tenant_id=self.tenant_id, text="  Home   CARE  ")
        self.assertEqual(query.text, "home care")

    def test_empty_text_stays_empty(self):
        query = normalize_query(tenant_id=self.tenant_id, text="   ")
        self.assertEqual(query.text, "")

    def test_city_is_normalized_and_none_when_blank(self):
        query = normalize_query(tenant_id=self.tenant_id, city="  Tehran  ")
        self.assertEqual(query.city, "tehran")
        self.assertIsNone(normalize_query(tenant_id=self.tenant_id, city="   ").city)

    def test_default_limit_applied_when_not_specified(self):
        query = normalize_query(tenant_id=self.tenant_id)
        self.assertEqual(query.limit, DEFAULT_LIMIT)

    def test_limit_is_clamped_to_max(self):
        query = normalize_query(tenant_id=self.tenant_id, limit=10_000)
        self.assertEqual(query.limit, MAX_LIMIT)

    def test_limit_is_clamped_to_at_least_one(self):
        query = normalize_query(tenant_id=self.tenant_id, limit=0)
        self.assertEqual(query.limit, 1)
        query = normalize_query(tenant_id=self.tenant_id, limit=-5)
        self.assertEqual(query.limit, 1)

    def test_offset_cannot_be_negative(self):
        query = normalize_query(tenant_id=self.tenant_id, offset=-10)
        self.assertEqual(query.offset, 0)

    def test_offset_passes_through_when_valid(self):
        query = normalize_query(tenant_id=self.tenant_id, offset=40)
        self.assertEqual(query.offset, 40)

    def test_scoping_fields_pass_through_unchanged(self):
        category_id = uuid.uuid4()
        query = normalize_query(
            tenant_id=self.tenant_id, service_category_id=category_id,
            supplier_type="INDEPENDENT_PROVIDER", availability_status="available",
            verification_level="basic",
        )
        self.assertEqual(query.service_category_id, category_id)
        self.assertEqual(query.supplier_type, "INDEPENDENT_PROVIDER")
        self.assertEqual(query.availability_status, "available")
        self.assertEqual(query.verification_level, "basic")
