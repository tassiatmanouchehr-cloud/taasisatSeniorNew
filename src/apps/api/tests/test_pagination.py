from django.test import SimpleTestCase

from apps.api.errors import ApiError
from apps.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, paginate, parse_pagination_params


class PaginateTest(SimpleTestCase):
    def test_paginate_returns_requested_slice(self):
        items = list(range(50))

        page = paginate(items, limit=10, offset=5)

        self.assertEqual(page.results, tuple(range(5, 15)))
        self.assertEqual(page.limit, 10)
        self.assertEqual(page.offset, 5)
        self.assertEqual(page.total_count, 50)
        self.assertTrue(page.has_more)

    def test_paginate_last_page_has_no_more(self):
        items = list(range(10))

        page = paginate(items, limit=10, offset=0)

        self.assertFalse(page.has_more)
        self.assertEqual(len(page.results), 10)

    def test_paginate_caps_at_max_limit(self):
        items = list(range(500))

        page = paginate(items, limit=10_000)

        self.assertEqual(page.limit, MAX_LIMIT)
        self.assertEqual(len(page.results), MAX_LIMIT)

    def test_paginate_rejects_negative_offset(self):
        page = paginate(list(range(10)), limit=5, offset=-100)
        self.assertEqual(page.offset, 0)

    def test_paginate_empty_dataset(self):
        page = paginate([], limit=DEFAULT_LIMIT, offset=0)

        self.assertEqual(page.results, ())
        self.assertEqual(page.total_count, 0)
        self.assertFalse(page.has_more)

    def test_page_dto_is_immutable(self):
        page = paginate([1, 2, 3])
        with self.assertRaises(Exception):
            page.limit = 999


class ParsePaginationParamsTest(SimpleTestCase):
    def test_defaults_when_absent(self):
        limit, offset = parse_pagination_params({})
        self.assertEqual(limit, DEFAULT_LIMIT)
        self.assertEqual(offset, 0)

    def test_parses_valid_values(self):
        limit, offset = parse_pagination_params({"limit": "15", "offset": "30"})
        self.assertEqual(limit, 15)
        self.assertEqual(offset, 30)

    def test_caps_limit_at_maximum(self):
        limit, offset = parse_pagination_params({"limit": "99999"})
        self.assertEqual(limit, MAX_LIMIT)

    def test_rejects_non_integer_limit(self):
        with self.assertRaises(ApiError):
            parse_pagination_params({"limit": "not-a-number"})

    def test_rejects_zero_or_negative_limit(self):
        with self.assertRaises(ApiError):
            parse_pagination_params({"limit": "0"})

    def test_rejects_negative_offset(self):
        with self.assertRaises(ApiError):
            parse_pagination_params({"offset": "-1"})
