import uuid
from decimal import Decimal

from apps.api.permission_keys import PAYMENTS_ATTEMPTS_CREATE, PAYMENTS_INTENTS_CREATE
from apps.payments.models import PaymentIntent, PaymentStatus

from .helpers import ApiTestCase


class PaymentIntentCreateEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post("/api/v1/payments/intents/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_login(self.customer_profile.user)
        response = self.client.post("/api/v1/payments/intents/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_creates_payment_intent(self):
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_INTENTS_CREATE])
        self.client.force_login(self.customer_profile.user)

        response = self.client.post(
            "/api/v1/payments/intents/",
            {"amount": "100000", "idempotency_key": f"key-{uuid.uuid4().hex}"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(Decimal(body["amount"]), Decimal("100000.00"))
        self.assertEqual(body["status"], PaymentStatus.CREATED)

        intent = PaymentIntent.objects.get(id=body["id"])
        self.assertEqual(intent.tenant_id, self.tenant.id)

    def test_idempotent_creation(self):
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_INTENTS_CREATE])
        self.client.force_login(self.customer_profile.user)
        key = f"key-{uuid.uuid4().hex}"

        first = self.client.post(
            "/api/v1/payments/intents/",
            {"amount": "100000", "idempotency_key": key},
            content_type="application/json",
        )
        second = self.client.post(
            "/api/v1/payments/intents/",
            {"amount": "100000", "idempotency_key": key},
            content_type="application/json",
        )

        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(PaymentIntent.objects.filter(idempotency_key=key).count(), 1)

    def test_missing_idempotency_key_is_a_validation_error(self):
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_INTENTS_CREATE])
        self.client.force_login(self.customer_profile.user)

        response = self.client.post(
            "/api/v1/payments/intents/",
            {"amount": "100000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


class PaymentAttemptCreateEndpointTest(ApiTestCase):
    def _create_intent(self):
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_INTENTS_CREATE])
        self.client.force_login(self.customer_profile.user)
        response = self.client.post(
            "/api/v1/payments/intents/",
            {"amount": "50000", "idempotency_key": f"key-{uuid.uuid4().hex}"},
            content_type="application/json",
        )
        return response.json()["id"]

    def test_unauthenticated_request_is_rejected(self):
        intent_id = self._create_intent()
        self.client.logout()

        response = self.client.post(
            f"/api/v1/payments/intents/{intent_id}/attempts/", {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_starts_attempt_and_transitions_to_pending(self):
        intent_id = self._create_intent()
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_ATTEMPTS_CREATE])

        response = self.client.post(
            f"/api/v1/payments/intents/{intent_id}/attempts/", {}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], PaymentStatus.PENDING)
        self.assertTrue(body["provider_reference"].startswith("FAKE-"))

    def test_intent_in_another_tenant_404s(self):
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_ATTEMPTS_CREATE])
        self.client.force_login(self.customer_profile.user)

        other_intent_id = uuid.uuid4()
        response = self.client.post(
            f"/api/v1/payments/intents/{other_intent_id}/attempts/", {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


class FakeProviderCallbackEndpointTest(ApiTestCase):
    def _create_pending_attempt(self):
        self._grant(self.customer_profile.user, self.tenant, [PAYMENTS_INTENTS_CREATE, PAYMENTS_ATTEMPTS_CREATE])
        self.client.force_login(self.customer_profile.user)

        intent_response = self.client.post(
            "/api/v1/payments/intents/",
            {"amount": "20000", "idempotency_key": f"key-{uuid.uuid4().hex}"},
            content_type="application/json",
        )
        intent_id = intent_response.json()["id"]

        attempt_response = self.client.post(
            f"/api/v1/payments/intents/{intent_id}/attempts/",
            {},
            content_type="application/json",
        )
        self.client.logout()
        return intent_id, attempt_response.json()["provider_reference"]

    def test_does_not_require_authentication(self):
        intent_id, provider_reference = self._create_pending_attempt()

        response = self.client.post(
            "/api/v1/payments/callbacks/fake/",
            {
                "provider_reference": provider_reference,
                "provider_event_id": "evt-1",
                "status": "SUCCEEDED",
                "amount": "20000",
                "currency": "IRR",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], PaymentStatus.SUCCEEDED)

    def test_duplicate_callback_is_idempotent(self):
        intent_id, provider_reference = self._create_pending_attempt()
        payload = {
            "provider_reference": provider_reference,
            "provider_event_id": "evt-dup",
            "status": "SUCCEEDED",
            "amount": "20000",
            "currency": "IRR",
        }

        first = self.client.post("/api/v1/payments/callbacks/fake/", payload, content_type="application/json")
        second = self.client.post("/api/v1/payments/callbacks/fake/", payload, content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["idempotent_replay"])

    def test_amount_mismatch_is_rejected_as_domain_error(self):
        intent_id, provider_reference = self._create_pending_attempt()

        response = self.client.post(
            "/api/v1/payments/callbacks/fake/",
            {
                "provider_reference": provider_reference,
                "provider_event_id": "evt-bad",
                "status": "SUCCEEDED",
                "amount": "999999",
                "currency": "IRR",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "domain_error")

    def test_unknown_provider_reference_404s(self):
        response = self.client.post(
            "/api/v1/payments/callbacks/fake/",
            {
                "provider_reference": "FAKE-does-not-exist",
                "provider_event_id": "evt-1",
                "status": "SUCCEEDED",
                "amount": "1",
                "currency": "IRR",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
