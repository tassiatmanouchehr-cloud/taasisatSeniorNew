import json

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.test import RequestFactory, TestCase

from apps.api.errors import ApiError
from apps.api.views import ApiView
from apps.kernel.services.errors import PermissionDenied


class _RaisingView(ApiView):
    exception_to_raise = None

    def get(self, request):
        raise self.exception_to_raise


class ApiErrorFormatTest(TestCase):
    """Exercises the real settings.REST_FRAMEWORK["EXCEPTION_HANDLER"] pipeline end to end."""

    def setUp(self):
        self.factory = RequestFactory()

    def _dispatch(self, exc):
        view = _RaisingView.as_view(exception_to_raise=exc)
        return view(self.factory.get("/"))

    def test_api_error_maps_to_its_own_status_and_code(self):
        response = self._dispatch(
            ApiError(code="validation_error", message="bad input", status_code=400, details={"field": "x"}),
        )

        self.assertEqual(response.status_code, 400)
        body = json.loads(response.render().content)
        self.assertEqual(body["error"]["code"], "validation_error")
        self.assertEqual(body["error"]["message"], "bad input")
        self.assertEqual(body["error"]["details"], {"field": "x"})

    def test_permission_denied_maps_to_403(self):
        response = self._dispatch(PermissionDenied("not allowed"))

        self.assertEqual(response.status_code, 403)
        body = json.loads(response.render().content)
        self.assertEqual(body["error"]["code"], "permission_denied")

    def test_http404_maps_to_404(self):
        response = self._dispatch(Http404("missing"))

        self.assertEqual(response.status_code, 404)
        body = json.loads(response.render().content)
        self.assertEqual(body["error"]["code"], "not_found")

    def test_object_does_not_exist_maps_to_404(self):
        response = self._dispatch(ObjectDoesNotExist("missing row"))

        self.assertEqual(response.status_code, 404)
        body = json.loads(response.render().content)
        self.assertEqual(body["error"]["code"], "not_found")

    def test_unhandled_exception_maps_to_500_without_leaking_details(self):
        response = self._dispatch(RuntimeError("some secret internal detail"))

        self.assertEqual(response.status_code, 500)
        body = json.loads(response.render().content)
        self.assertEqual(body["error"]["code"], "internal_error")
        rendered = json.dumps(body)
        self.assertNotIn("secret internal detail", rendered)
        self.assertNotIn("Traceback", rendered)

    def test_error_envelope_always_has_the_same_shape(self):
        response = self._dispatch(ApiError(code="x", message="y"))
        body = json.loads(response.render().content)

        self.assertIn("error", body)
        self.assertIn("code", body["error"])
        self.assertIn("message", body["error"])
        self.assertIn("details", body["error"])
